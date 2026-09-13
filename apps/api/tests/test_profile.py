from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from .conftest import login


def profile_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "Gavin",
        "title": "后端工程师 / AI 应用开发者",
        "bio": "把复杂问题写成未来仍然有用的答案。",
        "skills": ["FastAPI", "Nuxt", "SQLite"],
        "avatar_url": None,
        "city": None,
        "city_visible": False,
        "github_url": "https://github.com/gavin",
        "website_url": "https://gavin.example.com",
        "email": "gavin@example.com",
        "email_visible": False,
        "resume_url": "https://example.com/gavin-resume.pdf",
        "version": 1,
    }
    payload.update(overrides)
    return payload


def test_public_profile_returns_defaults_when_unconfigured(client: TestClient) -> None:
    response = client.get("/api/v1/profile")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Gavin"
    assert body["title"]
    assert body["bio"]
    assert body["skills"] == []
    for hidden in ("avatar_url", "github_url", "website_url", "resume_url", "city", "email"):
        assert hidden not in body


def test_admin_profile_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/admin/profile").status_code == 401
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    assert client.patch(
        "/api/v1/admin/profile",
        json=profile_payload(),
        headers={"X-CSRF-Token": csrf},
    ).status_code == 401


def test_admin_profile_update_requires_csrf(client: TestClient) -> None:
    login(client)
    response = client.patch("/api/v1/admin/profile", json=profile_payload())
    assert response.status_code == 403


def test_admin_profile_get_seeds_default_row(client: TestClient) -> None:
    csrf = login(client)
    response = client.get("/api/v1/admin/profile", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Gavin"
    assert body["version"] == 1
    assert body["city_visible"] is False
    assert body["email_visible"] is False


def test_update_and_public_reflects_changes(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    updated = client.patch(
        "/api/v1/admin/profile",
        json=profile_payload(
            skills=["Python", "TypeScript", "Postgres", "Docker"],
            github_url="https://github.com/gavinhub",
            website_url="https://gavinhub.example.com",
            resume_url="https://example.com/cv.pdf",
        ),
        headers=headers,
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["version"] == 2
    assert body["skills"] == ["Python", "TypeScript", "Postgres", "Docker"]
    assert body["github_url"] == "https://github.com/gavinhub"
    assert body["website_url"] == "https://gavinhub.example.com/"

    public = client.get("/api/v1/profile").json()
    assert public["name"] == "Gavin"
    assert public["skills"] == ["Python", "TypeScript", "Postgres", "Docker"]
    assert public["github_url"] == "https://github.com/gavinhub"
    assert public["website_url"] == "https://gavinhub.example.com/"
    assert public["resume_url"] == "https://example.com/cv.pdf"
    assert "city" not in public
    assert "email" not in public


def test_profile_accepts_managed_and_external_avatar_urls(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    managed = client.patch(
        "/api/v1/admin/profile",
        json=profile_payload(avatar_url="/api/v1/media/42/webp"),
        headers=headers,
    )
    assert managed.status_code == 200
    assert managed.json()["avatar_url"] == "/api/v1/media/42/webp"
    assert client.get("/api/v1/profile").json()["avatar_url"] == "/api/v1/media/42/webp"

    external = client.patch(
        "/api/v1/admin/profile",
        json=profile_payload(
            avatar_url="https://cdn.example.com/avatar.webp",
            version=managed.json()["version"],
        ),
        headers=headers,
    )
    assert external.status_code == 200
    assert external.json()["avatar_url"] == "https://cdn.example.com/avatar.webp"


def test_public_strips_hidden_city_and_email(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    client.patch(
        "/api/v1/admin/profile",
        json=profile_payload(
            city="Hangzhou",
            city_visible=False,
            email="gavin@example.com",
            email_visible=False,
        ),
        headers=headers,
    )
    public = client.get("/api/v1/profile").json()
    assert "city" not in public
    assert "email" not in public

    admin = client.get("/api/v1/admin/profile", headers=headers).json()
    assert admin["city"] == "Hangzhou"
    assert admin["email"] == "gavin@example.com"


def test_public_includes_visible_city_and_email(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    client.patch(
        "/api/v1/admin/profile",
        json=profile_payload(
            city="Hangzhou",
            city_visible=True,
            email="gavin@example.com",
            email_visible=True,
        ),
        headers=headers,
    )
    public = client.get("/api/v1/profile").json()
    assert public["city"] == "Hangzhou"
    assert public["email"] == "gavin@example.com"


def test_clearing_optional_fields(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    seeded = client.patch(
        "/api/v1/admin/profile",
        json=profile_payload(city="Hangzhou", city_visible=True),
        headers=headers,
    ).json()
    cleared = client.patch(
        "/api/v1/admin/profile",
        json=profile_payload(city=None, city_visible=False, version=seeded["version"]),
        headers=headers,
    ).json()
    assert cleared["city"] is None
    public = client.get("/api/v1/profile").json()
    assert "city" not in public


def test_invalid_email_rejected(client: TestClient) -> None:
    csrf = login(client)
    response = client.patch(
        "/api/v1/admin/profile",
        json=profile_payload(email="not-an-email"),
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 422


def test_invalid_urls_rejected(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    assert client.patch(
        "/api/v1/admin/profile",
        json=profile_payload(github_url="not-a-url"),
        headers=headers,
    ).status_code == 422
    assert client.patch(
        "/api/v1/admin/profile",
        json=profile_payload(resume_url="ftp://example.com/x"),
        headers=headers,
    ).status_code == 422
    assert client.patch(
        "/api/v1/admin/profile",
        json=profile_payload(website_url="javascript:alert(1)"),
        headers=headers,
    ).status_code == 422
    for avatar_url in (
        "/api/v1/media/0/webp",
        "/api/v1/media/2/original",
        "/api/v1/media/2/webp?download=1",
        "/api/v1/media/2/webp#fragment",
        "/api/v1/media/../2/webp",
        "//evil.example/avatar.webp",
        "javascript:alert(1)",
    ):
        assert client.patch(
            "/api/v1/admin/profile",
            json=profile_payload(avatar_url=avatar_url),
            headers=headers,
        ).status_code == 422


def test_skills_count_and_length_validation(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    empty = client.patch(
        "/api/v1/admin/profile",
        json=profile_payload(skills=[], bio="只修改简介，保留零技能初态。"),
        headers=headers,
    )
    assert empty.status_code == 200
    assert empty.json()["skills"] == []
    assert client.patch(
        "/api/v1/admin/profile",
        json=profile_payload(skills=["a", "b", "c", "d", "e", "f", "g"]),
        headers=headers,
    ).status_code == 422
    assert client.patch(
        "/api/v1/admin/profile",
        json=profile_payload(skills=["x" * 31]),
        headers=headers,
    ).status_code == 422


def test_version_conflict_returns_409(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    first = client.patch(
        "/api/v1/admin/profile",
        json=profile_payload(),
        headers=headers,
    ).json()
    stale = client.patch(
        "/api/v1/admin/profile",
        json=profile_payload(bio="stale write", version=first["version"] - 1),
        headers=headers,
    )
    assert stale.status_code == 409


def test_update_does_not_affect_articles(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    created = client.post(
        "/api/v1/admin/articles",
        json={"title": "Unaffected", "slug": "unaffected", "content": "# Body"},
        headers=headers,
    ).json()
    client.patch(
        "/api/v1/admin/profile",
        json=profile_payload(name="Renamed Gavin"),
        headers=headers,
    )
    article = client.get(f"/api/v1/admin/articles/{created['id']}", headers=headers).json()
    assert article["title"] == "Unaffected"
    public_profile = client.get("/api/v1/profile").json()
    assert public_profile["name"] == "Renamed Gavin"
