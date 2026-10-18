from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.article_revisions import create_publish_revision
from app.content_revisions import (
    create_book_note_publish_revision,
    create_project_publish_revision,
)
from app.models import Article, BookNote, MediaAsset, Project

from .conftest import login


def seed_paginated_content(client: TestClient) -> None:
    timestamp = datetime(2026, 8, 1, 12, tzinfo=UTC)
    with client.app.state.database.session_factory() as db:
        for index in range(25):
            article = Article(
                title=f"Article {index:02d}",
                slug=f"article-{index:02d}",
                content="# Bounded pagination",
                status="published",
                published_at=timestamp,
                updated_at=timestamp,
            )
            db.add(article)
            db.flush()
            create_publish_revision(db, article)
        for index in range(3):
            project = Project(
                title=f"Project {index}",
                slug=f"project-{index}",
                content="# Project",
                status="published",
                published_at=timestamp,
                updated_at=timestamp,
            )
            note = BookNote(
                book_title=f"Book {index}",
                author="Author",
                slug=f"book-{index}",
                content="# Book",
                status="published",
                published_at=timestamp,
                updated_at=timestamp,
            )
            db.add_all([project, note])
            db.flush()
            create_project_publish_revision(db, project, published_at=timestamp)
            create_book_note_publish_revision(db, note, published_at=timestamp)
            db.add(
                MediaAsset(
                    source="external",
                    original_name=f"media-{index}",
                    mime_type="image/external",
                    url=f"https://example.com/{index}.png",
                    created_at=timestamp,
                )
            )
        db.commit()


def test_content_lists_are_bounded_and_stably_paginated(client: TestClient) -> None:
    seed_paginated_content(client)
    login(client)

    first = client.get("/api/v1/articles")
    second = client.get("/api/v1/articles", params={"limit": 5, "offset": 20})
    admin = client.get("/api/v1/admin/articles", params={"limit": 2, "offset": 1})

    assert first.status_code == 200
    assert len(first.json()) == 20
    assert [item["id"] for item in first.json()] == list(range(25, 5, -1))
    assert [item["id"] for item in second.json()] == list(range(5, 0, -1))
    assert [item["id"] for item in admin.json()] == [24, 23]

    assert len(client.get("/api/v1/projects", params={"limit": 1}).json()) == 1
    assert len(client.get("/api/v1/books", params={"limit": 1}).json()) == 1
    assert len(client.get("/api/v1/admin/projects", params={"limit": 1}).json()) == 1
    assert len(client.get("/api/v1/admin/books", params={"limit": 1}).json()) == 1
    assert len(client.get("/api/v1/admin/media", params={"limit": 1}).json()) == 1


def test_trash_uses_global_stable_pagination(client: TestClient) -> None:
    timestamp = datetime(2026, 8, 1, 12, tzinfo=UTC)
    with client.app.state.database.session_factory() as db:
        db.add_all(
            [
                Article(title="Article", slug="trash-article", deleted_at=timestamp),
                Project(title="Project", slug="trash-project", deleted_at=timestamp),
                BookNote(
                    book_title="Book",
                    author="Author",
                    slug="trash-book",
                    deleted_at=timestamp,
                ),
            ]
        )
        db.commit()
    login(client)

    first = client.get("/api/v1/admin/trash", params={"limit": 2}).json()
    second = client.get("/api/v1/admin/trash", params={"limit": 2, "offset": 2}).json()

    assert [(item["content_type"], item["content_id"]) for item in first + second] == [
        ("article", 1),
        ("book", 1),
        ("project", 1),
    ]


@pytest.mark.parametrize(
    ("path", "params"),
    [
        ("/api/v1/articles", {"limit": 0}),
        ("/api/v1/projects", {"limit": 101}),
        ("/api/v1/books", {"offset": -1}),
        ("/api/v1/admin/articles", {"offset": 100_001}),
        ("/api/v1/admin/projects", {"limit": 0}),
        ("/api/v1/admin/books", {"limit": 101}),
        ("/api/v1/admin/media", {"offset": -1}),
        ("/api/v1/admin/trash", {"limit": 101}),
        ("/api/v1/search", {"q": "bounded", "limit": 51}),
        ("/api/v1/search", {"q": "bounded", "offset": 100_001}),
    ],
)
def test_list_boundaries_reject_invalid_windows(
    client: TestClient,
    path: str,
    params: dict[str, int | str],
) -> None:
    login(client)
    assert client.get(path, params=params).status_code == 422


def test_search_supports_offset_without_duplicate_results(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    for index in range(3):
        created = client.post(
            "/api/v1/admin/articles",
            json={
                "title": f"Bounded result {index}",
                "slug": f"bounded-result-{index}",
                "content": "# Bounded",
            },
            headers=headers,
        ).json()
        response = client.post(
            f"/api/v1/admin/articles/{created['id']}/publish",
            json={"version": created["version"]},
            headers=headers,
        )
        assert response.status_code == 200

    first = client.get("/api/v1/search", params={"q": "Bounded", "limit": 1}).json()
    second = client.get(
        "/api/v1/search",
        params={"q": "Bounded", "limit": 1, "offset": 1},
    ).json()

    assert len(first) == len(second) == 1
    assert first[0]["content_id"] != second[0]["content_id"]
