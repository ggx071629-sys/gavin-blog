from __future__ import annotations

from fastapi.testclient import TestClient

from .conftest import login, publish_article


def test_login_requires_csrf(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "gavin", "password": "correct-horse"},
    )
    assert response.status_code == 403


def test_login_rate_limit(client: TestClient) -> None:
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    for _ in range(3):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "gavin", "password": "wrong"},
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 401
    blocked = client.post(
        "/api/v1/auth/login",
        json={"username": "gavin", "password": "wrong"},
        headers={"X-CSRF-Token": csrf},
    )
    assert blocked.status_code == 429


def test_draft_autosave_publish_and_public_read(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    created = client.post(
        "/api/v1/admin/articles",
        json={
            "title": "Harness Engineering",
            "slug": "harness-engineering",
            "summary": "让 Agent 在清晰边界内工作。",
            "content": "# Draft",
        },
        headers=headers,
    )
    assert created.status_code == 201
    article = created.json()

    assert client.get("/api/v1/articles").json() == []
    missing = client.get("/api/v1/articles/2026/07/harness-engineering")
    assert missing.status_code == 404

    saved = client.patch(
        f"/api/v1/admin/articles/{article['id']}",
        json={
            "content": "# Published\n\nA complete article.",
            "version": article["version"],
        },
        headers=headers,
    )
    assert saved.status_code == 200
    saved_article = saved.json()
    assert saved_article["version"] == article["version"] + 1

    conflict = client.patch(
        f"/api/v1/admin/articles/{article['id']}",
        json={"summary": "stale write", "version": article["version"]},
        headers=headers,
    )
    assert conflict.status_code == 409

    published = publish_article(client, saved_article, headers)
    assert published.status_code == 200
    published_article = published.json()
    assert published_article["status"] == "published"

    public_path = published_article["public_path"]
    api_path = public_path.replace("/notes/", "/api/v1/articles/")
    public = client.get(api_path)
    assert public.status_code == 200
    assert public.json()["content"].startswith("# Published")
    assert len(client.get("/api/v1/articles").json()) == 1

    locked_slug = client.patch(
        f"/api/v1/admin/articles/{article['id']}",
        json={"slug": "renamed-article", "version": published_article["version"]},
        headers=headers,
    )
    assert locked_slug.status_code == 409
    updated = client.patch(
        f"/api/v1/admin/articles/{article['id']}",
        json={"summary": "Updated without moving the URL", "version": published_article["version"]},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["public_path"] == public_path


def test_mutation_requires_session_csrf(client: TestClient) -> None:
    login(client)
    response = client.post(
        "/api/v1/admin/articles",
        json={"title": "No CSRF", "slug": "no-csrf"},
    )
    assert response.status_code == 403
