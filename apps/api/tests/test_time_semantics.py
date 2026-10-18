from __future__ import annotations

import io
import zipfile
from datetime import UTC, datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.article_revisions import create_publish_revision
from app.models import Article
from app.search import ensure_search_table
from app.security import SESSION_COOKIE, token_hash
from app.time_utils import as_utc, utc_now

from .conftest import login


def assert_utc_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timedelta(0)
    return parsed


def test_utc_helpers_are_aware_and_treat_legacy_values_as_utc() -> None:
    current = utc_now()
    assert current.tzinfo is UTC
    assert as_utc(datetime(2026, 1, 2, 3, 4, 5)) == datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def test_sqlite_normalizes_offsets_and_public_paths_use_utc_calendar(
    client: TestClient,
) -> None:
    shanghai = timezone(timedelta(hours=8))
    with client.app.state.database.session_factory() as db:
        article = Article(
            title="UTC boundary",
            slug="utc-boundary",
            content="# UTC",
            status="published",
            published_at=datetime(2026, 1, 1, 0, 30, tzinfo=shanghai),
        )
        db.add(article)
        db.flush()
        create_publish_revision(db, article)
        db.commit()
        article_id = article.id

    with client.app.state.database.session_factory() as db:
        stored = db.get(Article, article_id)
        assert stored is not None
        assert stored.published_at == datetime(2025, 12, 31, 16, 30, tzinfo=UTC)
        assert stored.created_at.tzinfo is UTC

    public = client.get("/api/v1/articles/2025/12/utc-boundary")
    assert public.status_code == 200
    assert_utc_timestamp(public.json()["published_at"])
    assert client.get("/api/v1/articles/2026/01/utc-boundary").status_code == 404


def test_legacy_naive_session_expiry_is_compared_as_utc(client: TestClient) -> None:
    raw_token = "legacy-expired-session"
    with client.app.state.database.engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO admin_sessions
                (token_hash, csrf_hash, expires_at, created_at, public_id, last_seen_at)
                VALUES (:token_hash, :csrf_hash, :expires_at, :created_at, 'legacy', :created_at)
                """
            ),
            {
                "token_hash": token_hash(raw_token),
                "csrf_hash": "0" * 64,
                "expires_at": "2000-01-01 00:00:00.000000",
                "created_at": "1999-12-31 00:00:00.000000",
            },
        )
    client.cookies.set(SESSION_COOKIE, raw_token)

    response = client.get("/api/v1/admin/articles")

    assert response.status_code == 401
    assert response.json()["detail"] == "session expired"


def test_api_search_and_markdown_export_include_utc_offsets(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    created = client.post(
        "/api/v1/admin/articles",
        json={
            "title": "UTC serialization",
            "slug": "utc-serialization",
            "content": "# Explicit time",
        },
        headers=headers,
    )
    assert created.status_code == 201
    assert_utc_timestamp(created.json()["created_at"])
    published = client.post(
        f"/api/v1/admin/articles/{created.json()['id']}/publish",
        json={"version": created.json()["version"]},
        headers=headers,
    )
    assert published.status_code == 200
    assert_utc_timestamp(published.json()["published_at"])
    assert_utc_timestamp(published.json()["updated_at"])

    search = client.get("/api/v1/search", params={"q": "UTC serialization"})
    assert search.status_code == 200
    assert len(search.json()) == 1
    assert_utc_timestamp(search.json()[0]["published_at"])

    exported = client.get("/api/v1/admin/exports/markdown")
    assert exported.status_code == 200
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        document = archive.read("articles/utc-serialization.md").decode()
    assert "+00:00" in document


def test_legacy_search_timestamp_is_returned_as_utc(client: TestClient) -> None:
    with client.app.state.database.session_factory() as db:
        ensure_search_table(db)
        db.execute(
            text(
                """
                INSERT INTO search_index (
                    content_type, content_id, title, summary, body,
                    taxonomy, public_path, published_at
                ) VALUES (
                    'article', 999, 'Legacy UTC search', '', 'legacy body',
                    '', '/notes/2026/01/legacy-utc-search', '2026-01-01T00:00:00'
                )
                """
            )
        )
        db.commit()

    response = client.get("/api/v1/search", params={"q": "Legacy UTC"})

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert_utc_timestamp(response.json()[0]["published_at"])
