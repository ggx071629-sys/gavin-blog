"""Test-only in-process corpus bootstrap. Not an HTTP route."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..article_revisions import create_publish_revision, refresh_revision_content_hash
from ..assistant_index.outbox import enqueue_for_content
from ..assistant_index.worker import rebuild_generation
from ..config import Settings
from ..db import Database
from ..knowledge_links import rebuild_content_links, snapshot_working_references
from ..models import Article, AssistantIndexCommand
from ..search import sync_search_document
from ..time_utils import utc_now
from .admin_operations import finalize_rebuild, update_availability
from .readiness import write_receipt

# Public paths in the assistant e2e suite are pinned to this publication
# month, so the seeded article must not follow the wall clock.
TEST_ARTICLE_PUBLISHED_AT = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)


def bootstrap_test_assistant(settings: Settings, database: Database, online) -> None:
    if settings.environment != "test":
        raise RuntimeError("assistant test bootstrap refused outside test")
    db = database.session_factory()
    try:
        article = db.query(Article).filter(Article.slug == "python-notes").one_or_none()
        if article is None:
            article = Article(
                title="Python notes",
                slug="python-notes",
                summary="Published FastAPI notes",
                content="# Python\n\nI write about FastAPI, SQLite and published technical notes.",
                status="draft",
            )
            db.add(article)
            db.commit()
            db.refresh(article)
        article = db.query(Article).options(
            selectinload(Article.category),
            selectinload(Article.tags),
            selectinload(Article.current_revision),
            selectinload(Article.working_references),
        ).filter(Article.id == article.id).one()
        if article.status != "published":
            revision = create_publish_revision(
                db, article, first_published_at=TEST_ARTICLE_PUBLISHED_AT
            )
            snapshot_working_references(db, article, revision.id)
            refresh_revision_content_hash(db, article, revision)
            article.status = "published"
            article.published_at = TEST_ARTICLE_PUBLISHED_AT
            article.version += 1
            article.updated_at = utc_now()
            rebuild_content_links(db, article)
            sync_search_document(db, article)
            enqueue_for_content(db, article)
            db.commit()
    finally:
        db.close()
    generation_id = rebuild_generation(online.index_runtime)
    with database.session_factory() as command_db:
        command = command_db.scalar(
            select(AssistantIndexCommand).where(
                AssistantIndexCommand.generation_id == generation_id
            )
        )
        if command is None:
            raise RuntimeError("assistant test rebuild command is missing")
        operation_id = command.id
        operation_version = command.version
    finalize_rebuild(
        online,
        operation_id=operation_id,
        expected_version=operation_version,
        idempotency_key="test-bootstrap-finalize-key",
    )
    write_receipt(settings, probe_live=False, lock=online.lock)
    gate = online.control.read(
        lambda conn: conn.execute(
            "SELECT version FROM assistant_operational_gate WHERE id = 1"
        ).fetchone()
    )
    update_availability(online, enabled=True, expected_version=int(gate["version"]))
