from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.knowledge_links import iter_wikilinks
from app.models import ContentLink

from .conftest import login
from .test_article_context import publish_article


def test_iter_wikilinks_skips_code_and_supports_alias() -> None:
    content = "\n".join(
        [
            "See [[alpha]] and [[project:gavin|案例]].",
            "",
            "```python",
            "print('[[ignored]]')",
            "```",
            "",
            "Inline `[[also-ignored]]` stays code.",
        ]
    )
    links = iter_wikilinks(content)
    assert [(link.token, link.display) for link in links] == [
        ("alpha", "alpha"),
        ("project:gavin", "案例"),
    ]


def test_publish_wikilink_creates_public_backlink(client: TestClient) -> None:
    headers = {"X-CSRF-Token": login(client)}
    target = publish_article(client, headers, title="Alpha note", slug="alpha-note")
    source = client.post(
        "/api/v1/admin/articles",
        headers=headers,
        json={
            "title": "Beta note",
            "slug": "beta-note",
            "summary": "Links to alpha",
            "content": "See [[alpha-note]] for the earlier write-up.",
        },
    ).json()
    published = client.post(
        f"/api/v1/admin/articles/{source['id']}/publish",
        json={"version": source["version"]},
        headers=headers,
    )
    assert published.status_code == 200, published.text

    context = client.get(f"{target['public_path'].replace('/notes/', '/api/v1/articles/')}/context")
    assert context.status_code == 200, context.text
    backlinks = context.json()["backlinks"]
    assert [item["slug"] if "slug" in item else item["public_path"] for item in backlinks]
    assert backlinks[0]["content_type"] == "article"
    assert backlinks[0]["public_path"] == published.json()["public_path"]
    assert backlinks[0]["title"] == "Beta note"

    public_path = published.json()["public_path"].replace("/notes/", "/api/v1/articles/")
    public_source = client.get(public_path)
    assert public_source.status_code == 200
    wikilinks = public_source.json()["wikilinks"]
    assert wikilinks[0]["token"] == "alpha-note"
    assert wikilinks[0]["public_path"] == target["public_path"]


def test_working_copy_wikilink_does_not_change_public_backlinks(client: TestClient) -> None:
    headers = {"X-CSRF-Token": login(client)}
    target = publish_article(client, headers, title="Gamma", slug="gamma")
    source = publish_article(client, headers, title="Delta", slug="delta")
    updated = client.patch(
        f"/api/v1/admin/articles/{source['id']}",
        headers=headers,
        json={
            "content": "Draft only [[gamma]]",
            "version": source["version"],
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["has_unpublished_changes"] is True
    context = client.get(f"{target['public_path'].replace('/notes/', '/api/v1/articles/')}/context")
    assert context.json()["backlinks"] == []


def test_article_references_snapshot_on_publish_and_internal_backlink(client: TestClient) -> None:
    headers = {"X-CSRF-Token": login(client)}
    target = publish_article(client, headers, title="Epsilon", slug="epsilon")
    draft = client.post(
        "/api/v1/admin/articles",
        headers=headers,
        json={
            "title": "Zeta",
            "slug": "zeta",
            "content": "Body without wikilink",
            "references": [
                {
                    "kind": "internal",
                    "display_title": "Epsilon note",
                    "target_type": "article",
                    "target_id": target["id"],
                },
                {
                    "kind": "external",
                    "display_title": "RFC 9110",
                    "url": "https://www.rfc-editor.org/rfc/rfc9110",
                },
            ],
        },
    )
    assert draft.status_code == 201, draft.text
    published = client.post(
        f"/api/v1/admin/articles/{draft.json()['id']}/publish",
        json={"version": draft.json()["version"]},
        headers=headers,
    )
    assert published.status_code == 200, published.text
    public = client.get(published.json()["public_path"].replace("/notes/", "/api/v1/articles/"))
    urls = [item["url"] for item in public.json()["references"]]
    assert target["public_path"] in urls
    assert "https://www.rfc-editor.org/rfc/rfc9110" in urls
    context = client.get(f"{target['public_path'].replace('/notes/', '/api/v1/articles/')}/context")
    assert context.json()["backlinks"][0]["public_path"] == published.json()["public_path"]


def test_unpublished_and_ambiguous_targets_do_not_resolve(client: TestClient) -> None:
    headers = {"X-CSRF-Token": login(client)}
    draft = client.post(
        "/api/v1/admin/articles",
        headers=headers,
        json={"title": "Hidden", "slug": "shared-slug", "content": "draft"},
    ).json()
    publish_article(client, headers, title="Visible project twin", slug="other-slug")
    project = client.post(
        "/api/v1/admin/projects",
        headers=headers,
        json={
            "title": "Shared",
            "slug": "shared-slug",
            "content": "project body",
        },
    ).json()
    client.post(
        f"/api/v1/admin/projects/{project['id']}/publish",
        headers=headers,
        json={"version": project["version"]},
    )
    source = client.post(
        "/api/v1/admin/articles",
        headers=headers,
        json={
            "title": "Resolver",
            "slug": "resolver",
            "content": "[[shared-slug]] and [[article:shared-slug]]",
        },
    ).json()
    published = client.post(
        f"/api/v1/admin/articles/{source['id']}/publish",
        json={"version": source["version"]},
        headers=headers,
    ).json()
    public = client.get(
        published["public_path"].replace("/notes/", "/api/v1/articles/")
    ).json()
    by_token = {item["token"]: item for item in public["wikilinks"]}
    assert by_token["shared-slug"]["public_path"] == "/projects/shared-slug"
    assert by_token["article:shared-slug"]["public_path"] is None
    assert draft["status"] == "draft"


def test_soft_delete_hides_and_restore_rebuilds_backlinks(client: TestClient) -> None:
    headers = {"X-CSRF-Token": login(client)}
    target = publish_article(client, headers, title="Eta", slug="eta")
    source = client.post(
        "/api/v1/admin/articles",
        headers=headers,
        json={"title": "Theta", "slug": "theta", "content": "See [[eta]]"},
    ).json()
    client.post(
        f"/api/v1/admin/articles/{source['id']}/publish",
        json={"version": source["version"]},
        headers=headers,
    )
    deleted = client.delete(f"/api/v1/admin/articles/{source['id']}", headers=headers)
    assert deleted.status_code == 204
    context = client.get(f"{target['public_path'].replace('/notes/', '/api/v1/articles/')}/context")
    assert context.json()["backlinks"] == []
    restored = client.post(
        f"/api/v1/admin/trash/article/{source['id']}/restore",
        headers=headers,
    )
    assert restored.status_code == 200, restored.text
    context = client.get(f"{target['public_path'].replace('/notes/', '/api/v1/articles/')}/context")
    assert context.json()["backlinks"][0]["title"] == "Theta"
    with client.app.state.database.session_factory() as db:
        links = db.scalars(
            select(ContentLink).where(ContentLink.source_id == source["id"])
        )
        count = len(list(links))
        assert count == 1


def test_unpublished_internal_reference_is_rejected(client: TestClient) -> None:
    headers = {"X-CSRF-Token": login(client)}
    draft = client.post(
        "/api/v1/admin/articles",
        headers=headers,
        json={"title": "Not public", "slug": "not-public", "content": "draft"},
    ).json()
    response = client.post(
        "/api/v1/admin/articles",
        headers=headers,
        json={
            "title": "Bad ref",
            "slug": "bad-ref",
            "content": "body",
            "references": [
                {
                    "kind": "internal",
                    "display_title": "Nope",
                    "target_type": "article",
                    "target_id": draft["id"],
                }
            ],
        },
    )
    assert response.status_code == 422
