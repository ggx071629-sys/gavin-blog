from __future__ import annotations

from fastapi.testclient import TestClient

from .conftest import login


def create_and_publish(
    client: TestClient,
    headers: dict[str, str],
    kind: str,
    payload: dict,
) -> dict:
    created = client.post(f"/api/v1/admin/{kind}", json=payload, headers=headers)
    assert created.status_code == 201, created.text
    item = created.json()
    published = client.post(
        f"/api/v1/admin/{kind}/{item['id']}/publish",
        json={"version": item["version"]},
        headers=headers,
    )
    assert published.status_code == 200, published.text
    return published.json()


def test_search_covers_published_content_taxonomy_and_syncs_changes(
    client: TestClient,
) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    category = client.post(
        "/api/v1/admin/categories",
        json={"name": "Observability", "slug": "observability"},
        headers=headers,
    ).json()
    tag = client.post(
        "/api/v1/admin/tags",
        json={"name": "FastAPI", "slug": "fastapi"},
        headers=headers,
    ).json()
    article = create_and_publish(
        client,
        headers,
        "articles",
        {
            "title": "Traceable systems",
            "slug": "traceable-systems",
            "summary": "Production diagnostics",
            "content": "# Instrument every boundary",
            "category_id": category["id"],
            "tag_ids": [tag["id"]],
        },
    )
    create_and_publish(
        client,
        headers,
        "projects",
        {
            "title": "Search project",
            "slug": "search-project",
            "content": "# SQLite ranking",
        },
    )
    create_and_publish(
        client,
        headers,
        "books",
        {
            "book_title": "Reliable APIs",
            "author": "Ada Searcher",
            "slug": "reliable-apis",
            "content": "# Retry budgets",
        },
    )
    draft = client.post(
        "/api/v1/admin/articles",
        json={"title": "Secret draft", "slug": "secret-draft", "content": "leakproof"},
        headers=headers,
    )
    assert draft.status_code == 201

    taxonomy_result = client.get("/api/v1/search", params={"q": "FastAPI"})
    assert taxonomy_result.status_code == 200
    assert [item["content_type"] for item in taxonomy_result.json()] == ["article"]
    assert {
        item["content_type"] for item in client.get("/api/v1/search", params={"q": "Search"}).json()
    } == {"project", "book"}
    assert client.get("/api/v1/search", params={"q": "leakproof"}).json() == []

    updated = client.patch(
        f"/api/v1/admin/articles/{article['id']}",
        json={
            "content": "# Instrument every boundary\n\nCardinality guardrails",
            "version": article["version"],
        },
        headers=headers,
    )
    assert updated.status_code == 200
    # Working-copy autosaves must not leak into the public search index.
    assert client.get("/api/v1/search", params={"q": "Cardinality"}).json() == []
    assert len(client.get("/api/v1/search", params={"q": "Instrument"}).json()) == 1
    republished = client.post(
        f"/api/v1/admin/articles/{article['id']}/publish",
        json={"version": updated.json()["version"]},
        headers=headers,
    )
    assert republished.status_code == 200
    assert len(client.get("/api/v1/search", params={"q": "Cardinality"}).json()) == 1

    deleted = client.delete(f"/api/v1/admin/articles/{article['id']}", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/api/v1/search", params={"q": "Cardinality"}).json() == []


def test_search_validates_query(client: TestClient) -> None:
    assert client.get("/api/v1/search", params={"q": ""}).status_code == 422
    assert client.get("/api/v1/search", params={"q": "x" * 121}).status_code == 422


def test_search_returns_clean_plain_text_snippets(client: TestClient) -> None:
    headers = {"X-CSRF-Token": login(client)}
    create_and_publish(
        client,
        headers,
        "articles",
        {
            "title": "Markdown search",
            "slug": "markdown-search",
            "summary": "**Readable** [`summary`](https://example.com/summary)",
            "content": "# Install Codex\n\nUse `codex` with [Responses API](https://example.com).\n\n```bash\ncodex\n```",
        },
    )

    result = client.get("/api/v1/search", params={"q": "Codex"}).json()[0]

    assert result["summary"] == "Readable summary"
    assert result["snippet"] == "Install Codex Use codex with Responses API."
    for marker in ("#", "`", "https://", "```", "<"):
        assert marker not in result["snippet"]
