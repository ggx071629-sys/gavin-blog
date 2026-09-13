from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.article_revisions import create_publish_revision
from app.content_revisions import create_book_note_publish_revision, create_project_publish_revision
from app.models import Article, BookNote, Project

from .conftest import login


def test_admin_queries_filter_before_pagination_and_count_real_rows(client: TestClient):
    stamp = datetime(2026, 9, 1, tzinfo=UTC)
    for kind in ("articles", "books", "projects"):
        assert client.get(f"/api/v1/admin/{kind}/query").status_code == 401
    login(client)
    with client.app.state.database.session_factory() as db:
        for model in (Article, BookNote, Project):
            for index in range(25):
                title = f"Needle {index} 100%_"
                fields = (
                    {"book_title": title, "author": "Writer"}
                    if model is BookNote
                    else {"title": title}
                )
                item = model(
                    **fields,
                    slug=f"query-{index}",
                    status="draft" if index % 2 else "published",
                    updated_at=stamp,
                    published_at=stamp if index % 2 == 0 else None,
                )
                db.add(item)
                db.flush()
                if index % 2 == 0:
                    {
                        Article: create_publish_revision,
                        BookNote: create_book_note_publish_revision,
                        Project: create_project_publish_revision,
                    }[model](db, item)
            fields = (
                {"book_title": "Deleted", "author": "Writer"}
                if model is BookNote
                else {"title": "Deleted"}
            )
            db.add(model(**fields, slug="deleted", deleted_at=stamp))
        db.commit()
    for kind in ("articles", "books", "projects"):
        path = f"/api/v1/admin/{kind}/query"
        response = client.get(
            path, params={"q": " needle ", "status": "draft", "limit": 2, "offset": 2}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["counts"] == {"all": 25, "published": 13, "draft": 12}
        assert data["total"] == 12
        assert [r["id"] for r in data["items"]] == [20, 18]
        assert all(r["status"] == "draft" for r in data["items"])
        assert client.get(path, params={"q": "Needle 0"}).json()["total"] == 1
        assert client.get(path, params={"q": "%_"}).json()["total"] == 25
        assert client.get(path, params={"q": "%missing"}).json()["total"] == 0
        assert client.get(path, params={"q": "absent"}).json()["items"] == []
        assert client.get(path, params={"offset": 100}).json()["items"] == []
        for params in ({"status": "invalid"}, {"q": "x" * 201}, {"limit": 101}, {"offset": -1}):
            assert client.get(path, params=params).status_code == 422
        assert isinstance(client.get(f"/api/v1/admin/{kind}").json(), list)
        assert client.get(f"/api/v1/{kind}").status_code == 200
    assert client.get("/api/v1/admin/books/query", params={"q": "Writer"}).json()["total"] == 25
