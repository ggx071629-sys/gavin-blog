from dataclasses import replace

from app.assistant.hydrate import (
    _article_parts,
    _content_role,
    hydrate_descriptors,
    hydrate_evidence,
)
from app.assistant.prompt import _evidence_block
from app.assistant_index.projector import project_source
from app.models import Article

from .conftest import login, publish_article
from .test_assistant_online import _online_client, _publish_and_index


def test_role_requires_unambiguous_complete_current_field_match():
    parts = ("Title summary overlap", "# Body overlap actual fact")
    for text, role in [
        ("summary", "metadata"), ("# Body\n\n overlap actual fact", "body"),
        ("overlap", "unknown"), ("summary # Body", "unknown"),
        ("", "unknown"), ("invented body", "unknown"),
    ]:
        assert _content_role(text, parts) == role
    assert _content_role("actual fact", ("", "")) == "unknown"


def test_current_article_roles_survive_restore_without_public_descriptor_change(tmp_path):
    with _online_client(tmp_path) as client:
        headers = {"X-CSRF-Token": login(client)}
        created = client.post("/api/v1/admin/articles", headers=headers, json={
            "title": "正文归属测试", "slug": "article-content-role",
            "summary": "独立摘要不是正文。", "content": "# 正文\n\n第一句只在正文。",
        })
        assert created.status_code == 201
        assert publish_article(client, created.json(), headers).status_code == 200
        _publish_and_index(client)
        online = client.app.state.assistant
        with online.content_session() as db:
            found = hydrate_evidence(
                db, online.index_runtime, "正文", limit=20, max_chars=20000,
            )
            items = [e for e in found.evidence if e.title == "正文归属测试"]
            assert {e.content_role for e in items} == {"metadata", "body"}
            source = project_source(db, "article", items[0].source_id)
            assert source is not None
            assert _article_parts(db, replace(source, source_version="missing")) == ("", "")
            assert _article_parts(db, replace(source, source_id=-1)) == ("", "")
            assert _article_parts(db, replace(source, source_type="profile")) == ("", "")
            assert _article_parts(db, replace(source, body="different")) == ("", "")
            descriptors = [e.descriptor() for e in items]
            assert all("content_role" not in d and "body" not in d for d in descriptors)
            restored = hydrate_descriptors(db, descriptors)
            assert restored == items
            for item in restored:
                block = _evidence_block(item)
                assert f'"content_role":"{item.content_role}"' in block
                assert item.body in block
            assert project_source(db, "article", items[0].source_id) == source
            # Caller-supplied descriptors cannot overwrite the derived role.
            poisoned = [{**d, "content_role": "metadata"} for d in descriptors]
            assert hydrate_descriptors(db, poisoned) == items
            article = db.get(Article, items[0].source_id)
            article.status = "draft"
            db.commit()
            assert hydrate_descriptors(db, descriptors) == []
            found = hydrate_evidence(
                db, online.index_runtime, "正文", limit=20, max_chars=20000,
            )
            assert not [e for e in found.evidence if e.source_id == article.id
                        and e.source_type == "article"]
