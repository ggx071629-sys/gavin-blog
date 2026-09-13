from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import delete, text

from ..assistant.errors import AssistantOwnerLockError
from ..assistant_index.worker_control import acquire_worker_owner
from ..content_write_fence import content_write_fence
from ..models import (
    AssistantIndexWorkerState,
    AssistantResumeRequest,
    AssistantResumeSource,
    Profile,
)
from ..time_utils import utc_now
from .download import DownloadError, download_pdf
from .parse import ParseError, parse_pdf
from .storage import (
    ResumeLease,
    ResumeLeaseLost,
    accept_download,
    accept_parsed,
    bind,
    fail,
    source,
)

BACKOFF_SECONDS = (60, 300, 900)
LEASE_SECONDS = 90  # Download 30s + parse 15s, including process startup and short commits.


class RefreshConflict(Exception):
    pass


class RefreshCooldown(Exception):
    def __init__(self, seconds: int):
        self.seconds = seconds


def enqueue(db, row, *, manual: bool = False, now=None):
    now = now or utc_now()
    current = (
        db.get(AssistantResumeRequest, row.current_request_id) if row.current_request_id else None
    )
    if (
        current
        and current.binding_epoch == row.binding_epoch
        and current.status in {"pending", "leased"}
    ):
        return current
    if manual and row.last_refresh_at:
        remaining = 60 - (now - row.last_refresh_at).total_seconds()
        if remaining > 0:
            raise RefreshCooldown(max(1, int(remaining + 0.999)))
    db.execute(delete(AssistantResumeRequest))
    request = AssistantResumeRequest(
        id=uuid4().hex, binding_epoch=row.binding_epoch, available_at=now, created_at=now
    )
    db.add(request)
    row.current_request_id = request.id
    row.state = "pending"
    row.error_code = None
    if manual:
        row.last_refresh_at = now
    db.flush()
    return request


def sync_binding(db, url: str | None):
    row = source(db)
    changed = row.url != (url or None)
    row = bind(db, url)
    if changed and row.url:
        enqueue(db, row)
    return row


def refresh(db, epoch: int, *, now=None):
    row = source(db)
    if row.binding_epoch != epoch or not row.url:
        raise RefreshConflict("resume_binding_changed_or_unconfigured")
    return enqueue(db, row, manual=True, now=now)


@contextmanager
def _write(runtime):
    lock = content_write_fence(runtime.settings)
    lock.acquire()
    try:
        with runtime.database.session_factory() as db:
            db.info["settings"] = runtime.settings
            db.execute(text("BEGIN IMMEDIATE"))
            yield db
            db.commit()
    finally:
        lock.release()


def _claim(db, runtime):
    # Upgrade bootstrap is performed by the worker once, never by public/admin GET.
    if db.get(AssistantResumeSource, 1) is None:
        profile = db.get(Profile, 1)
        sync_binding(db, profile.resume_url if profile else None)
    row = source(db)
    request = (
        db.get(AssistantResumeRequest, row.current_request_id) if row.current_request_id else None
    )
    now = runtime.now()
    if not request or not row.url or request.binding_epoch != row.binding_epoch:
        return None
    if request.status == "leased":
        if request.lease_expires_at and request.lease_expires_at > now:
            return None
        # An abandoned attempt consumed the same finite attempt budget.
        request.status = "pending"
        row.enabled = False
        row.state = "failed"
        row.error_code = "download_failed"
    if request.status != "pending" or request.available_at > now:
        return None
    if request.attempt_count >= 4:
        request.status = "failed"
        row.state = "failed"
        row.enabled = False
        row.error_code = "download_failed"
        return None
    fence = acquire_worker_owner(db, runtime)
    if fence is None:
        return None
    expires = now + timedelta(seconds=LEASE_SECONDS)
    db.get(AssistantIndexWorkerState, 1).lease_expires_at = expires
    request.status = "leased"
    request.attempt_count += 1
    request.lease_owner = runtime.owner
    request.lease_token = uuid4().hex
    request.worker_fence = fence
    request.lease_expires_at = expires
    row.last_attempt_at = now
    row.state = "checking"
    row.error_code = None
    return ResumeLease(
        row.binding_epoch, request.id, runtime.owner, request.lease_token, fence
    ), row.url


def process_resume_once(runtime) -> bool:
    lease = None
    try:
        with _write(runtime) as db:
            claimed = _claim(db, runtime)
        if claimed is None:
            return False
        lease, url = claimed
        hosts = tuple(
            h.strip()
            for h in runtime.settings.assistant_resume_trusted_hosts.split(",")
            if h.strip()
        )
        downloaded = download_pdf(url, hosts, force_refresh=True)
        with _write(runtime) as db:
            needs_parse = accept_download(db, lease, downloaded, now=runtime.now())
        if needs_parse:
            parsed = parse_pdf(downloaded.body)
            with _write(runtime) as db:
                accept_parsed(db, lease, downloaded, parsed, now=runtime.now())
        return True
    except (DownloadError, ParseError) as exc:
        try:
            with _write(runtime) as db:
                fail(db, lease, exc.code, now=runtime.now())
                request = db.get(AssistantResumeRequest, lease.request_id)
                if isinstance(exc, DownloadError) and exc.transient and request.attempt_count < 4:
                    delay = max(BACKOFF_SECONDS[request.attempt_count - 1], exc.retry_after or 0)
                    request.status = "pending"
                    request.available_at = runtime.now() + timedelta(seconds=delay)
                request.lease_owner = request.lease_token = None
                request.lease_expires_at = None
                request.worker_fence = None
        except (ResumeLeaseLost, AssistantOwnerLockError):
            pass  # Replacement or backup won the write boundary; never revive the old result.
        return True
    except (ResumeLeaseLost, AssistantOwnerLockError):
        return lease is not None
