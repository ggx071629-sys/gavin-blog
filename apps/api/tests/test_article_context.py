from __future__ import annotations

from fastapi.testclient import TestClient

from .conftest import login


def publish_article(
    client: TestClient,
    headers: dict[str, str],
    *,
    title: str,
    slug: str,
    category_id: int | None = None,
    tag_ids: list[int] | None = None,
) -> dict:
    response = client.post(
        "/api/v1/admin/articles",
        headers=headers,
        json={
            "title": title,
            "slug": slug,
            "summary": f"Summary for {title}",
            "content": f"# {title}\n\nPublished body",
            "category_id": category_id,
            "tag_ids": tag_ids or [],
        },
    )
    assert response.status_code == 201, response.text
    article = response.json()
    published = client.post(
        f"/api/v1/admin/articles/{article['id']}/publish",
        json={"version": article["version"]},
        headers=headers,
    )
    assert published.status_code == 200, published.text
    return published.json()


def test_public_article_context_returns_stable_neighbors_and_related_snapshots(
    client: TestClient,
) -> None:
    headers = {"X-CSRF-Token": login(client)}
    primary_category = client.post(
        "/api/v1/admin/categories",
        headers=headers,
        json={"name": "Engineering", "slug": "engineering"},
    ).json()
    secondary_category = client.post(
        "/api/v1/admin/categories",
        headers=headers,
        json={"name": "Notes", "slug": "notes"},
    ).json()
    shared_tag = client.post(
        "/api/v1/admin/tags",
        headers=headers,
        json={"name": "FastAPI", "slug": "fastapi"},
    ).json()

    older = publish_article(client, headers, title="Older", slug="older")
    current = publish_article(
        client,
        headers,
        title="Current",
        slug="current",
        category_id=primary_category["id"],
        tag_ids=[shared_tag["id"]],
    )
    same_category_and_tag = publish_article(
        client,
        headers,
        title="Same category and tag",
        slug="same-category-tag",
        category_id=primary_category["id"],
        tag_ids=[shared_tag["id"]],
    )
    same_category = publish_article(
        client,
        headers,
        title="Same category",
        slug="same-category",
        category_id=primary_category["id"],
    )
    shared_tag_only = publish_article(
        client,
        headers,
        title="Shared tag only",
        slug="shared-tag-only",
        category_id=secondary_category["id"],
        tag_ids=[shared_tag["id"]],
    )
    publish_article(client, headers, title="Unrelated", slug="unrelated")
    draft = client.post(
        "/api/v1/admin/articles",
        headers=headers,
        json={"title": "Draft secret", "slug": "draft-secret", "content": "private"},
    )
    assert draft.status_code == 201

    year, month, _slug = current["public_path"].strip("/").split("/")[1:]
    response = client.get(f"/api/v1/articles/{year}/{month}/current/context")

    assert response.status_code == 200, response.text
    context = response.json()
    assert context["previous"]["id"] == older["id"]
    assert context["next"]["id"] == same_category_and_tag["id"]
    assert [item["id"] for item in context["related"]] == [
        same_category_and_tag["id"],
        same_category["id"],
        shared_tag_only["id"],
    ]
    assert all(item["title"] != "Draft secret" for item in context["related"])


def test_public_article_context_rejects_missing_or_wrong_date(client: TestClient) -> None:
    headers = {"X-CSRF-Token": login(client)}
    article = publish_article(client, headers, title="Dated", slug="dated")
    year, month, _slug = article["public_path"].strip("/").split("/")[1:]

    assert client.get(f"/api/v1/articles/{year}/{month}/missing/context").status_code == 404
    assert client.get(f"/api/v1/articles/{int(year) + 1}/{month}/dated/context").status_code == 404
