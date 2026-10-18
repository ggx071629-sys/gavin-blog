from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from .conftest import login


def content_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "statement": "这里记录工程实践、问题排查与项目复盘，只留下持续校准过的技术笔记。",
        "capabilities": [
            {
                "title": "后端工程",
                "description": "从 API、数据库到服务架构，构建能够真正运行和持续维护的后端系统。",
                "tags": ["Python", "FastAPI", "SQL"],
            }
        ],
        "now": [
            {"label": "重构这个网站", "status": "in_progress", "target": "projects"},
            {"label": "最近正在研究的技术", "status": "exploring", "target": "articles"},
        ],
        "editorial_topics": ["工程实践", "问题排查"],
        "site": {
            "description": "这里记录做过的事情、踩过的坑，以及随着实践不断改变的认识。",
            "stack": [
                {"label": "WRITING", "value": "Markdown"},
                {"label": "FRONTEND", "value": "Nuxt 4 SSR"},
            ],
        },
    }
    payload.update(overrides)
    return payload


def update_payload(version: int, **overrides: Any) -> dict[str, Any]:
    return {"content": content_payload(**overrides), "version": version}


def test_public_returns_defaults_without_writing_row(client: TestClient) -> None:
    response = client.get("/api/v1/about-page")
    assert response.status_code == 200
    body = response.json()
    assert body["statement"]
    assert body["capabilities"]
    assert body["editorial_topics"]
    assert body["site"]["stack"]


def test_admin_get_seeds_initial_published_revision(client: TestClient) -> None:
    assert client.get("/api/v1/admin/about-page").status_code == 401
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    response = client.get("/api/v1/admin/about-page", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "published"
    assert body["version"] == 1
    assert body["current_publish_revision"] == 1
    assert body["has_unpublished_changes"] is False
    assert body["content"]["statement"]


def test_autosave_changes_working_copy_without_public_change(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    current = client.get("/api/v1/admin/about-page", headers=headers).json()
    updated = client.patch(
        "/api/v1/admin/about-page",
        json=update_payload(current["version"], statement="草稿中的新引言"),
        headers=headers,
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["version"] == current["version"] + 1
    assert body["has_unpublished_changes"] is True
    assert body["content"]["statement"] == "草稿中的新引言"

    public = client.get("/api/v1/about-page").json()
    assert public["statement"] == current["content"]["statement"]


def test_publish_creates_revision_and_updates_public(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    seeded = client.get("/api/v1/admin/about-page", headers=headers).json()
    saved = client.patch(
        "/api/v1/admin/about-page",
        json=update_payload(seeded["version"], statement="发布后的新引言"),
        headers=headers,
    ).json()
    assert client.get("/api/v1/about-page").json()["statement"] != "发布后的新引言"

    published = client.post(
        "/api/v1/admin/about-page/publish",
        json={"version": saved["version"]},
        headers=headers,
    )
    assert published.status_code == 200
    body = published.json()
    assert body["current_publish_revision"] == 2
    assert body["has_unpublished_changes"] is False
    assert client.get("/api/v1/about-page").json()["statement"] == "发布后的新引言"


def test_version_conflict_blocks_autosave_and_publish(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    seeded = client.get("/api/v1/admin/about-page", headers=headers).json()
    client.patch(
        "/api/v1/admin/about-page",
        json=update_payload(seeded["version"], statement="first"),
        headers=headers,
    )
    assert client.patch(
        "/api/v1/admin/about-page",
        json=update_payload(seeded["version"], statement="stale"),
        headers=headers,
    ).status_code == 409
    assert client.post(
        "/api/v1/admin/about-page/publish",
        json={"version": seeded["version"]},
        headers=headers,
    ).status_code == 409


def test_rollback_creates_rollback_revision_without_rewriting_history(
    client: TestClient,
) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    seeded = client.get("/api/v1/admin/about-page", headers=headers).json()
    saved = client.patch(
        "/api/v1/admin/about-page",
        json=update_payload(seeded["version"], statement="second statement"),
        headers=headers,
    ).json()
    published = client.post(
        "/api/v1/admin/about-page/publish",
        json={"version": saved["version"]},
        headers=headers,
    ).json()
    first_revision_id = seeded["current_revision_id"]
    revision = client.get(
        f"/api/v1/admin/about-page/revisions/{first_revision_id}",
        headers=headers,
    ).json()
    assert revision["content"]["statement"] == seeded["content"]["statement"]

    # A dirty working copy must refuse rollback.
    client.patch(
        "/api/v1/admin/about-page",
        json=update_payload(published["version"], statement="unsaved draft"),
        headers=headers,
    )
    assert client.post(
        f"/api/v1/admin/about-page/revisions/{first_revision_id}/rollback",
        json={
            "version": published["version"] + 1,
            "current_revision_id": published["current_revision_id"],
            "rollback_confirmed": True,
        },
        headers=headers,
    ).status_code == 409

    # Resolve the draft, then rollback in a clean state.
    clean = client.post(
        "/api/v1/admin/about-page/publish",
        json={"version": published["version"] + 1},
        headers=headers,
    ).json()
    rolled = client.post(
        f"/api/v1/admin/about-page/revisions/{first_revision_id}/rollback",
        json={
            "version": clean["version"],
            "current_revision_id": clean["current_revision_id"],
            "rollback_confirmed": True,
        },
        headers=headers,
    )
    assert rolled.status_code == 200
    body = rolled.json()
    assert body["current_publish_revision"] == 4
    assert body["content"]["statement"] == seeded["content"]["statement"]
    assert client.get("/api/v1/about-page").json()["statement"] == seeded["content"]["statement"]

    revisions = client.get("/api/v1/admin/about-page/revisions", headers=headers).json()
    rollback_revision = revisions["revisions"][0]
    assert rollback_revision["source"] == "rollback"
    assert rollback_revision["rollback_from_revision_id"] == first_revision_id


def test_revision_diff_returns_fields(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    seeded = client.get("/api/v1/admin/about-page", headers=headers).json()
    saved = client.patch(
        "/api/v1/admin/about-page",
        json=update_payload(seeded["version"], statement="changed"),
        headers=headers,
    ).json()
    published = client.post(
        "/api/v1/admin/about-page/publish",
        json={"version": saved["version"]},
        headers=headers,
    ).json()
    diff = client.get(
        "/api/v1/admin/about-page/revision-diff",
        params={
            "from_revision_id": seeded["current_revision_id"],
            "to_revision_id": published["current_revision_id"],
        },
        headers=headers,
    )
    assert diff.status_code == 200
    assert "changed" in diff.json()["statement"]


def test_profile_bio_and_about_statement_are_decoupled(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    seeded = client.get("/api/v1/admin/about-page", headers=headers).json()
    saved = client.patch(
        "/api/v1/admin/about-page",
        json=update_payload(seeded["version"], statement="关于页独立引言"),
        headers=headers,
    ).json()
    client.post(
        "/api/v1/admin/about-page/publish",
        json={"version": saved["version"]},
        headers=headers,
    )
    profile = client.get("/api/v1/admin/profile", headers=headers).json()
    client.patch(
        "/api/v1/admin/profile",
        json={
            "name": profile["name"],
            "title": profile["title"],
            "bio": "首页简介被修改",
            "skills": profile["skills"],
            "avatar_url": profile["avatar_url"],
            "city": profile["city"],
            "city_visible": profile["city_visible"],
            "github_url": profile["github_url"],
            "website_url": profile["website_url"],
            "email": profile["email"],
            "email_visible": profile["email_visible"],
            "resume_url": profile["resume_url"],
            "version": profile["version"],
        },
        headers=headers,
    )
    assert client.get("/api/v1/profile").json()["bio"] == "首页简介被修改"
    assert client.get("/api/v1/about-page").json()["statement"] == "关于页独立引言"


def test_invalid_about_content_rejected(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    seeded = client.get("/api/v1/admin/about-page", headers=headers).json()
    invalid_cases = [
        update_payload(seeded["version"], capabilities=[]),
        update_payload(
            seeded["version"],
            capabilities=[{"title": " ", "description": "ok", "tags": []}],
        ),
        update_payload(
            seeded["version"],
            editorial_topics=[],
        ),
        update_payload(seeded["version"], statement=""),
    ]
    for payload in invalid_cases:
        response = client.patch(
            "/api/v1/admin/about-page",
            json=payload,
            headers=headers,
        )
        assert response.status_code == 422, payload
    assert client.patch(
        "/api/v1/admin/about-page",
        json={**update_payload(seeded["version"]), "unexpected": True},
        headers=headers,
    ).status_code == 422


def test_about_card_limits_preserve_ten_items_and_reject_eleven(client: TestClient) -> None:
    headers = {"X-CSRF-Token": login(client)}
    seeded = client.get("/api/v1/admin/about-page", headers=headers).json()
    content = content_payload(
        capabilities=[
            {"title": f"领域 {i}", "description": f"说明 {i}", "tags": ["Python"]}
            for i in range(10)
        ],
        now=[
            {"label": f"动态 {i}", "status": "building", "target": "projects"}
            for i in range(10)
        ],
    )
    saved = client.patch(
        "/api/v1/admin/about-page",
        json={"content": content, "version": seeded["version"]},
        headers=headers,
    )
    assert saved.status_code == 200
    assert saved.json()["content"] == content
    assert client.get("/api/v1/admin/about-page", headers=headers).json()["content"] == content
    assert client.get("/api/v1/about-page").json() == seeded["content"]

    for field in ("capabilities", "now"):
        invalid = {**content, field: [*content[field], content[field][0]]}
        rejected = client.patch(
            "/api/v1/admin/about-page",
            json={"content": invalid, "version": saved.json()["version"]},
            headers=headers,
        )
        assert rejected.status_code == 422
        assert any(
            error["loc"] == ["body", "content", field]
            for error in rejected.json()["detail"]
        )
        current = client.get("/api/v1/admin/about-page", headers=headers).json()
        assert current["version"] == saved.json()["version"]
        assert current["content"] == content

    published = client.post(
        "/api/v1/admin/about-page/publish",
        json={"version": saved.json()["version"]},
        headers=headers,
    )
    assert published.status_code == 200
    assert client.get("/api/v1/about-page").json() == content
