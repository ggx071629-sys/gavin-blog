from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.about_page_service import (
    create_publish_revision,
    get_or_create_about_page,
    parse_content,
    serialize_content,
)
from app.assistant_index.projector import project_about, project_source
from app.config import get_settings
from app.models import AssistantIndexTask


def test_about_projection_excludes_seed_and_draft_and_preserves_published_structure(client):
    with client.app.state.database.session_factory() as db:
        assert project_about(db) is None
        page = get_or_create_about_page(db)
        assert project_about(db) is None
        content = parse_content(page.content_json)
        content.statement = "明确发布的个人介绍"
        page.content_json = serialize_content(content)
        db.commit()
        assert project_about(db) is None
        revision = create_publish_revision(db, page)
        db.commit()
        document = project_source(db, "about", 1)
        assert document is not None
        assert (document.title, document.public_path, document.source_version) == (
            "关于 Gavin", "/about", str(revision.id),
        )
        for value in (
            content.statement, content.capabilities[0].title,
            content.capabilities[0].description, content.capabilities[0].tags[0],
            content.now[0].label, content.editorial_topics[0],
            content.site.description, content.site.stack[0].value,
        ):
            assert value in document.body
        content.statement = "禁止泄漏的未发布草稿"
        page.content_json = serialize_content(content)
        db.commit()
        assert project_about(db) == document
        rollback = create_publish_revision(db, page, source="rollback")
        db.commit()
        assert rollback.assistant_eligible
        assert project_about(db).source_version == str(rollback.id)
        assert project_source(db, "about", 999) is None
        page.current_revision_id = None
        db.commit()
        assert project_about(db) is None


def test_about_migration_preserves_existing_sources_and_qualifies_only_explicit_revisions(
    tmp_path, monkeypatch,
):
    url = "sqlite:///" + (tmp_path / "about-upgrade.db").as_posix()
    monkeypatch.setenv("GAVIN_DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    engine = create_engine(url)
    try:
        command.upgrade(config, "20260910_0028")
        with engine.begin() as conn:
            conn.execute(text("UPDATE profiles SET title = 'preserve profile' WHERE id = 1"))
            conn.execute(text(
                "INSERT INTO about_page_revisions "
                "(id, about_page_id, revision_number, content_json, content_sha256, source, "
                "first_published_at, published_at, created_at) "
                "SELECT 2, about_page_id, 2, content_json, content_sha256, 'editor', "
                "first_published_at, published_at, created_at FROM about_page_revisions WHERE id=1"
            ))
        with Session(engine) as db:
            for kind in ("article", "project", "book", "profile"):
                db.add(AssistantIndexTask(
                    source_type=kind, source_id=1, target_version="1",
                    pipeline_version="assistant-index-v1", operation="upsert",
                ))
            db.commit()
        command.upgrade(config, "20260911_0029")
        with engine.connect() as conn:
            assert conn.execute(text(
                "SELECT revision_number, assistant_eligible FROM about_page_revisions "
                "ORDER BY revision_number"
            )).all() == [(1, 0), (2, 1)]
            assert conn.scalar(text("SELECT title FROM profiles WHERE id=1")) == "preserve profile"
        with Session(engine) as db:
            assert set(db.scalars(select(AssistantIndexTask.source_type))) == {
                "article", "project", "book", "profile",
            }
            db.add(AssistantIndexTask(
                source_type="about", source_id=1, target_version="2",
                pipeline_version="assistant-index-v1", operation="upsert",
            ))
            db.commit()
            db.add(AssistantIndexTask(
                source_type="untrusted", source_id=1, target_version="2",
                pipeline_version="assistant-index-v1", operation="upsert",
            ))
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()
        for table in ("assistant_chunks", "assistant_index_tasks"):
            assert any(
                "'about'" in row["sqltext"] for row in inspect(engine).get_check_constraints(table)
            )
    finally:
        engine.dispose()
        get_settings.cache_clear()
