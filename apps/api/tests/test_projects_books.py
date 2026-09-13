from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from .conftest import login


@pytest.mark.parametrize(
    ("endpoint", "payload", "renamed_slug"),
    [
        ("articles", {"title": "Draft article", "slug": "draft-article"}, "draft-article-2"),
        ("projects", {"title": "Draft project", "slug": "draft-project"}, "draft-project-2"),
        (
            "books",
            {"book_title": "Draft book", "author": "Author", "slug": "draft-book"},
            "draft-book-2",
        ),
    ],
)
def test_draft_slugs_remain_editable(
    client: TestClient,
    endpoint: str,
    payload: dict[str, str],
    renamed_slug: str,
) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    created = client.post(f"/api/v1/admin/{endpoint}", json=payload, headers=headers)
    assert created.status_code == 201

    updated = client.patch(
        f"/api/v1/admin/{endpoint}/{created.json()['id']}",
        json={"slug": renamed_slug, "version": created.json()["version"]},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["slug"] == renamed_slug


def create_article(
    client: TestClient,
    headers: dict[str, str],
    slug: str,
    publish: bool,
) -> dict:
    response = client.post(
        "/api/v1/admin/articles",
        json={"title": slug.replace("-", " ").title(), "slug": slug, "content": "# Article"},
        headers=headers,
    )
    assert response.status_code == 201
    article = response.json()
    if publish:
        published = client.post(
            f"/api/v1/admin/articles/{article['id']}/publish",
            json={"version": article["version"]},
            headers=headers,
        )
        assert published.status_code == 200
        return published.json()
    return article


def test_project_draft_autosave_publish_and_related_article_visibility(
    client: TestClient,
) -> None:
    assert client.get("/api/v1/admin/projects").status_code == 401
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    published_article = create_article(client, headers, "public-project-note", True)
    draft_article = create_article(client, headers, "draft-project-note", False)

    invalid = client.post(
        "/api/v1/admin/projects",
        json={"title": "Invalid", "slug": "invalid-project", "article_ids": [9999]},
        headers=headers,
    )
    assert invalid.status_code == 422

    created = client.post(
        "/api/v1/admin/projects",
        json={
            "title": "Gavin Blog",
            "slug": "gavin-blog",
            "summary": "A verified knowledge publication.",
            "content": "# Project draft",
            "repository_url": "https://github.com/example/gavin-blog",
            "website_url": "https://example.com",
            "article_ids": [published_article["id"], draft_article["id"]],
        },
        headers=headers,
    )
    assert created.status_code == 201
    project = created.json()
    assert project["article_ids"] == [published_article["id"], draft_article["id"]]
    assert client.get("/api/v1/projects").json() == []
    assert client.get("/api/v1/projects/gavin-blog").status_code == 404

    saved = client.patch(
        f"/api/v1/admin/projects/{project['id']}",
        json={
            "content": "# Published project\n\nA complete case study.",
            "version": project["version"],
        },
        headers=headers,
    )
    assert saved.status_code == 200
    assert saved.json()["version"] == project["version"] + 1
    conflict = client.patch(
        f"/api/v1/admin/projects/{project['id']}",
        json={"summary": "stale", "version": project["version"]},
        headers=headers,
    )
    assert conflict.status_code == 409

    published = client.post(
        f"/api/v1/admin/projects/{project['id']}/publish",
        json={"version": saved.json()["version"]},
        headers=headers,
    )
    assert published.status_code == 200
    assert published.json()["public_path"] == "/projects/gavin-blog"
    assert published.json()["current_publish_revision"] == 1
    assert not published.json()["has_unpublished_changes"]
    public = client.get("/api/v1/projects/gavin-blog")
    assert public.status_code == 200
    assert len(client.get("/api/v1/search", params={"q": "verified"}).json()) == 1
    assert [article["slug"] for article in public.json()["related_articles"]] == [
        "public-project-note"
    ]
    article_working = client.patch(
        f"/api/v1/admin/articles/{published_article['id']}",
        json={
            "title": "UNPUBLISHED article title",
            "summary": "UNPUBLISHED article summary",
            "version": published_article["version"],
        },
        headers=headers,
    )
    assert article_working.status_code == 200
    related = client.get("/api/v1/projects/gavin-blog").json()["related_articles"][0]
    assert related["title"] == "Public Project Note"
    assert related["summary"] == ""
    locked_slug = client.patch(
        f"/api/v1/admin/projects/{project['id']}",
        json={"slug": "renamed-project", "version": published.json()["version"]},
        headers=headers,
    )
    assert locked_slug.status_code == 409
    updated = client.patch(
        f"/api/v1/admin/projects/{project['id']}",
        json={
            "summary": "Updated without moving the URL",
            "article_ids": [],
            "version": published.json()["version"],
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["public_path"] == "/projects/gavin-blog"
    assert updated.json()["has_unpublished_changes"]
    assert client.get("/api/v1/search", params={"q": "Updated"}).json() == []
    public_before_republish = client.get("/api/v1/projects/gavin-blog").json()
    assert public_before_republish["summary"] == "A verified knowledge publication."
    assert len(public_before_republish["related_articles"]) == 1
    stale_publish = client.post(
        f"/api/v1/admin/projects/{project['id']}/publish",
        json={"version": published.json()["version"]},
        headers=headers,
    )
    assert stale_publish.status_code == 409
    republished = client.post(
        f"/api/v1/admin/projects/{project['id']}/publish",
        json={"version": updated.json()["version"]},
        headers=headers,
    )
    assert republished.status_code == 200
    assert republished.json()["current_publish_revision"] == 2
    assert not republished.json()["has_unpublished_changes"]
    public_after_republish = client.get("/api/v1/projects/gavin-blog").json()
    assert public_after_republish["summary"] == "Updated without moving the URL"
    assert public_after_republish["related_articles"] == []
    assert len(client.get("/api/v1/search", params={"q": "Updated"}).json()) == 1


def test_book_note_fields_validation_autosave_publish_and_public_read(
    client: TestClient,
) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}

    invalid_status = client.post(
        "/api/v1/admin/books",
        json={
            "book_title": "Invalid",
            "author": "Nobody",
            "slug": "invalid-status",
            "reading_status": "unknown",
        },
        headers=headers,
    )
    assert invalid_status.status_code == 422
    invalid_rating = client.post(
        "/api/v1/admin/books",
        json={
            "book_title": "Invalid",
            "author": "Nobody",
            "slug": "invalid-rating",
            "rating": 6,
        },
        headers=headers,
    )
    assert invalid_rating.status_code == 422

    created = client.post(
        "/api/v1/admin/books",
        json={
            "book_title": "Designing Data-Intensive Applications",
            "author": "Martin Kleppmann",
            "slug": "designing-data-intensive-applications",
            "cover_url": "https://example.com/ddia.webp",
            "reading_status": "reading",
            "reading_date": "2026-08-01",
            "rating": 5,
            "summary": "Notes on reliable data systems.",
            "content": "# Book draft",
        },
        headers=headers,
    )
    assert created.status_code == 201
    note = created.json()
    assert note["reading_status"] == "reading"
    assert client.get("/api/v1/books").json() == []

    saved = client.patch(
        f"/api/v1/admin/books/{note['id']}",
        json={
            "reading_status": "completed",
            "content": "# Finished\n\nDurability needs explicit trade-offs.",
            "version": note["version"],
        },
        headers=headers,
    )
    assert saved.status_code == 200
    assert saved.json()["reading_status"] == "completed"
    conflict = client.patch(
        f"/api/v1/admin/books/{note['id']}",
        json={"summary": "stale", "version": note["version"]},
        headers=headers,
    )
    assert conflict.status_code == 409

    published = client.post(
        f"/api/v1/admin/books/{note['id']}/publish",
        json={"version": saved.json()["version"]},
        headers=headers,
    )
    assert published.status_code == 200
    published_payload = published.json()
    assert published_payload["current_publish_revision"] == 1
    public_path = published_payload["public_path"]
    # The book path is scoped to the month of first publication, so derive the
    # prefix from the response instead of pinning a wall-clock month.
    month_prefix = f"/books/{published_payload['published_at'][:7].replace('-', '/')}/"
    assert public_path.startswith(month_prefix)
    assert public_path.endswith("/designing-data-intensive-applications")
    public = client.get(public_path.replace("/books/", "/api/v1/books/"))
    assert public.status_code == 200
    assert public.json()["author"] == "Martin Kleppmann"
    assert len(client.get("/api/v1/search", params={"q": "reliable"}).json()) == 1
    assert len(client.get("/api/v1/books").json()) == 1
    locked_slug = client.patch(
        f"/api/v1/admin/books/{note['id']}",
        json={"slug": "renamed-book", "version": published.json()["version"]},
        headers=headers,
    )
    assert locked_slug.status_code == 409
    updated = client.patch(
        f"/api/v1/admin/books/{note['id']}",
        json={"summary": "Updated without moving the URL", "version": published.json()["version"]},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["public_path"] == public_path
    assert updated.json()["has_unpublished_changes"]
    assert client.get("/api/v1/search", params={"q": "Updated"}).json() == []
    public_before_republish = client.get(public_path.replace("/books/", "/api/v1/books/"))
    assert public_before_republish.json()["summary"] == "Notes on reliable data systems."
    stale_publish = client.post(
        f"/api/v1/admin/books/{note['id']}/publish",
        json={"version": published.json()["version"]},
        headers=headers,
    )
    assert stale_publish.status_code == 409
    republished = client.post(
        f"/api/v1/admin/books/{note['id']}/publish",
        json={"version": updated.json()["version"]},
        headers=headers,
    )
    assert republished.status_code == 200
    assert republished.json()["current_publish_revision"] == 2
    assert not republished.json()["has_unpublished_changes"]
    public_after_republish = client.get(public_path.replace("/books/", "/api/v1/books/"))
    assert public_after_republish.json()["summary"] == "Updated without moving the URL"
    assert len(client.get("/api/v1/search", params={"q": "Updated"}).json()) == 1


def test_project_and_book_mutations_require_csrf(client: TestClient) -> None:
    login(client)
    project = client.post(
        "/api/v1/admin/projects",
        json={"title": "No CSRF", "slug": "project-no-csrf"},
    )
    book = client.post(
        "/api/v1/admin/books",
        json={"book_title": "No CSRF", "author": "Nobody", "slug": "book-no-csrf"},
    )
    assert project.status_code == 403
    assert book.status_code == 403


def test_book_cover_accepts_site_media_path_and_keeps_http_urls(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    created = client.post(
        "/api/v1/admin/books",
        json={
            "book_title": "Cover contract book",
            "author": "Author",
            "slug": "cover-contract-book",
            "cover_url": "/api/v1/media/14/webp",
        },
        headers=headers,
    )
    assert created.status_code == 201
    book = created.json()
    assert book["cover_url"] == "/api/v1/media/14/webp"
    assert client.get(f"/api/v1/admin/books/{book['id']}").json()["cover_url"] == (
        "/api/v1/media/14/webp"
    )

    external = client.patch(
        f"/api/v1/admin/books/{book['id']}",
        json={"cover_url": "https://example.com/cover.jpg", "version": book["version"]},
        headers=headers,
    )
    assert external.status_code == 200
    assert external.json()["cover_url"] == "https://example.com/cover.jpg"
    version = external.json()["version"]

    rejected_covers = [
        "/api/v1/media/0/webp",
        "/api/v1/media/14/png",
        "/api/v1/media/14/webp?size=large",
        "/etc/passwd",
        "//cdn.example.com/cover.webp",
        "ftp://example.com/cover.webp",
        "javascript:alert(1)",
    ]
    for cover in rejected_covers:
        rejected = client.patch(
            f"/api/v1/admin/books/{book['id']}",
            json={"cover_url": cover, "version": version},
            headers=headers,
        )
        assert rejected.status_code == 422, cover

    cleared = client.patch(
        f"/api/v1/admin/books/{book['id']}",
        json={"cover_url": None, "version": version},
        headers=headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["cover_url"] is None
