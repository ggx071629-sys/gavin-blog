from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models import (
    ArticleRevision,
)

from .conftest import login, publish_article


def create_draft(client: TestClient, headers: dict[str, str], **overrides) -> dict:
    payload = {
        "title": "Revision basics",
        "slug": "revision-basics",
        "summary": "Summary",
        "content": "# One",
        **overrides,
    }
    response = client.post("/api/v1/admin/articles", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_every_publish_creates_immutable_monotonic_revision(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    article = create_draft(client, headers)
    first = publish_article(client, article, headers).json()
    assert first["current_publish_revision"] == 1
    assert first["has_unpublished_changes"] is False
    public_path = first["public_path"].replace("/notes/", "/api/v1/articles/")
    first_public = client.get(public_path).json()
    assert first_public["updated_at"] == first_public["published_at"]

    updated = client.patch(
        f"/api/v1/admin/articles/{article['id']}",
        json={"content": "# Two", "version": first["version"]},
        headers=headers,
    ).json()
    assert updated["has_unpublished_changes"] is True
    assert updated["current_publish_revision"] == 1

    second = publish_article(client, updated, headers).json()
    assert second["current_publish_revision"] == 2
    assert second["has_unpublished_changes"] is False
    second_public = client.get(public_path).json()
    assert second_public["updated_at"] > second_public["published_at"]

    with client.app.state.database.session_factory() as db:
        revisions = list(
            db.scalars(
                select(ArticleRevision)
                .where(ArticleRevision.article_id == article["id"])
                .order_by(ArticleRevision.revision_number)
            ).all()
        )
        assert [revision.revision_number for revision in revisions] == [1, 2]
        assert revisions[0].content == "# One"
        assert revisions[1].content == "# Two"
        assert revisions[0].source == "editor"
        assert revisions[1].published_at >= revisions[0].published_at
        assert revisions[0].content_sha256 != revisions[1].content_sha256
        assert all(revision.title == "Revision basics" for revision in revisions)


def test_autosave_never_creates_revision_or_changes_public_content(
    client: TestClient,
) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    article = create_draft(client, headers, content="# Public")
    published = publish_article(client, article, headers).json()
    path = published["public_path"].replace("/notes/", "/api/v1/articles/")
    before = client.get(path).json()

    saved = client.patch(
        f"/api/v1/admin/articles/{article['id']}",
        json={"content": "# Working copy secret", "version": published["version"]},
        headers=headers,
    ).json()
    assert saved["version"] == published["version"] + 1
    after = client.get(path).json()
    assert after["content"] == before["content"] == "# Public"
    with client.app.state.database.session_factory() as db:
        count = db.scalar(
            select(func.count(ArticleRevision.id)).where(
                ArticleRevision.article_id == article["id"]
            )
        )
        assert count == 1


def test_revision_keeps_taxonomy_snapshot(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    category = client.post(
        "/api/v1/admin/categories",
        json={"name": "Arch", "slug": "arch"},
        headers=headers,
    ).json()
    tags = [
        client.post(
            "/api/v1/admin/tags",
            json={"name": name, "slug": slug},
            headers=headers,
        ).json()
        for name, slug in (("Beta", "beta"), ("Alpha", "alpha"))
    ]
    article = create_draft(
        client,
        headers,
        category_id=category["id"],
        tag_ids=[tag["id"] for tag in tags],
    )
    published = publish_article(client, article, headers).json()
    with client.app.state.database.session_factory() as db:
        revision = db.scalar(
            select(ArticleRevision).where(ArticleRevision.article_id == article["id"])
        )
        assert revision is not None
        assert revision.category_id == category["id"]
        assert revision.category_name == "Arch"
        snapshot_tags = list(revision.tags)
        assert [(tag.name, tag.slug) for tag in snapshot_tags] == [
            ("Alpha", "alpha"),
            ("Beta", "beta"),
        ]
        assert [tag.position for tag in snapshot_tags] == [0, 1]
    public = client.get(published["public_path"].replace("/notes/", "/api/v1/articles/"))
    assert public.status_code == 200
    assert [tag["name"] for tag in public.json()["tags"]] == ["Alpha", "Beta"]


def test_trash_removes_public_and_restore_republishes_snapshot(
    client: TestClient,
) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    article = create_draft(client, headers, content="# Visible")
    published = publish_article(client, article, headers).json()
    public_path = published["public_path"].replace("/notes/", "/api/v1/articles/")
    assert client.get(public_path).status_code == 200

    deleted = client.delete(f"/api/v1/admin/articles/{article['id']}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(public_path).status_code == 404
    restored = client.post(
        "/api/v1/admin/trash/article/" + str(article["id"]) + "/restore",
        headers=headers,
    )
    assert restored.status_code == 200
    assert client.get(public_path).status_code == 200


def test_publish_rejects_stale_version_and_published_slug_change(
    client: TestClient,
) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    article = create_draft(client, headers)
    published = publish_article(client, article, headers).json()
    stale = client.post(
        f"/api/v1/admin/articles/{article['id']}/publish",
        json={"version": published["version"] - 1},
        headers=headers,
    )
    assert stale.status_code == 409
    assert stale.json()["detail"] == "article was updated elsewhere"

    locked = client.patch(
        f"/api/v1/admin/articles/{article['id']}",
        json={"slug": published["slug"] + "-moved", "version": published["version"]},
        headers=headers,
    )
    assert locked.status_code == 409
    assert locked.json()["detail"] == "published article slug cannot be changed"


def test_revision_list_diff_and_rollback_remain_core_article_features(
    client: TestClient,
) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    article = create_draft(client, headers, content="# First\n\nOriginal body")
    first_publish = publish_article(client, article, headers).json()
    updated = client.patch(
        f"/api/v1/admin/articles/{article['id']}",
        json={"content": "# Second\n\nChanged body", "version": first_publish["version"]},
        headers=headers,
    ).json()
    second_publish = publish_article(client, updated, headers).json()

    history = client.get(f"/api/v1/admin/articles/{article['id']}/revisions")
    assert history.status_code == 200
    revisions = history.json()["revisions"]
    assert [item["revision_number"] for item in revisions] == [2, 1]
    first_revision = revisions[1]
    second_revision = revisions[0]

    diff = client.get(
        f"/api/v1/admin/articles/{article['id']}/revision-diff",
        params={
            "from_revision_id": first_revision["id"],
            "to_revision_id": second_revision["id"],
        },
    )
    assert diff.status_code == 200
    original_diff = diff.json()["content"]
    assert "Original body" in original_diff
    assert "Changed body" in original_diff

    rollback = client.post(
        f"/api/v1/admin/articles/{article['id']}/revisions/{first_revision['id']}/rollback",
        json={
            "version": second_publish["version"],
            "current_revision_id": second_publish["current_revision_id"],
            "rollback_confirmed": True,
        },
        headers=headers,
    )
    assert rollback.status_code == 200, rollback.text
    rolled_back = rollback.json()
    assert rolled_back["revision_number"] == 3
    assert rolled_back["source"] == "rollback"
    assert rolled_back["rollback_from_revision_id"] == first_revision["id"]
    assert rolled_back["content"] == "# First\n\nOriginal body"

    history_after = client.get(
        f"/api/v1/admin/articles/{article['id']}/revisions"
    ).json()["revisions"]
    assert [item["revision_number"] for item in history_after] == [3, 2, 1]
    immutable = {item["revision_number"]: item for item in history_after}
    assert immutable[1] == first_revision
    assert immutable[2] == second_revision
    diff_after = client.get(
        f"/api/v1/admin/articles/{article['id']}/revision-diff",
        params={
            "from_revision_id": first_revision["id"],
            "to_revision_id": second_revision["id"],
        },
    )
    assert diff_after.status_code == 200
    assert diff_after.json()["content"] == original_diff

    public_path = second_publish["public_path"].replace("/notes/", "/api/v1/articles/")
    assert client.get(public_path).json()["content"] == "# First\n\nOriginal body"


def test_dirty_working_copy_blocks_revision_rollback(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    article = create_draft(client, headers, content="# First")
    first_publish = publish_article(client, article, headers).json()
    updated = client.patch(
        f"/api/v1/admin/articles/{article['id']}",
        json={"content": "# Second", "version": first_publish["version"]},
        headers=headers,
    ).json()
    second_publish = publish_article(client, updated, headers).json()
    dirty = client.patch(
        f"/api/v1/admin/articles/{article['id']}",
        json={"content": "# Unsaved public replacement", "version": second_publish["version"]},
        headers=headers,
    ).json()

    history = client.get(f"/api/v1/admin/articles/{article['id']}/revisions").json()
    first_revision = history["revisions"][-1]
    blocked = client.post(
        f"/api/v1/admin/articles/{article['id']}/revisions/{first_revision['id']}/rollback",
        json={
            "version": dirty["version"],
            "current_revision_id": dirty["current_revision_id"],
            "rollback_confirmed": True,
        },
        headers=headers,
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "ARTICLE_WORKING_COPY_DIRTY"


def test_retired_incubator_routes_are_not_registered(client: TestClient) -> None:
    csrf = login(client)
    response = client.get(
        "/api/v1/admin/incubator/overview",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 404
