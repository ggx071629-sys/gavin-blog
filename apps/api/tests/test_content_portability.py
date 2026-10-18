from __future__ import annotations

import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.routes import admin_content

from .conftest import login


def create_content(client: TestClient, headers: dict[str, str], kind: str, payload: dict) -> dict:
    response = client.post(f"/api/v1/admin/{kind}", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def markdown_bytes(metadata: dict, content: str = "# Imported") -> bytes:
    return f"---\n{json.dumps(metadata)}\n---\n\n{content}\n".encode()


def test_trash_restore_and_permanent_delete_for_all_content_types(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    article = create_content(
        client,
        headers,
        "articles",
        {"title": "Trash article", "slug": "trash-article", "content": "# A"},
    )
    project = create_content(
        client,
        headers,
        "projects",
        {"title": "Trash project", "slug": "trash-project", "content": "# P"},
    )
    book = create_content(
        client,
        headers,
        "books",
        {"book_title": "Trash book", "author": "Author", "slug": "trash-book", "content": "# B"},
    )
    for kind, item in (("articles", article), ("projects", project), ("books", book)):
        published = client.post(
            f"/api/v1/admin/{kind}/{item['id']}/publish",
            json={"version": item["version"]},
            headers=headers,
        )
        assert published.status_code == 200
        assert (
            client.delete(f"/api/v1/admin/{kind}/{item['id']}", headers=headers).status_code == 204
        )
        assert client.get(f"/api/v1/admin/{kind}/{item['id']}").status_code == 404

    trash = client.get("/api/v1/admin/trash")
    assert trash.status_code == 200
    assert {item["content_type"] for item in trash.json()} == {"article", "project", "book"}
    restored = client.post(
        f"/api/v1/admin/trash/article/{article['id']}/restore",
        headers=headers,
    )
    assert restored.status_code == 200
    assert client.get(f"/api/v1/admin/articles/{article['id']}").status_code == 200
    assert len(client.get("/api/v1/search", params={"q": "Trash article"}).json()) == 1

    assert (
        client.delete(f"/api/v1/admin/trash/project/{project['id']}", headers=headers).status_code
        == 204
    )
    assert {item["content_type"] for item in client.get("/api/v1/admin/trash").json()} == {"book"}


def test_permanent_delete_published_article_removes_revisions(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    created = create_content(
        client,
        headers,
        "articles",
        {"title": "Purge published", "slug": "purge-published", "content": "# Keep"},
    )
    published = client.post(
        f"/api/v1/admin/articles/{created['id']}/publish",
        json={"version": created["version"]},
        headers=headers,
    ).json()
    public_path = published["public_path"].replace("/notes/", "/api/v1/articles/")
    assert client.get(public_path).status_code == 200
    trashed = client.delete(
        f"/api/v1/admin/articles/{created['id']}",
        headers=headers,
    )
    assert trashed.status_code == 204
    purged = client.delete(
        f"/api/v1/admin/trash/article/{created['id']}",
        headers=headers,
    )
    assert purged.status_code == 204, purged.text
    assert client.get(public_path).status_code == 404
    with client.app.state.database.session_factory() as db:
        from sqlalchemy import func, select

        from app.models import Article, ArticleRevision

        assert db.scalar(select(Article).where(Article.id == created["id"])) is None
        assert (
            db.scalar(
                select(func.count(ArticleRevision.id)).where(
                    ArticleRevision.article_id == created["id"]
                )
            )
            == 0
        )


def test_markdown_export_and_safe_draft_import(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    create_content(
        client,
        headers,
        "articles",
        {
            "title": "Portable article",
            "slug": "portable-article",
            "summary": "Backup",
            "content": "# Portable\n\nBody",
        },
    )
    exported = client.get("/api/v1/admin/exports/markdown")
    assert exported.status_code == 200
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        document = archive.read("articles/portable-article.md").decode()
    assert document.startswith("---\n")
    assert "# Portable" in document


def test_markdown_export_uses_publish_revision_not_working_copy(
    client: TestClient,
) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    created = create_content(
        client,
        headers,
        "articles",
        {
            "title": "Exported snapshot",
            "slug": "exported-snapshot",
            "summary": "Public summary",
            "content": "# Published body",
        },
    )
    published = client.post(
        f"/api/v1/admin/articles/{created['id']}/publish",
        json={"version": created["version"]},
        headers=headers,
    ).json()
    patched = client.patch(
        f"/api/v1/admin/articles/{created['id']}",
        json={
            "title": "Working title",
            "summary": "Working summary",
            "content": "# Secret working copy",
            "version": published["version"],
        },
        headers=headers,
    )
    assert patched.status_code == 200
    exported = client.get("/api/v1/admin/exports/markdown")
    assert exported.status_code == 200
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        document = archive.read("articles/exported-snapshot.md").decode()
    assert "Published body" in document
    assert "Secret working copy" not in document
    assert "Exported snapshot" in document
    assert "Working title" not in document

    metadata = {
        "type": "book",
        "book_title": "Imported book",
        "author": "Importer",
        "slug": "imported-book",
        "reading_status": "reading",
        "rating": 4,
        "summary": "From Markdown",
        "status": "published",
    }
    markdown = f"---\n{json.dumps(metadata)}\n---\n\n# Imported safely\n".encode()
    imported = client.post(
        "/api/v1/admin/imports/markdown",
        files=[("files", ("imported-book.md", markdown, "text/markdown"))],
        headers=headers,
    )
    assert imported.status_code == 200, imported.text
    result = imported.json()["imported"][0]
    created = client.get(f"/api/v1/admin/books/{result['content_id']}").json()
    assert created["status"] == "draft"
    assert created["content"].startswith("# Imported safely")
    assert client.get("/api/v1/books").json() == []
    duplicate = client.post(
        "/api/v1/admin/imports/markdown",
        files=[("files", ("imported-book.md", markdown, "text/markdown"))],
        headers=headers,
    )
    assert duplicate.status_code == 409


@pytest.mark.parametrize(
    "metadata",
    [
        {"type": "article", "title": "Bad slug", "slug": ["not", "a", "string"]},
        {
            "type": "article",
            "title": "Bad list",
            "slug": "bad-list",
            "tag_slugs": "fastapi",
        },
        {
            "type": "article",
            "title": "Unknown field",
            "slug": "unknown-field",
            "unexpected": True,
        },
        {
            "type": "article",
            "title": "Numeric timestamp",
            "slug": "numeric-timestamp",
            "published_at": 1_788_000_000,
        },
    ],
)
def test_import_rejects_metadata_type_confusion_and_unknown_fields(
    client: TestClient,
    metadata: dict,
) -> None:
    csrf = login(client)
    response = client.post(
        "/api/v1/admin/imports/markdown",
        files=[("files", ("invalid.md", markdown_bytes(metadata), "text/markdown"))],
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 422
    assert client.get("/api/v1/admin/articles").json() == []


def test_import_rejects_yaml_aliases(client: TestClient) -> None:
    csrf = login(client)
    document = b"""---
type: article
title: &shared Alias title
slug: alias-title
summary: *shared
---

# Alias
"""

    response = client.post(
        "/api/v1/admin/imports/markdown",
        files=[("files", ("alias.md", document, "text/markdown"))],
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 422
    assert "aliases are not supported" in response.json()["detail"]


def test_import_enforces_front_matter_and_batch_size_limits(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    first = markdown_bytes({"type": "article", "title": "First", "slug": "first"})
    second = markdown_bytes({"type": "article", "title": "Second", "slug": "second"})
    monkeypatch.setattr(admin_content, "MAX_IMPORT_TOTAL_BYTES", len(first) + len(second) - 1)

    too_large = client.post(
        "/api/v1/admin/imports/markdown",
        files=[
            ("files", ("first.md", first, "text/markdown")),
            ("files", ("second.md", second, "text/markdown")),
        ],
        headers=headers,
    )
    assert too_large.status_code == 413
    assert client.get("/api/v1/admin/articles").json() == []

    monkeypatch.setattr(admin_content, "MAX_IMPORT_TOTAL_BYTES", 10 * 1024 * 1024)
    monkeypatch.setattr(admin_content, "MAX_FRONT_MATTER_BYTES", 20)
    front_matter_too_large = client.post(
        "/api/v1/admin/imports/markdown",
        files=[("files", ("first.md", first, "text/markdown"))],
        headers=headers,
    )
    assert front_matter_too_large.status_code == 413
    assert client.get("/api/v1/admin/articles").json() == []


def test_import_prevalidates_the_whole_batch_before_writing(client: TestClient) -> None:
    csrf = login(client)
    valid = markdown_bytes({"type": "article", "title": "Valid", "slug": "valid"})
    invalid = markdown_bytes(
        {"type": "article", "title": "Invalid", "slug": "invalid", "tag_slugs": "tag"}
    )

    response = client.post(
        "/api/v1/admin/imports/markdown",
        files=[
            ("files", ("valid.md", valid, "text/markdown")),
            ("files", ("invalid.md", invalid, "text/markdown")),
        ],
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 422
    assert client.get("/api/v1/admin/articles").json() == []


def test_import_enforces_metadata_complexity(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csrf = login(client)
    document = markdown_bytes(
        {
            "type": "article",
            "title": "Too complex",
            "slug": "too-complex",
            "tag_slugs": ["one", "two"],
        }
    )
    monkeypatch.setattr(admin_content, "MAX_METADATA_NODES", 3)

    response = client.post(
        "/api/v1/admin/imports/markdown",
        files=[("files", ("complex.md", document, "text/markdown"))],
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 422
    assert "front matter is too complex" in response.json()["detail"]
    assert client.get("/api/v1/admin/articles").json() == []


def with_crlf(document: bytes) -> bytes:
    return document.replace(b"\n", b"\r\n")


LINE_ENDING_CASES = [
    (
        "articles",
        "article",
        {
            "type": "article",
            "title": "换行对照文章",
            "slug": "line-ending",
            "summary": "对照摘要",
        },
        "# 换行对照\n\n第一行\n第二行",
    ),
    (
        "projects",
        "project",
        {
            "type": "project",
            "title": "换行对照项目",
            "slug": "line-ending",
            "summary": "对照摘要",
        },
        "# 项目正文\n\n第二段",
    ),
    (
        "books",
        "book",
        {
            "type": "book",
            "book_title": "换行对照书籍",
            "author": "对照作者",
            "slug": "line-ending",
            "summary": "对照摘要",
        },
        "# 书摘正文\n\n第二段",
    ),
]


def test_markdown_import_treats_lf_and_crlf_alike(
    client: TestClient,
) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    for endpoint, content_type, metadata, body in LINE_ENDING_CASES:
        lf_metadata = {**metadata, "slug": f"{metadata['slug']}-lf"}
        crlf_metadata = {**metadata, "slug": f"{metadata['slug']}-crlf"}
        response = client.post(
            "/api/v1/admin/imports/markdown",
            files=[
                ("files", ("lf.md", markdown_bytes(lf_metadata, body), "text/markdown")),
                (
                    "files",
                    ("crlf.md", with_crlf(markdown_bytes(crlf_metadata, body)), "text/markdown"),
                ),
            ],
            headers=headers,
        )
        assert response.status_code == 200, response.text
        imported = {item["filename"]: item for item in response.json()["imported"]}
        assert set(imported) == {"lf.md", "crlf.md"}
        for item in imported.values():
            assert item["content_type"] == content_type

        lf_row = client.get(
            f"/api/v1/admin/{endpoint}/{imported['lf.md']['content_id']}"
        ).json()
        crlf_row = client.get(
            f"/api/v1/admin/{endpoint}/{imported['crlf.md']['content_id']}"
        ).json()
        title_field = "book_title" if content_type == "book" else "title"
        assert crlf_row[title_field] == lf_row[title_field] == metadata[title_field]
        assert crlf_row["summary"] == lf_row["summary"] == "对照摘要"
        assert crlf_row["content"] == lf_row["content"]
        assert "\r" not in crlf_row["content"]
        assert "# " in crlf_row["content"]
        assert crlf_row["status"] == lf_row["status"] == "draft"
        assert client.get(f"/api/v1/{endpoint}").json() == []


def test_markdown_import_keeps_front_matter_validation_with_crlf(
    client: TestClient,
) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}

    def submit(name: str, document: bytes) -> tuple[int, str]:
        response = client.post(
            "/api/v1/admin/imports/markdown",
            files=[("files", (name, document, "text/markdown"))],
            headers=headers,
        )
        return response.status_code, response.json().get("detail", "")

    status, detail = submit(
        "plain.md",
        with_crlf(b"# \xe6\x97\xa0 front matter\n\n\xe6\xad\xa3\xe6\x96\x87\n"),
    )
    assert status == 422
    assert "front matter is required" in detail

    status, detail = submit(
        "unclosed.md",
        with_crlf(b"---\ntype: article\ntitle: Unclosed\nslug: unclosed\n\n# Body\n"),
    )
    assert status == 422
    assert "front matter is required" in detail

    status, detail = submit(
        "alias.md",
        with_crlf(
            b"---\ntype: article\ntitle: &shared Alias\n"
            b"slug: alias-crlf\nsummary: *shared\n---\n\n# Body\n"
        ),
    )
    assert status == 422
    assert "aliases are not supported" in detail

    status, detail = submit(
        "broken.md",
        with_crlf(b"---\ntype: article\ntitle: [unterminated\nslug: broken-crlf\n---\n\n# Body\n"),
    )
    assert status == 422
    assert "safe YAML" in detail

    status, detail = submit("binary.md", with_crlf(b"---\ntype: article\n---\n\n\xff\xfe\n"))
    assert status == 422
    assert "UTF-8 is required" in detail

    assert client.get("/api/v1/admin/articles").json() == []

    status, detail = submit(
        "valid.md",
        with_crlf(markdown_bytes({"type": "article", "title": "Valid CRLF", "slug": "valid-crlf"})),
    )
    assert status == 200, detail
    assert len(client.get("/api/v1/admin/articles").json()) == 1
