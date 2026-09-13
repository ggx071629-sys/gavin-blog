from __future__ import annotations

import base64
import hashlib
import json
import struct
import threading
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import OpenAI
from tokenizers import Tokenizer, models

from app.local_embedding import artifact
from app.local_embedding.artifact import MODEL, PIPELINE, VERSION
from app.local_embedding.client import E5Embeddings
from app.local_embedding.service import create_app, identity
from app.local_embedding.tokenization import E5Tokenizer

KEY = "test-internal-key-24-characters"


@pytest.fixture
def tokenizer(tmp_path, monkeypatch):
    # Tiny character BPE artifact: no model/network dependency in contract tests.
    vocab = {
        char: i
        for i, char in enumerate(
            dict.fromkeys(
                "[UNK] query: passage:abcdefghijklmnopqrstuvwxyz"
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                "作者中文标题技术项目当前问题历史尾部代码\n#你好你好？，。-_*()<>/="
            )
        )
    }
    vocab["[UNK]"] = len(vocab)
    inner = Tokenizer(models.BPE(vocab=vocab, merges=[], unk_token="[UNK]"))
    inner.save(str(tmp_path / "tokenizer.json"))
    lock = tmp_path / "lock.json"
    lock.write_text(
        json.dumps(
            {
                "model": MODEL,
                "revision": artifact.REVISION,
                "files": {
                    "tokenizer.json": {"sha256": artifact.sha256(tmp_path / "tokenizer.json")}
                },
            }
        )
    )
    monkeypatch.setattr(artifact, "LOCK_PATH", lock)
    return E5Tokenizer(tmp_path)


class Encoder:
    def __init__(self):
        self.calls = []

    def count(self, text):
        return len(text) + 2

    def encode(self, text):
        self.calls.append(text)
        return [1.0] + [0.0] * 383


def test_artifact_hash_missing_and_changed_fail_closed(tmp_path, monkeypatch):
    path = tmp_path / "weights"
    path.write_bytes(b"fixed")
    lock = tmp_path / "lock.json"
    lock.write_text(
        json.dumps(
            {
                "model": MODEL,
                "revision": artifact.REVISION,
                "files": {"weights": {"sha256": hashlib.sha256(b"fixed").hexdigest()}},
            }
        )
    )
    monkeypatch.setattr(artifact, "LOCK_PATH", lock)
    artifact.verify_artifact(tmp_path)
    path.write_bytes(b"changed")
    with pytest.raises(RuntimeError, match="hash mismatch"):
        artifact.verify_artifact(tmp_path)
    path.unlink()
    with pytest.raises(RuntimeError, match="missing"):
        artifact.verify_artifact(tmp_path)


def test_service_contract_auth_usage_encoding_and_rejections():
    encoder = Encoder()
    with TestClient(create_app(encoder=encoder, api_key=KEY)) as client:
        headers = {"Authorization": "Bearer " + KEY}
        assert client.get("/healthz").json() == {"status": "alive"}
        assert client.get("/readyz").status_code == 401
        assert client.get("/readyz", headers=headers).json() == identity()
        payload = {"model": MODEL, "input": ["query: 中文 hello"], "dimensions": 384}
        assert client.post("/v1/embeddings", json=payload).status_code == 401
        response = client.post("/v1/embeddings", headers=headers, json=payload).json()
        assert response["usage"]["prompt_tokens"] == len(payload["input"][0]) + 2
        assert response["data"][0]["index"] == 0
        assert len(response["data"][0]["embedding"]) == 384
        response = client.post(
            "/v1/embeddings", headers=headers, json={**payload, "encoding_format": "base64"}
        ).json()
        assert (
            struct.unpack("<384f", base64.b64decode(response["data"][0]["embedding"]))
            == (1.0,) + (0.0,) * 383
        )
        for changed in [
            {"model": "wrong"},
            {"dimensions": 768},
            {"input": ["raw without role"]},
            {"input": ["query: "]},
            {"input": ["query: " + "a" * 512]},
            {"input": ["query: a", "passage: b"]},
            {"input": [42]},
        ]:
            assert client.post(
                "/v1/embeddings", headers=headers, json={**payload, **changed}
            ).status_code in {400, 422}
        assert len(encoder.calls) == 2
        sdk = OpenAI(api_key=KEY, base_url="http://testserver/v1", http_client=client)
        # The installed SDK defaults to base64; it must decode our response correctly.
        response = sdk.embeddings.create(model=MODEL, input=["query: 中文"], dimensions=384)
        assert response.data[0].embedding == [1.0] + [0.0] * 383
        assert len(encoder.calls) == 3


def test_service_single_inference_priority_queue_and_timeout():
    started, release = threading.Event(), threading.Event()

    class SlowEncoder(Encoder):
        def encode(self, text):
            if not self.calls:
                started.set()
                assert release.wait(5)
            return super().encode(text)

    encoder = SlowEncoder()
    app = create_app(encoder=encoder, api_key=KEY, queue_size=2, timeout=3)
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=4) as pool:

        def send(text):
            return client.post(
                "/v1/embeddings",
                headers={"Authorization": "Bearer " + KEY},
                json={"model": MODEL, "input": [text]},
            )

        first = pool.submit(send, "passage: first")
        assert started.wait(3)
        second = pool.submit(send, "passage: second")
        third = pool.submit(send, "query: third")

        # Wait on queue state through the service loop, not on assumed sleep timing.
        async def full():
            import asyncio

            for _ in range(1000):
                if app.state.queue.full():
                    return True
                await asyncio.sleep(0.001)
            return False

        try:
            assert client.portal.call(full)
            assert send("query: rejected").status_code == 429
        finally:
            release.set()
        assert all(f.result().status_code == 200 for f in [first, second, third])
        assert encoder.calls == ["passage: first", "query: third", "passage: second"]

    waiting, finish = threading.Event(), threading.Event()

    class DeadlineEncoder(Encoder):
        def encode(self, text):
            waiting.set()
            assert finish.wait(3)
            return super().encode(text)

    deadline_encoder = DeadlineEncoder()
    with TestClient(create_app(encoder=deadline_encoder, api_key=KEY, timeout=0.02)) as client:
        try:
            response = client.post(
                "/v1/embeddings",
                headers={"Authorization": "Bearer " + KEY},
                json={"model": MODEL, "input": ["query: deadline"]},
            )
            assert waiting.is_set()
            assert response.status_code == 504
        finally:
            finish.set()
    assert deadline_encoder.calls == ["query: deadline"]


def test_e5_adapter_roles_identity_and_usage(tokenizer):
    requests = []
    drift = False

    def respond(request):
        payload = json.loads(request.content)
        requests.append(payload)
        return httpx.Response(
            200,
            json={
                "object": "list",
                **identity(),
                "model_version": "wrong" if drift else VERSION,
                "data": [{"object": "embedding", "index": 0, "embedding": [1.0] + [0.0] * 383}],
                "usage": {
                    "prompt_tokens": tokenizer.count(payload["input"][0]),
                    "total_tokens": tokenizer.count(payload["input"][0]),
                },
            },
        )

    adapter = object.__new__(E5Embeddings)
    adapter.tokenizer = tokenizer
    adapter._client = OpenAI(
        api_key=KEY,
        base_url="http://localhost/v1",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(respond)),
    )
    assert adapter.embed_query_metered("中文").version_identity_source == "provider-response"
    adapter.embed_documents_metered(["hello", "中文"])
    assert [r["input"] for r in requests] == [
        ["query: 中文"],
        ["passage: hello"],
        ["passage: 中文"],
    ]
    assert all(r["encoding_format"] == "float" for r in requests)
    drift = True
    with pytest.raises(RuntimeError, match="identity"):
        adapter.embed_query("hello")
    before = len(requests)
    with pytest.raises(ValueError, match="512"):
        adapter.embed_query("a" * 600)
    assert len(requests) == before


def test_e5_chunks_preserve_content_versions_and_token_limit(tokenizer):
    from app.assistant_index.chunker import chunk_source
    from app.assistant_index.projector import SourceDocument

    body = "# 标题\n" + ("中文技术 hello code()\n" * 180) + "问题尾部"
    document = SourceDocument(
        "article", 1, "published-2", "title", "/notes/test", body, "hash", PIPELINE
    )
    drafts = chunk_source(document, chunk_size=384, chunk_overlap=64, tokenizer=tokenizer)
    assert len(drafts) > 2
    assert all(tokenizer.count("passage: " + d.page_content) <= 512 for d in drafts)
    assert all(tokenizer.count(d.page_content, special=False) <= 384 for d in drafts)
    assert all(d.heading_path == "标题" for d in drafts)
    assert drafts[-1].page_content.endswith("问题尾部")
    assert len({d.chunk_id for d in drafts}) == len(drafts)
    from dataclasses import replace

    revised = chunk_source(
        replace(document, source_version="published-3"),
        chunk_size=384,
        chunk_overlap=64,
        tokenizer=tokenizer,
    )
    assert {d.chunk_id for d in drafts}.isdisjoint({d.chunk_id for d in revised})


def test_e5_query_preserves_complete_current_and_lexical_degrades(tokenizer):
    current = "当前问题" + "a" * 475 + "尾部"
    query, skip = tokenizer.retrieval_query(current, ["b" * 300, "历史"])
    assert query.startswith(current) and "历史" in query
    assert not skip and tokenizer.count("query: " + query) <= 512
    current = "a" * 520 + "尾部"
    assert tokenizer.retrieval_query(current, ["历史"]) == (current, True)

    from app.assistant_index.retriever import _match_expressions

    history = "Tell me how the first project implements logging monitoring deployment backups security and caching"
    for current, previous, required in [
        ("Redis", [history], "Redis"),
        ("向量检索", [history], "向"),
        ("How does it retry?", [history, "Redis retry policy"], "retry"),
    ]:
        query, skip = tokenizer.retrieval_query(current, previous)
        assert not skip
        expressions = _match_expressions(query)
        assert expressions and all(required in expression for expression in expressions)
        if "it" in current:
            assert all("Redis" in expression for expression in expressions)


def test_graph_overlong_e5_query_skips_embedding_and_releases_reservation(tmp_path, monkeypatch):
    from .test_assistant_online import (
        _create_session,
        _online_client,
        _publish_and_index,
        _sse_body,
    )

    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        csrf = _create_session(client)
        online = client.app.state.assistant
        # A verbatim supported response isolates this runtime/query contract
        # from the separate heading-plus-first-person paraphrase limitation.
        from app.assistant.providers import ScriptedChatTurn

        quote = "I write about FastAPI, SQLite and published technical notes."
        online.chat.script.append(
            ScriptedChatTurn(
                parsed={
                    "blocks": [
                        {
                            "text": quote,
                            "citation_ids": ["c1"],
                            "supports": [{"citation_id": "c1", "quote": quote}],
                        }
                    ]
                }
            )
        )
        before = len(online.embeddings.calls)
        monkeypatch.setattr(
            online.embeddings,
            "prepare_retrieval_query",
            lambda question, history: (question, True),
            raising=False,
        )
        status, body = _sse_body(client, csrf, "FastAPI SQLite", idem="e5-overlong-query-0001")
        assert status == 200
        assert '"code":"answered_lexical"' in body.replace(" ", "")
        assert "问题较长，本次仅使用关键词检索公开资料" in body
        assert len(online.embeddings.calls) == before
        facts = online.control.read(
            lambda conn: (
                conn.execute(
                    "SELECT status, settled_micro FROM assistant_attempts "
                    "WHERE kind = 'query_embedding'"
                ).fetchall(),
                conn.execute(
                    "SELECT reserved_micro FROM assistant_query_embedding_budgets"
                ).fetchall(),
            )
        )
        assert all(row["status"] not in {"sending", "unknown"} for row in facts[0])
        assert all(row["settled_micro"] == 0 for row in facts[0])
        assert all(row["reserved_micro"] == 0 for row in facts[1])


def test_worker_rejects_embedding_into_old_generation_before_call():
    from types import SimpleNamespace

    from app.assistant_index.worker import _index_document

    runtime = SimpleNamespace(
        settings=SimpleNamespace(
            assistant_embedding_model=MODEL,
            assistant_embedding_model_version=VERSION,
            assistant_embedding_dimension=384,
            assistant_pipeline_version=PIPELINE,
        )
    )
    old = SimpleNamespace(
        embedding_model="old-model",
        embedding_model_version="old",
        vector_dimension=384,
        pipeline_version="old-pipeline",
    )
    with pytest.raises(RuntimeError, match="generation identity mismatch"):
        _index_document(None, runtime, old, None, fence=1, task_id=None, lease_token=None)


def test_repeated_rebuild_reuses_ready_staging(client):
    from sqlalchemy import func, select

    from app.assistant_index.worker import rebuild_generation
    from app.models import AssistantIndexCommand

    from .test_assistant_index import _runtime

    runtime = _runtime(client)
    first = rebuild_generation(runtime)
    assert rebuild_generation(runtime) == first
    with runtime.database.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(AssistantIndexCommand)) == 1


def test_local_mode_configuration_rejects_online_and_identity_drift(tmp_path, monkeypatch):
    from app.local_embedding.local import load_settings

    monkeypatch.setenv("GAVIN_ENVIRONMENT", "development")

    env = tmp_path / ".env"
    env.write_text(
        "GAVIN_ADMIN_PASSWORD=test\nGAVIN_ENVIRONMENT=development\n"
        "GAVIN_ASSISTANT_ONLINE_ENABLED=true\n"
    )
    with pytest.raises(ValueError, match="online_enabled=false"):
        load_settings(str(env))
    env.write_text("GAVIN_ADMIN_PASSWORD=test\nGAVIN_ENVIRONMENT=development\n")
    with pytest.raises(ValueError, match="pinned E5"):
        load_settings(str(env))


def test_service_owner_lock_prevents_second_process(tmp_path):
    import subprocess
    import sys

    from app.assistant.owner_lock import ExclusiveFileLock

    path = tmp_path / "owner.lock"
    with ExclusiveFileLock(path):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from pathlib import Path; from app.assistant.owner_lock import ExclusiveFileLock; "
                "import sys; ExclusiveFileLock(Path(sys.argv[1])).acquire()",
                str(path),
            ],
            capture_output=True,
            timeout=10,
        )
        assert result.returncode != 0
        assert b"held by another process" in result.stderr
    with ExclusiveFileLock(path):
        pass
