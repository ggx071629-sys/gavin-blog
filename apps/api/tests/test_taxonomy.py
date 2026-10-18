from __future__ import annotations

from fastapi.testclient import TestClient

from .conftest import login, publish_article


def create_taxonomy(client: TestClient, headers: dict[str, str]) -> tuple[dict, dict]:
    category_response = client.post(
        "/api/v1/admin/categories",
        json={"name": "工程实践", "slug": "engineering", "description": "可复验的工程经验"},
        headers=headers,
    )
    tag_response = client.post(
        "/api/v1/admin/tags",
        json={"name": "FastAPI", "slug": "fastapi", "description": "FastAPI 技术笔记"},
        headers=headers,
    )
    assert category_response.status_code == 201
    assert tag_response.status_code == 201
    return category_response.json(), tag_response.json()


def test_taxonomy_admin_requires_session_and_csrf(client: TestClient) -> None:
    assert client.get("/api/v1/admin/categories").status_code == 401
    login(client)
    without_csrf = client.post(
        "/api/v1/admin/categories",
        json={"name": "工程实践", "slug": "engineering"},
    )
    assert without_csrf.status_code == 403


def test_taxonomy_crud_and_reference_protection(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    category, tag = create_taxonomy(client, headers)

    duplicate = client.post(
        "/api/v1/admin/categories",
        json={"name": "重复", "slug": "engineering"},
        headers=headers,
    )
    assert duplicate.status_code == 409

    updated = client.patch(
        f"/api/v1/admin/tags/{tag['id']}",
        json={"name": "FastAPI / Starlette"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "FastAPI / Starlette"

    article = client.post(
        "/api/v1/admin/articles",
        json={
            "title": "分类文章",
            "slug": "categorized-article",
            "content": "# Taxonomy",
            "category_id": category["id"],
            "tag_ids": [tag["id"]],
        },
        headers=headers,
    )
    assert article.status_code == 201
    assert article.json()["category"]["slug"] == "engineering"
    assert [item["slug"] for item in article.json()["tags"]] == ["fastapi"]

    assert (
        client.delete(f"/api/v1/admin/categories/{category['id']}", headers=headers).status_code
        == 409
    )
    assert client.delete(f"/api/v1/admin/tags/{tag['id']}", headers=headers).status_code == 409

    unused = client.post(
        "/api/v1/admin/tags",
        json={"name": "未使用", "slug": "unused"},
        headers=headers,
    ).json()
    assert client.delete(f"/api/v1/admin/tags/{unused['id']}", headers=headers).status_code == 204


def test_article_taxonomy_validation_autosave_and_public_filters(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    category, tag = create_taxonomy(client, headers)

    invalid = client.post(
        "/api/v1/admin/articles",
        json={"title": "无效关系", "slug": "invalid-relation", "category_id": 9999},
        headers=headers,
    )
    assert invalid.status_code == 422

    created = client.post(
        "/api/v1/admin/articles",
        json={
            "title": "可筛选文章",
            "slug": "filterable-article",
            "content": "# Published",
        },
        headers=headers,
    ).json()
    saved = client.patch(
        f"/api/v1/admin/articles/{created['id']}",
        json={
            "version": created["version"],
            "category_id": category["id"],
            "tag_ids": [tag["id"]],
        },
        headers=headers,
    )
    assert saved.status_code == 200
    saved_article = saved.json()
    assert saved_article["version"] == created["version"] + 1

    draft = client.post(
        "/api/v1/admin/articles",
        json={
            "title": "同分类草稿",
            "slug": "categorized-draft",
            "category_id": category["id"],
            "tag_ids": [tag["id"]],
        },
        headers=headers,
    )
    assert draft.status_code == 201

    published = publish_article(client, saved_article, headers)
    assert published.status_code == 200

    by_category = client.get("/api/v1/articles?category=engineering").json()
    by_tag = client.get("/api/v1/articles?tag=fastapi").json()
    assert [item["slug"] for item in by_category] == ["filterable-article"]
    assert [item["slug"] for item in by_tag] == ["filterable-article"]
    assert client.get("/api/v1/articles?tag=missing").json() == []

    taxonomy = client.get("/api/v1/taxonomy").json()
    assert taxonomy["categories"] == [
        {"id": category["id"], "name": "工程实践", "slug": "engineering", "article_count": 1}
    ]
    assert taxonomy["tags"] == [
        {"id": tag["id"], "name": "FastAPI", "slug": "fastapi", "article_count": 1}
    ]
    assert taxonomy["total_article_count"] == 1

    uncategorized = client.post(
        "/api/v1/admin/articles",
        json={"title": "未分类公开", "slug": "uncategorized-public", "content": "# Free"},
        headers=headers,
    ).json()
    assert publish_article(client, uncategorized, headers).status_code == 200
    taxonomy = client.get("/api/v1/taxonomy").json()
    assert taxonomy["total_article_count"] == 2
    assert sum(item["article_count"] for item in taxonomy["categories"]) == 1


def test_unpublished_taxonomy_change_does_not_move_public_filters(
    client: TestClient,
) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    first = client.post(
        "/api/v1/admin/categories",
        json={"name": "First Column", "slug": "first-cat"},
        headers=headers,
    ).json()
    second = client.post(
        "/api/v1/admin/categories",
        json={"name": "Second Column", "slug": "second-cat"},
        headers=headers,
    ).json()
    tag_a = client.post(
        "/api/v1/admin/tags",
        json={"name": "标签甲", "slug": "tag-a"},
        headers=headers,
    ).json()
    tag_b = client.post(
        "/api/v1/admin/tags",
        json={"name": "标签乙", "slug": "tag-b"},
        headers=headers,
    ).json()
    created = client.post(
        "/api/v1/admin/articles",
        json={
            "title": "修订栏目文章",
            "slug": "revision-taxonomy",
            "content": "# 发布正文",
            "category_id": first["id"],
            "tag_ids": [tag_a["id"]],
        },
        headers=headers,
    ).json()
    published = client.post(
        f"/api/v1/admin/articles/{created['id']}/publish",
        json={"version": created["version"]},
        headers=headers,
    ).json()
    public_path = published["public_path"].replace("/notes/", "/api/v1/articles/")

    def slugs(path: str) -> list[str]:
        return [item["slug"] for item in client.get(path).json()]

    assert client.get(public_path).json()["category"]["slug"] == "first-cat"
    assert [tag["slug"] for tag in client.get(public_path).json()["tags"]] == ["tag-a"]
    assert slugs("/api/v1/articles?category=first-cat") == ["revision-taxonomy"]
    assert slugs("/api/v1/articles?category=second-cat") == []
    assert slugs("/api/v1/articles?tag=tag-a") == ["revision-taxonomy"]
    assert slugs("/api/v1/articles?tag=tag-b") == []
    taxonomy = client.get("/api/v1/taxonomy").json()
    assert {item["slug"]: item["article_count"] for item in taxonomy["categories"]} == {
        "first-cat": 1,
    }
    assert {item["slug"]: item["article_count"] for item in taxonomy["tags"]} == {
        "tag-a": 1,
    }
    assert client.get("/api/v1/search", params={"q": "First"}).json()[0]["public_path"].endswith(
        "/revision-taxonomy"
    )
    assert client.get("/api/v1/search", params={"q": "Second"}).json() == []

    moved = client.patch(
        f"/api/v1/admin/articles/{created['id']}",
        json={
            "version": published["version"],
            "category_id": second["id"],
            "tag_ids": [tag_b["id"]],
        },
        headers=headers,
    ).json()
    assert moved["has_unpublished_changes"] is True
    assert moved["category"]["slug"] == "second-cat"

    public = client.get(public_path).json()
    assert public["category"]["slug"] == "first-cat"
    assert [tag["slug"] for tag in public["tags"]] == ["tag-a"]
    assert slugs("/api/v1/articles?category=first-cat") == ["revision-taxonomy"]
    assert slugs("/api/v1/articles?category=second-cat") == []
    assert slugs("/api/v1/articles?tag=tag-a") == ["revision-taxonomy"]
    assert slugs("/api/v1/articles?tag=tag-b") == []
    taxonomy = client.get("/api/v1/taxonomy").json()
    assert {item["slug"]: item["article_count"] for item in taxonomy["categories"]} == {
        "first-cat": 1,
    }
    assert {item["slug"]: item["article_count"] for item in taxonomy["tags"]} == {
        "tag-a": 1,
    }
    assert client.get("/api/v1/search", params={"q": "First"}).json()[0]["public_path"].endswith(
        "/revision-taxonomy"
    )
    assert client.get("/api/v1/search", params={"q": "Second"}).json() == []

    client.post(
        f"/api/v1/admin/articles/{created['id']}/publish",
        json={"version": moved["version"]},
        headers=headers,
    )
    public = client.get(public_path).json()
    assert public["category"]["slug"] == "second-cat"
    assert [tag["slug"] for tag in public["tags"]] == ["tag-b"]
    assert slugs("/api/v1/articles?category=first-cat") == []
    assert slugs("/api/v1/articles?category=second-cat") == ["revision-taxonomy"]
    assert slugs("/api/v1/articles?tag=tag-a") == []
    assert slugs("/api/v1/articles?tag=tag-b") == ["revision-taxonomy"]
    taxonomy = client.get("/api/v1/taxonomy").json()
    assert {item["slug"]: item["article_count"] for item in taxonomy["categories"]} == {
        "second-cat": 1,
    }
    assert {item["slug"]: item["article_count"] for item in taxonomy["tags"]} == {
        "tag-b": 1,
    }
    assert client.get("/api/v1/search", params={"q": "Second"}).json()[0]["public_path"].endswith(
        "/revision-taxonomy"
    )
