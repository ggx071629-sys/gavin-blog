from __future__ import annotations

import threading
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..assistant.crypto import random_id
from ..models import (
    AssistantIndexProviderFact,
    AssistantIndexRepairIntent,
    AssistantIndexTask,
    AssistantIndexWorkerState,
)
from .projector import project_source

WORKER_STATE_ID = 1


class WorkerFenceLost(RuntimeError):
    pass


def ensure_worker_state(db: Session, runtime) -> AssistantIndexWorkerState:
    row = db.get(AssistantIndexWorkerState, WORKER_STATE_ID)
    if row is None:
        row = AssistantIndexWorkerState(
            id=WORKER_STATE_ID,
            owner_id=None,
            fencing_token=0,
            updated_at=runtime.now(),
        )
        db.add(row)
        db.flush()
    return row


def acquire_worker_owner(db: Session, runtime) -> int | None:
    now = runtime.now()
    row = ensure_worker_state(db, runtime)
    same_owner = row.owner_id == runtime.owner
    expired = row.lease_expires_at is None or row.lease_expires_at <= now
    if not same_owner and not expired:
        return None
    if not same_owner:
        row.fencing_token += 1
    row.owner_id = runtime.owner
    row.heartbeat_at = now
    row.lease_expires_at = now + timedelta(
        seconds=runtime.settings.assistant_index_lease_seconds
    )
    row.updated_at = now
    db.flush()
    return int(row.fencing_token)


def renew_worker_owner(db: Session, runtime, fence: int) -> bool:
    row = ensure_worker_state(db, runtime)
    if row.owner_id != runtime.owner or int(row.fencing_token) != int(fence):
        return False
    now = runtime.now()
    row.heartbeat_at = now
    row.lease_expires_at = now + timedelta(
        seconds=runtime.settings.assistant_index_lease_seconds
    )
    row.updated_at = now
    db.flush()
    return True


def worker_fence_valid(
    runtime,
    fence: int,
    *,
    task_id: int | None = None,
    token: str | None = None,
) -> bool:
    with runtime.database.session_factory() as db:
        row = db.get(AssistantIndexWorkerState, WORKER_STATE_ID)
        if (
            row is None
            or row.owner_id != runtime.owner
            or int(row.fencing_token) != int(fence)
            or row.lease_expires_at is None
            or row.lease_expires_at <= runtime.now()
        ):
            return False
        if task_id is None:
            return True
        task = db.get(AssistantIndexTask, task_id)
        return bool(
            task
            and task.status == "leased"
            and task.worker_fence == fence
            and task.lease_token == token
            and task.lease_owner == runtime.owner
            and task.lease_expires_at is not None
            and task.lease_expires_at > runtime.now()
        )


def require_worker_fence(
    runtime,
    fence: int,
    *,
    task_id: int | None = None,
    token: str | None = None,
) -> None:
    if not worker_fence_valid(runtime, fence, task_id=task_id, token=token):
        raise WorkerFenceLost("assistant index worker fence was lost")


def require_source_revision(
    runtime,
    *,
    source_type: str,
    source_id: int,
    expected_version: str,
) -> None:
    with runtime.database.session_factory() as db:
        db.info["settings"] = runtime.settings
        current = project_source(db, source_type, source_id)
        actual = current.source_version if current is not None else "0"
    if actual != expected_version:
        raise WorkerFenceLost("assistant index source revision changed")


def renew_task_and_owner(runtime, fence: int, task_id: int | None, token: str | None) -> bool:
    with runtime.database.session_factory() as db:
        if not renew_worker_owner(db, runtime, fence):
            db.rollback()
            return False
        if task_id is not None:
            task = db.get(AssistantIndexTask, task_id)
            if (
                task is None
                or task.status != "leased"
                or task.worker_fence != fence
                or task.lease_token != token
            ):
                db.rollback()
                return False
            task.lease_expires_at = runtime.now() + timedelta(
                seconds=runtime.settings.assistant_index_lease_seconds
            )
            task.updated_at = runtime.now()
        db.commit()
        return True


class FenceHeartbeat:
    def __init__(
        self,
        runtime,
        fence: int,
        *,
        task_id: int | None = None,
        token: str | None = None,
    ) -> None:
        self.runtime = runtime
        self.fence = fence
        self.task_id = task_id
        self.token = token
        self.stop_event = threading.Event()
        self.lost = False
        self.thread: threading.Thread | None = None

    def __enter__(self):
        interval = max(
            0.1,
            min(2.0, float(self.runtime.settings.assistant_index_lease_seconds) / 3),
        )

        def beat() -> None:
            while not self.stop_event.wait(interval):
                if not renew_task_and_owner(
                    self.runtime, self.fence, self.task_id, self.token
                ):
                    self.lost = True
                    return

        self.thread = threading.Thread(target=beat, name="assistant-index-heartbeat", daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=1.0)
        if exc_type is None and self.lost:
            raise WorkerFenceLost("assistant index heartbeat lost its fence")


def record_repair_intent(
    runtime,
    *,
    source_type: str,
    source_id: int,
    generation_id: int,
    reason_code: str,
) -> None:
    with runtime.database.session_factory() as db:
        db.info["settings"] = runtime.settings
        current = project_source(db, source_type, source_id)
        target_version = current.source_version if current is not None else "0"
        existing = db.scalar(
            select(AssistantIndexRepairIntent).where(
                AssistantIndexRepairIntent.source_type == source_type,
                AssistantIndexRepairIntent.source_id == source_id,
                AssistantIndexRepairIntent.target_version == target_version,
                AssistantIndexRepairIntent.generation_id == generation_id,
            )
        )
        if existing is None:
            db.add(
                AssistantIndexRepairIntent(
                    source_type=source_type,
                    source_id=source_id,
                    target_version=target_version,
                    generation_id=generation_id,
                    reason_code=reason_code,
                    status="pending",
                    created_at=runtime.now(),
                    updated_at=runtime.now(),
                )
            )
        db.commit()


def record_provider_fact(runtime, *, kind: str, status: str, reason: str, outcome: str) -> None:
    with runtime.database.session_factory() as db:
        row = db.get(AssistantIndexProviderFact, kind)
        if row is None:
            row = AssistantIndexProviderFact(
                kind=kind,
                status=status,
                reason_code=reason,
                outcome=outcome,
                observed_at=runtime.now(),
            )
            db.add(row)
        else:
            row.status = status
            row.reason_code = reason
            row.outcome = outcome
            row.observed_at = runtime.now()
        db.commit()


def new_lease_token() -> str:
    return random_id()
