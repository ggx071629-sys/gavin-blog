from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app.assistant_index.chunker import chunk_source, sanitize_markdown
from app.assistant_index.constants import (
    OP_PURGE,
    PAYLOAD_ALLOWLIST,
    SOURCE_ARTICLE,
    SOURCE_PROFILE,
    STATUS_PENDING,
    STATUS_SUCCEEDED,
    TEST_EMBEDDING_MODEL,
    TEST_EMBEDDING_MODEL_VERSION,
    TEST_EMBEDDING_PROVIDER,
)
from app.assistant_index.embeddings import (
    AssistantIndexConfigurationError,
    DeterministicHashEmbeddings,
    validate_assistant_worker_settings,
)
from app.assistant_index.fts import (
    ASSISTANT_FTS_SQL,
    lexical_fallback_query,
    lexical_index_text,
    lexical_match_query,
)
from app.assistant_index.outbox import enqueue_task
from app.assistant_index.projector import (
    SourceDocument,
    iter_public_sources,
    project_article,
    project_profile,
    project_source,
)
from app.assistant_index.qdrant_store import sanitize_payload
from app.assistant_index.retriever import retrieve
from app.assistant_index.runtime import build_test_runtime
from app.assistant_index.worker import main, process_once, rebuild_generation
from app.config import Settings
from app.search import safe_match_query
from app.models import (
    Article,
    AssistantChunk,
    AssistantIndexCommand,
    AssistantIndexGeneration,
    AssistantIndexPointer,
    AssistantIndexTask,
    AssistantIndexWorkerState,
)

from .conftest import login, publish_article


class FakeClock:
    def __init__(self) -> None:
        self.now = datetime.now(UTC) + timedelta(hours=1)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


def _runtime(client: TestClient, clock: FakeClock | None = None):
    settings = client.app.state.settings.model_copy(
        update={
            "assistant_index_worker_enabled": True,
            "assistant_embedding_provider": TEST_EMBEDDING_PROVIDER,
            "assistant_embedding_model": TEST_EMBEDDING_MODEL,
            "assistant_embedding_model_version": TEST_EMBEDDING_MODEL_VERSION,
            "assistant_embedding_dimension": 32,
        }
    )
    return build_test_runtime(
        settings,
        client.app.state.database,
        clock=clock,
    )


def _session(client: TestClient):
    session = client.app.state.database.session_factory()
    session.info["settings"] = client.app.state.settings
    return session


def _result_chunks(db, result) -> list[AssistantChunk]:
    chunk_ids = [item.chunk_id for item in result.candidates]
    if not chunk_ids:
        return []
    return list(
        db.scalars(select(AssistantChunk).where(AssistantChunk.chunk_id.in_(chunk_ids))).all()
    )


def _activate_ready_generation(client: TestClient, runtime) -> int:
    """Simulate the API-owner finalize boundary in worker-focused unit tests."""
    generation_id = rebuild_generation(runtime)
    with _session(client) as db:
        pointer = db.get(AssistantIndexPointer, 1)
        generation = db.get(AssistantIndexGeneration, generation_id)
        assert pointer is not None
        assert generation is not None
        assert generation.status == "staging"
        if pointer.active_generation_id is not None:
            previous = db.get(AssistantIndexGeneration, pointer.active_generation_id)
            if previous is not None:
                previous.status = "previous"
        pointer.previous_generation_id = pointer.active_generation_id
        pointer.active_generation_id = generation_id
        generation.status = "active"
        command = db.scalar(select(AssistantIndexCommand).where(
            AssistantIndexCommand.generation_id == generation_id,
        ))
        command.status = "switched"
        db.commit()
    return generation_id


def test_chunker_is_deterministic_and_strips_html_noise() -> None:
    dirty = (
        "# Title\n\n"
        "<script>alert(1)</script>\n"
        '<p onclick="steal()">visible paragraph about retrieval</p>\n'
        "<div hidden>secret hidden copy</div>\n"
        "{{ templateNoise }}\n"
        "```python\nprint('keep code')\n```\n"
    )
    cleaned = sanitize_markdown(dirty)
    assert "alert(1)" not in cleaned
    assert "secret hidden copy" not in cleaned
    assert "templateNoise" not in cleaned
    assert "print('keep code')" in cleaned
    document = SourceDocument(
        source_type="article",
        source_id=1,
        source_version="9",
        title="Title",
        public_path="/notes/2026/08/title",
        body=dirty,
        content_hash="abc",
        pipeline_version="assistant-index-v1",
    )
    first = chunk_source(document, chunk_size=120, chunk_overlap=20)
    second = chunk_source(document, chunk_size=120, chunk_overlap=20)
    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    assert [chunk.heading_path for chunk in first] == [chunk.heading_path for chunk in second]
    assert all("alert(1)" not in chunk.page_content for chunk in first)
    assert any("keep code" in chunk.page_content for chunk in first)


def test_qdrant_payload_allowlist_rejects_document_text() -> None:
    legal = {
        "chunk_id": "abc",
        "source_type": "article",
        "source_id": 1,
        "source_version": "2",
        "generation": 1,
        "pipeline_version": "assistant-index-v1",
    }
    assert set(sanitize_payload(legal)) == set(PAYLOAD_ALLOWLIST)
    with pytest.raises(ValueError, match="not allowed"):
        sanitize_payload({**legal, "page_content": "nope", "title": "nope"})


def test_projector_excludes_drafts_old_revisions_and_hidden_profile(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    draft = client.post(
        "/api/v1/admin/articles",
        json={"title": "Draft only", "slug": "draft-only", "content": "should not index"},
        headers=headers,
    )
    assert draft.status_code == 201
    published = client.post(
        "/api/v1/admin/articles",
        json={
            "title": "Public note",
            "slug": "public-note",
            "summary": "summary",
            "content": "# Public body",
            "category_id": None,
            "tag_ids": [],
        },
        headers=headers,
    )
    assert published.status_code == 201
    article = publish_article(client, published.json(), headers).json()
    client.patch(
        f"/api/v1/admin/articles/{article['id']}",
        json={
            "title": "Working copy",
            "content": "unpublished change",
            "version": article["version"],
        },
        headers=headers,
    )
    client.patch(
        "/api/v1/admin/profile",
        json={
            "name": "Gavin",
            "title": "Engineer",
            "bio": "Public bio",
            "skills": [],
            "city": "Hidden City",
            "city_visible": False,
            "email": "secret@example.com",
            "email_visible": False,
            "version": 1,
        },
        headers=headers,
    )
    with _session(client) as db:
        sources = {f"{item.source_type}:{item.source_id}": item for item in iter_public_sources(db)}
        assert f"article:{draft.json()['id']}" not in sources
        public_article = sources[f"article:{article['id']}"]
        assert "unpublished change" not in public_article.body
        assert "Public body" in public_article.body
        profile = project_profile(db)
        assert "Hidden City" not in profile.body
        assert "secret@example.com" not in profile.body
        assert "Public bio" in profile.body
        row = db.get(Article, article["id"])
        assert row is not None
        assert project_article(db, row) is not None


def test_outbox_records_lifecycle_in_the_same_transaction(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    created = client.post(
        "/api/v1/admin/articles",
        json={"title": "Indexed", "slug": "indexed-article", "content": "# Hello index"},
        headers=headers,
    ).json()
    published = publish_article(client, created, headers).json()
    with _session(client) as db:
        tasks = list(db.scalars(select(AssistantIndexTask)).all())
        assert len(tasks) == 1
        assert tasks[0].source_type == SOURCE_ARTICLE
        assert tasks[0].operation == "upsert"
        assert tasks[0].target_version == str(published["current_revision_id"])
        assert tasks[0].status == STATUS_PENDING
        enqueue_task(
            db,
            source_type=SOURCE_ARTICLE,
            source_id=published["id"],
            target_version="will-rollback",
            operation="upsert",
        )
        db.rollback()
        remaining = db.scalar(
            select(func.count())
            .select_from(AssistantIndexTask)
            .where(AssistantIndexTask.target_version == "will-rollback")
        )
        assert remaining == 0

    client.delete(f"/api/v1/admin/articles/{published['id']}", headers=headers)
    with _session(client) as db:
        task = db.scalar(
            select(AssistantIndexTask)
            .where(AssistantIndexTask.source_id == published["id"])
            .order_by(AssistantIndexTask.id.desc())
        )
        assert task is not None
        assert task.operation == "delete"
    restore = client.post(
        f"/api/v1/admin/trash/article/{published['id']}/restore",
        headers=headers,
    )
    assert restore.status_code == 200
    trashed_again = client.delete(f"/api/v1/admin/articles/{published['id']}", headers=headers)
    assert trashed_again.status_code == 204
    purge = client.delete(
        f"/api/v1/admin/trash/article/{published['id']}",
        headers=headers,
    )
    assert purge.status_code == 204
    with _session(client) as db:
        tombstone = db.scalar(
            select(AssistantIndexTask)
            .where(
                AssistantIndexTask.source_id == published["id"],
                AssistantIndexTask.operation == OP_PURGE,
            )
            .order_by(AssistantIndexTask.id.desc())
        )
        assert tombstone is not None
        assert tombstone.target_version is not None
        assert db.get(Article, published["id"]) is None


def test_profile_and_taxonomy_name_changes_enqueue_tasks(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    category = client.post(
        "/api/v1/admin/categories",
        json={"name": "Observability", "slug": "observability"},
        headers=headers,
    ).json()
    article = publish_article(
        client,
        client.post(
            "/api/v1/admin/articles",
            json={
                "title": "Taxonomy indexed",
                "slug": "taxonomy-indexed",
                "content": "# Body",
                "category_id": category["id"],
                "tag_ids": [],
            },
            headers=headers,
        ).json(),
        headers,
    ).json()
    renamed = client.patch(
        f"/api/v1/admin/categories/{category['id']}",
        json={"name": "Telemetry"},
        headers=headers,
    )
    assert renamed.status_code == 200
    profile = client.patch(
        "/api/v1/admin/profile",
        json={
            "name": "Gavin",
            "title": "Engineer",
            "bio": "Updated public bio",
            "skills": ["Python"],
            "city_visible": False,
            "email_visible": False,
            "version": 1,
        },
        headers=headers,
    )
    assert profile.status_code == 200
    with _session(client) as db:
        article_tasks = list(
            db.scalars(
                select(AssistantIndexTask).where(
                    AssistantIndexTask.source_type == SOURCE_ARTICLE,
                    AssistantIndexTask.source_id == article["id"],
                )
            ).all()
        )
        assert article_tasks
        profile_task = db.scalar(
            select(AssistantIndexTask).where(AssistantIndexTask.source_type == SOURCE_PROFILE)
        )
        assert profile_task is not None
        assert profile_task.target_version == str(profile.json()["version"])


def test_worker_rebuild_retriever_and_staleness(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    first = publish_article(
        client,
        client.post(
            "/api/v1/admin/articles",
            json={
                "title": "Alpha retrieval",
                "slug": "alpha-retrieval",
                "content": "# UniqueAlphaToken appears here",
            },
            headers=headers,
        ).json(),
        headers,
    ).json()
    clock = FakeClock()
    start = clock.now
    runtime = _runtime(client, clock=clock)
    _activate_ready_generation(client, runtime)
    elapsed = clock.now - start
    assert elapsed < timedelta(minutes=5)
    with _session(client) as db:
        result = retrieve(db, runtime, "UniqueAlphaToken")
        assert result.status == "ok"
        chunks = _result_chunks(db, result)
        article_chunks = [chunk for chunk in chunks if chunk.source_type == SOURCE_ARTICLE]
        assert article_chunks
        chunk = article_chunks[0]
        assert chunk.source_version == str(first["current_revision_id"])
        collection_name = chunk.generation.collection_name
        assert chunk.chunk_id in runtime.store.chunk_ids(collection_name)
        payload_records, _offset = runtime.store.client.scroll(
            collection_name=collection_name,
            limit=20,
            with_payload=True,
            with_vectors=False,
        )
        for record in payload_records:
            payload = record.payload or {}
            assert set(payload) <= set(PAYLOAD_ALLOWLIST)
            assert "page_content" not in payload
            assert "title" not in payload

    updated = client.patch(
        f"/api/v1/admin/articles/{first['id']}",
        json={
            "title": "Alpha retrieval",
            "content": "# UniqueBetaToken replaced the old unique token",
            "version": first["version"],
        },
        headers=headers,
    ).json()
    second = publish_article(client, updated, headers).json()
    assert second["current_revision_id"] != first["current_revision_id"]
    with _session(client) as db:
        stale = retrieve(db, runtime, "UniqueAlphaToken")
        stale_articles = [
            chunk
            for chunk in _result_chunks(db, stale)
            if chunk.source_type == SOURCE_ARTICLE and chunk.source_id == first["id"]
        ]
        assert stale_articles == []
        current = project_source(db, SOURCE_ARTICLE, first["id"])
        assert current is not None
        assert current.source_version == str(second["current_revision_id"])

    process_once(runtime)
    with _session(client) as db:
        fresh = retrieve(db, runtime, "UniqueBetaToken")
        assert fresh.candidates
        enqueue_task(
            db,
            source_type=SOURCE_ARTICLE,
            source_id=first["id"],
            target_version=str(first["current_revision_id"]),
            operation="upsert",
        )
        db.commit()
    process_once(runtime)
    with _session(client) as db:
        after_old = retrieve(db, runtime, "UniqueAlphaToken")
        assert [
            chunk
            for chunk in _result_chunks(db, after_old)
            if chunk.source_type == SOURCE_ARTICLE
            and chunk.source_version == str(first["current_revision_id"])
        ] == []
        still_new = retrieve(db, runtime, "UniqueBetaToken")
        assert [
            chunk
            for chunk in _result_chunks(db, still_new)
            if chunk.source_type == SOURCE_ARTICLE
            and chunk.source_version == str(second["current_revision_id"])
        ]
        task_states = {row.status for row in db.scalars(select(AssistantIndexTask)).all()}
        assert STATUS_SUCCEEDED in task_states

    client.delete(f"/api/v1/admin/articles/{first['id']}", headers=headers)
    with _session(client) as db:
        hidden = retrieve(db, runtime, "UniqueBetaToken")
        assert [
            chunk
            for chunk in _result_chunks(db, hidden)
            if chunk.source_type == SOURCE_ARTICLE and chunk.source_id == first["id"]
        ] == []
    process_once(runtime)

    for collection in list(runtime.store.client.get_collections().collections):
        runtime.store.delete_collection(collection.name)
    _activate_ready_generation(client, runtime)
    with _session(client) as db:
        profile_hits = retrieve(db, runtime, "Gavin")
        assert profile_hits.status in {"ok", "degraded"}


def test_retriever_degrades_without_dense_and_is_not_ready_without_fts(
    client: TestClient,
) -> None:
    runtime = _runtime(client)
    with _session(client) as db:
        empty = retrieve(db, runtime, "anything")
        assert empty.status == "not_ready"
        assert empty.candidates == []
    _activate_ready_generation(client, runtime)
    broken = _runtime(client)
    broken.store.search = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("qdrant down"))  # type: ignore[method-assign]
    with _session(client) as db:
        degraded = retrieve(db, broken, "Gavin")
        assert degraded.status == "degraded"
        assert degraded.degraded is True
        db.execute(text("DROP TABLE assistant_chunk_fts"))
        missing = retrieve(db, broken, "Gavin")
        assert missing.status == "not_ready"
        assert missing.candidates == []


def _lexical_recall(connection: sqlite3.Connection, query: str) -> set[str]:
    """Replay the retrieval match order against a real FTS5 table."""
    for match in (
        lexical_match_query(query),
        lexical_fallback_query(query),
        safe_match_query(query),
    ):
        if not match:
            continue
        rows = {
            str(row[0])
            for row in connection.execute(
                "SELECT chunk_id FROM assistant_chunk_fts "
                "WHERE assistant_chunk_fts MATCH ? AND generation_id = 1",
                (match,),
            )
        }
        if rows:
            return rows
    return set()


def test_lexical_projection_recalls_chinese_substrings_and_natural_questions() -> None:
    """G08: unicode61 stores a CJK run as one token, so substring questions miss it."""
    connection = sqlite3.connect(":memory:")
    try:
        connection.executescript(ASSISTANT_FTS_SQL)
        documents = {
            "c1": "系统支持全文检索和向量检索。",
            "c2": "retry handles transient failures",
            "c3": "访问数组 a[1] 与令牌 x_api_key。",
        }
        for chunk_id, body in documents.items():
            connection.execute(
                "INSERT INTO assistant_chunk_fts"
                "(chunk_id, generation_id, title, heading_path, body) VALUES (?,?,?,?,?)",
                (
                    chunk_id,
                    1,
                    lexical_index_text("笔记"),
                    lexical_index_text("说明"),
                    lexical_index_text(body),
                ),
            )

        assert _lexical_recall(connection, "向量检索") == {"c1"}
        assert _lexical_recall(connection, "全文检索") == {"c1"}
        assert _lexical_recall(connection, "系统支持全文检索和向量检索") == {"c1"}
        assert _lexical_recall(connection, "How does retry work?") == {"c2"}
        assert _lexical_recall(connection, "retry") == {"c2"}
        assert _lexical_recall(connection, "数组 a[1]") == {"c3"}
        assert _lexical_recall(connection, "x_api_key") == {"c3"}
        assert _lexical_recall(connection, "自动驾驶") == set()
    finally:
        connection.close()


def test_legacy_fts_rows_stay_queryable_until_the_index_is_rebuilt() -> None:
    """Rows written before the lexical projection keep their previous recall."""
    connection = sqlite3.connect(":memory:")
    try:
        connection.executescript(ASSISTANT_FTS_SQL)
        for chunk_id, body in {
            "c1": "系统支持全文检索和向量检索。",
            "c2": "retry handles transient failures",
        }.items():
            connection.execute(
                "INSERT INTO assistant_chunk_fts"
                "(chunk_id, generation_id, title, heading_path, body) VALUES (?,?,?,?,?)",
                (chunk_id, 1, "笔记", "说明", body),
            )

        assert _lexical_recall(connection, "系统支持全文检索和向量检索") == {"c1"}
        assert _lexical_recall(connection, "retry") == {"c2"}
        assert _lexical_recall(connection, "向量检索") == set()
    finally:
        connection.close()


def test_retriever_recalls_a_chinese_substring_from_the_real_index(client: TestClient) -> None:
    headers = {"X-CSRF-Token": login(client)}
    article = client.post(
        "/api/v1/admin/articles",
        headers=headers,
        json={
            "title": "检索说明",
            "slug": "lexical-retrieval",
            "content": "# 检索\n\n系统支持全文检索和向量检索。",
        },
    ).json()
    assert publish_article(client, article, headers).status_code == 200
    runtime = _runtime(client)
    _activate_ready_generation(client, runtime)
    with _session(client) as db:
        matched = retrieve(db, runtime, "向量检索")
        assert matched.status in {"ok", "degraded"}
        assert any("fts" in candidate.sources for candidate in matched.candidates)
        assert any(
            chunk.source_type == SOURCE_ARTICLE for chunk in _result_chunks(db, matched)
        )


def test_worker_owner_is_singleton_and_fence_advances_after_expiry(client: TestClient) -> None:
    clock = FakeClock()
    first = _runtime(client, clock=clock)
    first.owner = "worker-a"
    second = _runtime(client, clock=clock)
    second.owner = "worker-b"
    assert process_once(first) is False
    assert process_once(second) is False
    with _session(client) as db:
        initial = db.get(AssistantIndexWorkerState, 1)
        assert initial is not None
        initial_fence = initial.fencing_token
        assert initial.owner_id == "worker-a"
    clock.advance(first.settings.assistant_index_lease_seconds + 1)
    assert process_once(second) is False
    with _session(client) as db:
        taken_over = db.get(AssistantIndexWorkerState, 1)
        assert taken_over is not None
        assert taken_over.owner_id == "worker-b"
        assert taken_over.fencing_token == initial_fence + 1
    assert process_once(first) is False


def test_embeddings_are_deterministic_and_worker_fails_closed() -> None:
    first = DeterministicHashEmbeddings(
        dimension=32,
        model="deterministic-hash",
        version="test-v1",
    )
    second = DeterministicHashEmbeddings(
        dimension=32,
        model="deterministic-hash",
        version="test-v1",
    )
    assert first.embed_query("hello") == second.embed_query("hello")
    production = Settings(
        environment="production",
        admin_password="a-strong-production-password",
        assistant_index_worker_enabled=True,
        assistant_embedding_provider=TEST_EMBEDDING_PROVIDER,
        assistant_embedding_model=TEST_EMBEDDING_MODEL,
        assistant_embedding_model_version=TEST_EMBEDDING_MODEL_VERSION,
        assistant_embedding_dimension=32,
        _env_file=None,
    )
    with pytest.raises(AssistantIndexConfigurationError, match="not allowed in production"):
        validate_assistant_worker_settings(production)
    missing = Settings(
        environment="test",
        admin_password="configured",
        cookie_secure=False,
        assistant_index_worker_enabled=True,
        _env_file=None,
    )
    with pytest.raises(AssistantIndexConfigurationError):
        validate_assistant_worker_settings(missing)
    unknown = Settings(
        environment="production",
        admin_password="a-strong-production-password",
        assistant_index_worker_enabled=True,
        assistant_embedding_provider="openai",
        assistant_embedding_model="text-embedding-3-small",
        assistant_embedding_model_version="1",
        assistant_embedding_dimension=1536,
        assistant_embedding_endpoint="https://example.invalid",
        assistant_embedding_api_key="sk-test",
        assistant_qdrant_url="https://qdrant.internal",
        assistant_qdrant_api_key="qdrant-key",
        _env_file=None,
    )
    with pytest.raises(AssistantIndexConfigurationError, match="not implemented"):
        validate_assistant_worker_settings(unknown)
    disabled = Settings(
        environment="test",
        admin_password="configured",
        cookie_secure=False,
        assistant_index_worker_enabled=False,
        _env_file=None,
    )
    with pytest.raises(AssistantIndexConfigurationError, match="disabled"):
        validate_assistant_worker_settings(disabled)
    assert main(["--once"]) == 1


def test_existing_search_and_openapi_are_unchanged_by_assistant_index(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    publish_article(
        client,
        client.post(
            "/api/v1/admin/articles",
            json={
                "title": "Search stays",
                "slug": "search-stays",
                "content": "# Site search token",
            },
            headers=headers,
        ).json(),
        headers,
    )
    response = client.get("/api/v1/search", params={"q": "search"})
    assert response.status_code == 200
    assert response.json()
    paths = client.app.openapi()["paths"]
    assert not any("qdrant" in path or "retriev" in path for path in paths)
    assert "/api/v1/search" in paths
    assert "/api/v1/assistant/sessions" in paths
    assert "/api/v1/assistant/questions" in paths
