from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from sqlalchemy import delete, exists, select, update
from sqlalchemy.orm import Session

from ..models import (
    AssistantChunk,
    AssistantIndexPointer,
    AssistantIndexWorkerState,
    AssistantResumeRequest,
    AssistantResumeSource,
    AssistantResumeVersion,
)
from ..time_utils import utc_now
from .download import DownloadedPdf
from .parse import MAX_CHARS, MAX_PAGES, PARSER_VERSION, ParsedPdf


class ResumeLeaseLost(Exception):
    pass


@dataclass(frozen=True)
class ResumeLease:
    epoch: int
    request_id: str
    owner: str
    token: str
    fence: int


def source(db: Session) -> AssistantResumeSource:
    row = db.get(AssistantResumeSource, 1)
    if row is None:
        row = AssistantResumeSource(id=1)
        db.add(row)
        db.flush()
    return row


def _purge(db: Session, version_id: str) -> None:
    from ..assistant_index.outbox import enqueue_task

    enqueue_task(
        db, source_type="resume", source_id=1, target_version=version_id, operation="purge"
    )


def bind(db: Session, url: str | None) -> AssistantResumeSource:
    """Call in the same write transaction as the Profile URL update; never commit."""
    row = source(db)
    url = url or None
    if row.url == url:
        return row
    row.binding_epoch += 1
    row.url = url
    row.enabled = False
    row.state = "pending" if url else "unconfigured"
    row.current_version_id = None
    row.current_request_id = None
    row.error_code = None
    row.last_attempt_at = row.last_checked_at = row.last_indexed_at = None
    row.last_refresh_at = None
    for version_id in db.scalars(select(AssistantResumeVersion.id)):
        _purge(db, version_id)
    db.execute(delete(AssistantResumeVersion))
    db.execute(delete(AssistantResumeRequest))
    db.flush()
    return row


def guard(db: Session, lease: ResumeLease, now: datetime) -> AssistantResumeSource:
    """Acquire SQLite write ownership and validate every fence in one statement."""
    request_ok = exists().where(
        AssistantResumeRequest.id == lease.request_id,
        AssistantResumeRequest.binding_epoch == lease.epoch,
        AssistantResumeRequest.status == "leased",
        AssistantResumeRequest.lease_owner == lease.owner,
        AssistantResumeRequest.lease_token == lease.token,
        AssistantResumeRequest.worker_fence == lease.fence,
        AssistantResumeRequest.lease_expires_at > now,
    )
    owner_ok = exists().where(
        AssistantIndexWorkerState.id == 1,
        AssistantIndexWorkerState.owner_id == lease.owner,
        AssistantIndexWorkerState.fencing_token == lease.fence,
        AssistantIndexWorkerState.lease_expires_at > now,
    )
    matched = db.execute(
        update(AssistantResumeSource)
        .where(
            AssistantResumeSource.id == 1,
            AssistantResumeSource.binding_epoch == lease.epoch,
            AssistantResumeSource.current_request_id == lease.request_id,
            AssistantResumeSource.url.is_not(None),
            request_ok,
            owner_ok,
        )
        .values(binding_epoch=AssistantResumeSource.binding_epoch),
        execution_options={"synchronize_session": False},
    )
    if matched.rowcount != 1:
        raise ResumeLeaseLost("resume_lease_lost")
    return db.get(AssistantResumeSource, 1, populate_existing=True)


def current_version(db: Session, row: AssistantResumeSource) -> AssistantResumeVersion | None:
    version = (
        db.get(AssistantResumeVersion, row.current_version_id) if row.current_version_id else None
    )
    if version is None or version.binding_epoch != row.binding_epoch:
        return None
    return version


def accept_download(
    db: Session, lease: ResumeLease, pdf: DownloadedPdf, *, now: datetime | None = None
) -> bool:
    """False means same parser/hash reused; True requires parsing after committing suspension."""
    now = now or utc_now()
    row = guard(db, lease, now)
    if hashlib.sha256(pdf.body).hexdigest() != pdf.sha256:
        raise ValueError("download_hash_mismatch")
    version = current_version(db, row)
    row.last_checked_at = now
    row.error_code = None
    if version and version.sha256 == pdf.sha256 and version.parser_version == PARSER_VERSION:
        row.enabled = True
        row.state = "indexing"
        request = db.get(AssistantResumeRequest, lease.request_id)
        request.status = "succeeded"
        from ..assistant_index.outbox import enqueue_task

        enqueue_task(
            db, source_type="resume", source_id=1, target_version=version.id, operation="upsert"
        )
        return False
    row.enabled = False
    row.state = "parsing"
    return True


def accept_parsed(
    db: Session,
    lease: ResumeLease,
    pdf: DownloadedPdf,
    parsed: ParsedPdf,
    *,
    now: datetime | None = None,
) -> AssistantResumeVersion:
    now = now or utc_now()
    row = guard(db, lease, now)
    if row.state != "parsing" or row.enabled:
        raise ResumeLeaseLost("resume_parse_not_started")
    if (
        hashlib.sha256(pdf.body).hexdigest() != pdf.sha256
        or not pdf.body.startswith(b"%PDF-")
        or len(pdf.body) > 10485760
        or not 1 <= len(parsed.pages) <= MAX_PAGES
        or not parsed.body
        or len(parsed.body) > MAX_CHARS
        or parsed.parser_version != PARSER_VERSION
    ):
        raise ValueError("invalid_parsed_pdf")
    version = AssistantResumeVersion(
        id=uuid4().hex,
        binding_epoch=row.binding_epoch,
        sha256=pdf.sha256,
        parser_version=parsed.parser_version,
        pdf_bytes=pdf.body,
        pages_json=json.dumps(parsed.pages, ensure_ascii=False),
        body=parsed.body,
        created_at=now,
    )
    for old_id in db.scalars(select(AssistantResumeVersion.id)):
        _purge(db, old_id)
    db.execute(delete(AssistantResumeVersion))
    db.add(version)
    row.current_version_id = version.id
    row.enabled = True
    row.state = "indexing"
    row.error_code = None
    row.last_indexed_at = None
    db.get(AssistantResumeRequest, lease.request_id).status = "succeeded"
    from ..assistant_index.outbox import enqueue_task

    enqueue_task(
        db, source_type="resume", source_id=1, target_version=version.id, operation="upsert"
    )
    db.flush()
    return version


def fail(db: Session, lease: ResumeLease, code: str, *, now: datetime | None = None) -> None:
    from .download import ERROR_CODES as DOWNLOAD_CODES
    from .parse import ERROR_CODES as PARSE_CODES

    row = guard(db, lease, now or utc_now())
    row.enabled = False
    row.state = "failed"
    row.error_code = (
        code if code in (DOWNLOAD_CODES | PARSE_CODES | {"index_failed"}) else "download_failed"
    )
    db.get(AssistantResumeRequest, lease.request_id).status = "failed"


def usable_version(db: Session) -> AssistantResumeVersion | None:
    row = db.get(AssistantResumeSource, 1, populate_existing=True)
    if row is None or not row.url or not row.enabled:
        return None
    version = current_version(db, row)
    pointer = db.get(AssistantIndexPointer, 1, populate_existing=True)
    if version is None or pointer is None or not pointer.active_generation_id:
        return None
    indexed = db.scalar(
        select(AssistantChunk.id)
        .where(
            AssistantChunk.source_type == "resume",
            AssistantChunk.source_id == 1,
            AssistantChunk.source_version == version.id,
            AssistantChunk.generation_id == pointer.active_generation_id,
        )
        .limit(1)
    )
    return version if indexed else None
