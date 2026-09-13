from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import func, select

from ..models import (
    AssistantChunk,
    AssistantIndexTask,
    AssistantResumeRequest,
    AssistantResumeSource,
    Profile,
)
from .storage import usable_version


class ResumeRefresh(BaseModel):
    binding_epoch: int = Field(ge=0)


class ResumeStatus(BaseModel):
    state: Literal["unconfigured", "pending", "checking", "parsing", "indexing", "ready", "failed"]
    usable: bool
    binding_epoch: int
    request_id: str | None = None
    version_id: str | None = None
    last_attempt_at: datetime | None = None
    last_checked_at: datetime | None = None
    last_indexed_at: datetime | None = None
    retry_at: datetime | None = None
    error_code: str | None = None


def status_view(db) -> ResumeStatus:
    row = db.get(AssistantResumeSource, 1, populate_existing=True)
    if row is None:
        profile = db.get(Profile, 1)
        return ResumeStatus(
            state="pending" if profile and profile.resume_url else "unconfigured",
            usable=False,
            binding_epoch=0,
        )
    version = usable_version(db)
    state = row.state
    error = row.error_code
    request = (
        db.get(AssistantResumeRequest, row.current_request_id) if row.current_request_id else None
    )
    indexed_at = row.last_indexed_at
    if indexed_at is None and row.current_version_id:
        indexed_at = db.scalar(
            select(func.max(AssistantChunk.created_at)).where(
                AssistantChunk.source_type == "resume",
                AssistantChunk.source_version == row.current_version_id,
            )
        )
    if version:
        if state == "indexing":
            state = "ready"
    elif state == "indexing":
        task = db.scalar(
            select(AssistantIndexTask)
            .where(
                AssistantIndexTask.source_type == "resume",
                AssistantIndexTask.operation == "upsert",
                AssistantIndexTask.target_version == row.current_version_id,
            )
            .order_by(AssistantIndexTask.id.desc())
            .limit(1)
        )
        if task and task.status == "failed":
            state, error = "failed", "index_failed"
    return ResumeStatus(
        state=state,
        usable=version is not None,
        binding_epoch=row.binding_epoch,
        request_id=row.current_request_id,
        version_id=row.current_version_id,
        last_attempt_at=row.last_attempt_at,
        last_checked_at=row.last_checked_at,
        last_indexed_at=indexed_at,
        retry_at=request.available_at
        if request and request.status == "pending" and error
        else None,
        error_code=error,
    )
