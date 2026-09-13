from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AboutPage, Article, AssistantIndexTask, BookNote, Profile, Project
from ..profile_service import PROFILE_SINGLETON_ID
from ..time_utils import utc_now
from .constants import (
    OP_DELETE,
    OP_PURGE,
    OP_UPSERT,
    SOURCE_ABOUT,
    SOURCE_ARTICLE,
    SOURCE_BOOK,
    SOURCE_PROFILE,
    SOURCE_PROJECT,
    STATUS_PENDING,
)
from .projector import pipeline_version_from


def _kind(content: Article | Project | BookNote) -> str:
    if isinstance(content, Article):
        return SOURCE_ARTICLE
    if isinstance(content, Project):
        return SOURCE_PROJECT
    return SOURCE_BOOK


def enqueue_task(
    db: Session,
    *,
    source_type: str,
    source_id: int,
    target_version: str,
    operation: str,
    pipeline_version: str | None = None,
) -> AssistantIndexTask:
    version = pipeline_version or pipeline_version_from(db)
    now = utc_now()
    pending = select(AssistantIndexTask).where(
            AssistantIndexTask.source_type == source_type,
            AssistantIndexTask.source_id == source_id,
            AssistantIndexTask.status == STATUS_PENDING,
        )
    if source_type == "resume":
        # Never merge a version tombstone into a new-version upsert (or vice versa).
        pending = pending.where(AssistantIndexTask.operation == operation)
        if operation == OP_PURGE:
            pending = pending.where(AssistantIndexTask.target_version == target_version)
    existing = db.scalar(
        pending
        .order_by(AssistantIndexTask.id.desc())
        .limit(1)
    )
    if existing is not None:
        existing.target_version = target_version
        existing.operation = operation
        existing.pipeline_version = version
        existing.available_at = now
        existing.updated_at = now
        existing.last_error_summary = None
        return existing
    task = AssistantIndexTask(
        source_type=source_type,
        source_id=source_id,
        target_version=target_version,
        pipeline_version=version,
        operation=operation,
        status=STATUS_PENDING,
        attempt_count=0,
        available_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.flush()
    return task


def enqueue_for_content(db: Session, content: Article | Project | BookNote) -> AssistantIndexTask:
    current = getattr(content, "current_revision_id", None)
    if (
        content.status == "published"
        and content.deleted_at is None
        and current is not None
    ):
        operation = OP_UPSERT
        target_version = str(current)
    else:
        operation = OP_DELETE
        target_version = str(current or 0)
    return enqueue_task(
        db,
        source_type=_kind(content),
        source_id=content.id,
        target_version=target_version,
        operation=operation,
    )


def enqueue_purge(db: Session, content: Article | Project | BookNote) -> AssistantIndexTask:
    current = getattr(content, "current_revision_id", None)
    return enqueue_task(
        db,
        source_type=_kind(content),
        source_id=content.id,
        target_version=str(current or 0),
        operation=OP_PURGE,
    )


def enqueue_profile(db: Session, profile: Profile) -> AssistantIndexTask:
    return enqueue_task(
        db,
        source_type=SOURCE_PROFILE,
        source_id=PROFILE_SINGLETON_ID,
        target_version=str(profile.version),
        operation=OP_UPSERT,
    )


def enqueue_about(db: Session, page: AboutPage) -> AssistantIndexTask:
    return enqueue_task(
        db,
        source_type=SOURCE_ABOUT,
        source_id=page.id,
        target_version=str(page.current_revision_id),
        operation=OP_UPSERT,
    )
