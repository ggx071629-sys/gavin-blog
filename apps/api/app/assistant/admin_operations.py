from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import case, func, select, text
from sqlalchemy.orm import Session

from ..assistant_index.projector import (
    iter_public_sources,
    pipeline_version_from,
    project_source,
    source_revision_set_digest,
)
from ..http_errors import ApiException
from ..models import (
    AssistantIndexCommand,
    AssistantIndexEmbeddingAttempt,
    AssistantIndexEmbeddingBudget,
    AssistantIndexGeneration,
    AssistantIndexPointer,
    AssistantIndexProviderFact,
    AssistantIndexTask,
    AssistantIndexWorkerState,
)
from ..time_utils import utc_now
from .admin_schemas import (
    AssistantAdminSnapshot,
    AvailabilityView,
    BudgetKind,
    BudgetView,
    DailyActivityView,
    DeploymentView,
    IndexTaskList,
    IndexTaskOperation,
    IndexTaskStatus,
    IndexTaskView,
    ManifestView,
    ObservationStatus,
    ObservedFact,
    OperationKind,
    OperationStatus,
    OperationView,
    QueueView,
    RetryTaskResponse,
    TaskSourceType,
)
from .crypto import random_id
from .money import cny_to_micro
from .operational import (
    STATE_ENABLED,
    disable_gate,
    enable_gate,
    fail_closed_snapshot,
    gate_json,
    gate_row,
    validate_enabled_binding,
)
from .readiness import verify_receipt
from .recovery import online_lock_until
from .store import breaker_open, current_receipt
from .time_beijing import beijing_date

IDEMPOTENCY_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
NONTERMINAL_OPERATIONS = {
    "pending",
    "running",
    "waiting",
    "catch_up",
    "ready_to_switch",
    "switch_pending",
}
SAFE_MESSAGES = {
    "input_budget_exceeded": (
        "问题与检索资料超过模型输入上限，本次未调用模型；请检查输入预算与资料选取。"
    ),
    "index_task_failed": "索引任务失败，可在确认当前公开事实后重试。",
    "index_vectors_unavailable": (
        "此前向量计算已成功，但已存向量不可复用；已停止自动重试，请检查向量存储或重建索引。"
    ),
    "embedding_budget_waiting": "索引费用额度不足，任务将在下一个北京时间账期继续。",
    "provider_result_unknown": "供应商结果未知；系统不会自动重发。",
    "worker_fence_lost": "Worker 已失去所有权，当前事实会由新 owner 修复。",
    "source_changed": "公开内容已变化，操作将重新进入追赶阶段。",
    "rebuild_failed": "重建失败，现有 active generation 未改变。",
}


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _as_utc(value: Any) -> datetime | None:
    if value is None:
        return None
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _freshness(value: Any, now: datetime) -> int | None:
    stamp = _as_utc(value)
    current = _as_utc(now)
    if stamp is None or current is None:
        return None
    return max(0, int((current - stamp).total_seconds()))


def _fact(
    *,
    status: str,
    reason: str,
    observed_at: Any,
    now: datetime,
    stale_after: int | None = None,
) -> ObservedFact:
    age = _freshness(observed_at, now)
    stale = age is None or (stale_after is not None and age > stale_after)
    final_status = "stale" if stale and status not in {"blocked", "disabled"} else status
    final_reason = "observation_stale" if final_status == "stale" else reason
    return ObservedFact(
        status=cast(ObservationStatus, final_status),
        reason_code=final_reason,
        observed_at=_iso(observed_at),
        freshness_seconds=age,
        stale=stale,
    )


def _key_hash(scope: str, key: str) -> str:
    if not IDEMPOTENCY_RE.fullmatch(key):
        raise ApiException(400, "invalid_idempotency_key", "Idempotency-Key is invalid.")
    return hashlib.sha256(f"{scope}|{key}".encode()).hexdigest()


def _safe_message(code: str | None) -> str | None:
    return SAFE_MESSAGES.get(code or "")


def task_view(task: AssistantIndexTask) -> IndexTaskView:
    code = task.safe_error_code
    if task.status == "failed" and code is None:
        code = "index_task_failed"
    return IndexTaskView(
        id=task.id,
        source_type=cast(TaskSourceType, task.source_type),
        source_id=task.source_id,
        target_version=task.target_version,
        pipeline_version=task.pipeline_version,
        operation=cast(IndexTaskOperation, task.operation),
        status=cast(IndexTaskStatus, task.status),
        version=task.version,
        attempt_count=task.attempt_count,
        safe_error_code=code,
        message=_safe_message(code),
        parent_task_id=task.parent_task_id,
        operator_authorized=bool(task.operator_authorized),
        created_at=_iso(task.created_at) or "",
        updated_at=_iso(task.updated_at) or "",
    )


def operation_view(operation: AssistantIndexCommand) -> OperationView:
    return OperationView(
        operation_id=operation.id,
        kind=cast(OperationKind, operation.kind),
        status=cast(OperationStatus, operation.status),
        version=operation.version,
        generation_id=operation.generation_id,
        previous_generation_id=operation.previous_generation_id,
        source_cursor=operation.source_cursor,
        outbox_high_water=operation.outbox_high_water,
        safe_error_code=operation.safe_error_code,
        message=_safe_message(operation.safe_error_code),
        created_at=_iso(operation.created_at) or "",
        updated_at=_iso(operation.updated_at) or "",
        terminal_at=_iso(operation.terminal_at),
    )


def list_tasks(
    db: Session,
    *,
    limit: int,
    offset: int,
    status: str | None,
) -> IndexTaskList:
    query = select(AssistantIndexTask)
    if status is not None:
        query = query.where(AssistantIndexTask.status == status)
    rows = list(
        db.scalars(
            query.order_by(AssistantIndexTask.created_at.desc(), AssistantIndexTask.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return IndexTaskList(items=[task_view(row) for row in rows], limit=limit, offset=offset)


def retry_task(
    db: Session,
    *,
    task_id: int,
    expected_version: int,
    expected_status: str,
    operator_authorized: bool,
    idempotency_key: str,
) -> RetryTaskResponse:
    intent_key = _key_hash("retry", idempotency_key)
    existing = db.scalar(
        select(AssistantIndexTask).where(AssistantIndexTask.intent_key == intent_key)
    )
    if existing is not None:
        if existing.parent_task_id != task_id:
            raise ApiException(409, "idempotency_conflict", "Idempotency key was already used.")
        return RetryTaskResponse(task=task_view(existing), idempotent=True)
    original = db.get(AssistantIndexTask, task_id)
    if original is None:
        raise ApiException(404, "index_task_not_found", "Index task was not found.")
    if original.status != expected_status or original.version != expected_version:
        raise ApiException(409, "index_task_version_conflict", "Index task state is stale.")
    if original.status != "failed":
        raise ApiException(409, "index_task_not_failed", "Only failed tasks can be retried.")
    if original.provider_state in {"sending", "unknown"}:
        raise ApiException(
            409,
            "index_attempt_not_retryable",
            "A sending or unknown provider attempt cannot be retried.",
        )
    if original.provider_state == "succeeded" and not operator_authorized:
        raise ApiException(
            409,
            "operator_authorization_required",
            "Retry may duplicate a billed provider call and requires confirmation.",
        )
    document = project_source(db, original.source_type, original.source_id)
    if document is None:
        operation = "purge" if original.operation == "purge" else "delete"
        target_version = "0"
    else:
        operation = "upsert"
        target_version = document.source_version
    now = utc_now()
    created = AssistantIndexTask(
        source_type=original.source_type,
        source_id=original.source_id,
        target_version=target_version,
        pipeline_version=pipeline_version_from(db),
        operation=operation,
        status="pending",
        attempt_count=0,
        available_at=now,
        created_at=now,
        updated_at=now,
        version=1,
        intent_key=intent_key,
        parent_task_id=original.id,
        operator_authorized=1 if operator_authorized else 0,
        provider_state="prepared",
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return RetryTaskResponse(task=task_view(created), idempotent=False)


def request_rebuild(db: Session, *, idempotency_key: str) -> tuple[OperationView, bool]:
    key_hash = _key_hash("rebuild", idempotency_key)
    existing = db.scalar(
        select(AssistantIndexCommand).where(
            AssistantIndexCommand.idempotency_key_hash == key_hash
        )
    )
    if existing is not None:
        return operation_view(existing), True
    active = db.scalar(
        select(AssistantIndexCommand)
        .where(AssistantIndexCommand.status.in_(NONTERMINAL_OPERATIONS))
        .order_by(AssistantIndexCommand.created_at.desc())
    )
    if active is not None:
        raise ApiException(409, "rebuild_already_active", "A rebuild is already active.")
    now = utc_now()
    operation = AssistantIndexCommand(
        id=random_id(),
        kind="rebuild",
        idempotency_key_hash=key_hash,
        status="pending",
        version=1,
        manifest_json="{}",
        created_at=now,
        updated_at=now,
    )
    db.add(operation)
    db.commit()
    db.refresh(operation)
    return operation_view(operation), False


def get_operation(db: Session, operation_id: str) -> OperationView:
    operation = db.get(AssistantIndexCommand, operation_id)
    if operation is None:
        raise ApiException(404, "rebuild_not_found", "Rebuild operation was not found.")
    return operation_view(operation)


def update_availability(online, *, enabled: bool, expected_version: int) -> AvailabilityView:
    if online is None:
        raise ApiException(
            503, "assistant_runtime_unavailable", "Assistant runtime is unavailable."
        )
    if enabled:
        row = online.control.immediate(
            lambda conn: enable_gate(
                conn,
                online=online,
                expected_version=expected_version,
                now=online.now(),
            )
        )
    else:
        row = online.control.immediate(lambda conn: disable_gate(conn, now=online.now()))
    return _availability_view(online, row)


def _availability_view(online, row: dict[str, Any]) -> AvailabilityView:
    draining = 0
    if online is not None:
        draining = online.control.read(
            lambda conn: int(
                conn.execute(
                    "SELECT COUNT(*) FROM assistant_attempts WHERE status = 'sending'"
                ).fetchone()[0]
            )
        )
    public = gate_json(row)
    if online is not None and public["effective_state"] == STATE_ENABLED:
        # Reconcile drift using the normal fail-closed transition, including its
        # version/epoch. The operator can then explicitly enable the new binding.
        public = gate_json(online.control.immediate(lambda conn: validate_enabled_binding(
            conn, settings=online.settings, generation=online.active_generation(),
            now=online.now(),
        )))
    return AvailabilityView(
        requested_state=public["requested_state"],
        effective_state=public["effective_state"],
        version=int(public["version"]),
        operational_epoch=int(public["operational_epoch"]),
        blocked_reason=public.get("blocked_reason"),
        switch_pending_operation_id=public.get("switch_pending_operation_id"),
        switch_target_generation_id=public.get("switch_target_generation_id"),
        updated_at=public.get("updated_at"),
        draining_attempts=draining,
    )


def _budget_values(cap: Decimal | None, settled: int, reserved: int) -> tuple[int | None, int, int]:
    cap_micro = cny_to_micro(cap) if cap is not None else None
    remaining = max(0, cap_micro - settled - reserved) if cap_micro is not None else 0
    overage = max(0, settled + reserved - cap_micro) if cap_micro is not None else 0
    return cap_micro, remaining, overage


def _runtime_budget(conn, *, kind: str, day: str, cap: Decimal | None, observed_at: str):
    table = (
        "assistant_chat_budgets"
        if kind == "chat"
        else "assistant_query_embedding_budgets"
    )
    row = conn.execute(
        f"SELECT settled_micro, reserved_micro, circuit_open FROM {table} "
        "WHERE beijing_date = ?",
        (day,),
    ).fetchone()
    settled = int(row["settled_micro"]) if row else 0
    reserved = int(row["reserved_micro"]) if row else 0
    circuit = bool(row["circuit_open"]) if row else False
    events = conn.execute(
        """
        SELECT COUNT(*) AS calls, SUM(input_tokens) AS input_tokens,
               SUM(output_tokens) AS output_tokens,
               SUM(CASE WHEN input_tokens IS NULL THEN 1 ELSE 0 END) AS unknown_input,
               SUM(CASE WHEN kind = 'chat' AND output_tokens IS NULL THEN 1 ELSE 0 END)
                   AS unknown_output
        FROM assistant_metered_events WHERE beijing_date = ? AND kind = ?
        """,
        (day, kind),
    ).fetchone()
    calls = int(events["calls"] or 0)
    known = not int(events["unknown_input"] or 0) and not int(events["unknown_output"] or 0)
    cap_micro, remaining, overage = _budget_values(cap, settled, reserved)
    return BudgetView(
        kind=cast(BudgetKind, kind),
        beijing_date=day,
        cap_micro_cny=cap_micro,
        settled_micro_cny=settled,
        reserved_micro_cny=reserved,
        remaining_micro_cny=remaining if cap_micro is not None else None,
        overage_micro_cny=overage if cap_micro is not None else None,
        circuit_open=circuit,
        calls=calls,
        input_tokens=int(events["input_tokens"] or 0) if known else None,
        output_tokens=(int(events["output_tokens"] or 0) if known and kind == "chat" else None),
        usage_known=known,
        observed_at=observed_at,
        authority="runtime",
    )


def _unknown_runtime_budget(kind: str, day: str, cap: Decimal | None) -> BudgetView:
    return BudgetView(
        kind=cast(BudgetKind, kind),
        beijing_date=day,
        cap_micro_cny=cny_to_micro(cap) if cap is not None else None,
        settled_micro_cny=None,
        reserved_micro_cny=None,
        remaining_micro_cny=None,
        overage_micro_cny=None,
        circuit_open=None,
        calls=None,
        input_tokens=None,
        output_tokens=None,
        usage_known=False,
        observed_at=None,
        authority="runtime",
    )


def _index_budget(db: Session, *, day: str, settings, observed_at: str) -> BudgetView:
    row = db.get(AssistantIndexEmbeddingBudget, day)
    settled = row.settled_micro_cny if row else 0
    reserved = row.reserved_micro_cny if row else 0
    circuit = bool(row.circuit_open) if row else False
    attempts = db.execute(
        select(
            func.count(AssistantIndexEmbeddingAttempt.id),
            func.sum(AssistantIndexEmbeddingAttempt.input_tokens),
            func.sum(
                case(
                    (AssistantIndexEmbeddingAttempt.input_tokens.is_(None), 1),
                    else_=0,
                )
            ),
        ).where(
            AssistantIndexEmbeddingAttempt.beijing_date == day,
            AssistantIndexEmbeddingAttempt.status.in_(("sending", "succeeded", "unknown")),
        )
    ).one()
    calls = int(attempts[0] or 0)
    known = not int(attempts[2] or 0)
    cap = settings.assistant_index_embedding_daily_budget_cny
    cap_micro, remaining, overage = _budget_values(cap, settled, reserved)
    return BudgetView(
        kind="index_embedding",
        beijing_date=day,
        cap_micro_cny=cap_micro,
        settled_micro_cny=settled,
        reserved_micro_cny=reserved,
        remaining_micro_cny=remaining if cap_micro is not None else None,
        overage_micro_cny=overage if cap_micro is not None else None,
        circuit_open=circuit,
        calls=calls,
        input_tokens=int(attempts[1] or 0) if known else None,
        output_tokens=None,
        usage_known=known,
        observed_at=observed_at,
        authority="content",
    )


def build_snapshot(
    *, settings, online, db: Session, launcher_source: str
) -> AssistantAdminSnapshot:
    del launcher_source
    now = utc_now()
    observed_at = now.isoformat()
    day = beijing_date(now).isoformat()
    partial = online is None
    pointer = db.get(AssistantIndexPointer, 1)
    generation = (
        db.get(AssistantIndexGeneration, pointer.active_generation_id)
        if pointer is not None and pointer.active_generation_id is not None
        else None
    )
    queue_counts = {status: 0 for status in ("pending", "leased", "succeeded", "failed")}
    for status, count in db.execute(
        select(AssistantIndexTask.status, func.count(AssistantIndexTask.id)).group_by(
            AssistantIndexTask.status
        )
    ):
        if status in queue_counts:
            queue_counts[status] = int(count)
    from .sync_attention import covered_failed_task_ids

    failed_tasks = list(db.scalars(select(AssistantIndexTask).where(
        AssistantIndexTask.status == "failed",
    )))
    queue_counts["failed"] = len(failed_tasks) - len(covered_failed_task_ids(
        db, online.index_runtime if online is not None else None, failed_tasks,
    ))
    latest_success = db.scalar(
        select(AssistantIndexTask.updated_at)
        .where(AssistantIndexTask.status == "succeeded")
        .order_by(AssistantIndexTask.updated_at.desc())
        .limit(1)
    )
    operation = db.scalar(
        select(AssistantIndexCommand).order_by(
            AssistantIndexCommand.created_at.desc(), AssistantIndexCommand.id.desc()
        )
    )
    worker_row = db.get(AssistantIndexWorkerState, 1)
    if worker_row is None or worker_row.heartbeat_at is None:
        worker = _fact(
            status="unknown", reason="worker_observation_missing", observed_at=None, now=now
        )
    else:
        worker = _fact(
            status="healthy",
            reason="worker_owner_heartbeat",
            observed_at=worker_row.heartbeat_at,
            now=now,
            stale_after=max(5, int(settings.assistant_index_lease_seconds) * 2),
        )
    provider_facts = {
        item.kind: item
        for item in db.scalars(select(AssistantIndexProviderFact)).all()
    }
    qdrant_row = provider_facts.get("qdrant")
    qdrant = (
        _fact(status="unknown", reason="qdrant_observation_missing", observed_at=None, now=now)
        if qdrant_row is None
        else _fact(
            status=qdrant_row.status,
            reason=qdrant_row.reason_code,
            observed_at=qdrant_row.observed_at,
            now=now,
            stale_after=3600,
        )
    )
    runtime_observed_at: str | None = None
    chat_provider = _fact(
        status="unknown", reason="provider_observation_missing", observed_at=None, now=now
    )
    embedding_provider = _fact(
        status="unknown", reason="provider_observation_missing", observed_at=None, now=now
    )
    readiness = _fact(
        status="unknown", reason="runtime_unavailable", observed_at=None, now=now
    )
    cleanup = _fact(status="unknown", reason="runtime_unavailable", observed_at=None, now=now)
    restore = _fact(status="unknown", reason="runtime_unavailable", observed_at=None, now=now)
    gate = fail_closed_snapshot(
        "deployment_capability_disabled"
        if not settings.assistant_online_enabled
        else "runtime_unavailable"
    )
    runtime_budgets = [
        _unknown_runtime_budget("chat", day, settings.assistant_chat_daily_budget_cny),
        _unknown_runtime_budget(
            "query_embedding", day, settings.assistant_query_embedding_daily_budget_cny
        ),
    ]
    activity = DailyActivityView(
        accepted_questions=None,
        rate_limit_decisions=None,
        refusals=None,
        errors=None,
        security_events=None,
        latency_ms_min=None,
        latency_ms_max=None,
    )
    if online is not None:
        runtime_observed_at = online.now().isoformat()

        def read_runtime(conn):
            from .feedback import feedback_summary
            local_gate = gate_row(conn) or fail_closed_snapshot()
            receipt = current_receipt(conn)
            receipt_status = "unknown"
            receipt_reason = "readiness_missing"
            receipt_at = None
            if receipt is not None:
                receipt_at = receipt.get("created_at")
                try:
                    verify_receipt(settings, conn, generation=online.active_generation())
                    receipt_status = "healthy"
                    receipt_reason = "readiness_binding_valid"
                except Exception:
                    receipt_status = "blocked"
                    receipt_reason = "readiness_binding_invalid"
                    if local_gate.get("effective_state") == STATE_ENABLED:
                        local_gate = dict(local_gate)
                        local_gate["effective_state"] = "blocked"
                        local_gate["blocked_reason"] = "readiness_drift"
            provider_rows = conn.execute("SELECT * FROM assistant_provider_facts").fetchall()
            providers = {str(row["kind"]): row for row in provider_rows}
            cleanup_open = breaker_open(conn)
            restore_until = online_lock_until(conn)
            activities = conn.execute(
                """
                SELECT kind, COUNT(*) AS n, MIN(latency_ms) AS min_latency,
                       MAX(latency_ms) AS max_latency
                FROM assistant_activity_events WHERE beijing_date = ? GROUP BY kind
                """,
                (day,),
            ).fetchall()
            counts = {str(row["kind"]): int(row["n"]) for row in activities}
            latency_values = [
                value
                for row in activities
                for value in (row["min_latency"], row["max_latency"])
                if value is not None and row["kind"] in {"answer", "refusal", "error"}
            ]
            return {
                "gate": local_gate,
                "readiness": (receipt_status, receipt_reason, receipt_at),
                "providers": providers,
                "cleanup": cleanup_open,
                "restore_until": restore_until,
                "budgets": [
                    _runtime_budget(
                        conn,
                        kind="chat",
                        day=day,
                        cap=settings.assistant_chat_daily_budget_cny,
                        observed_at=runtime_observed_at or observed_at,
                    ),
                    _runtime_budget(
                        conn,
                        kind="query_embedding",
                        day=day,
                        cap=settings.assistant_query_embedding_daily_budget_cny,
                        observed_at=runtime_observed_at or observed_at,
                    ),
                ],
                "counts": counts,
                "latencies": latency_values,
                "feedback": feedback_summary(conn, online.now()),
                "stages": [{"stage": row["kind"].removeprefix("stage_"), "count": row["n"],
                            "latency_ms_min": row["min_latency"],
                            "latency_ms_max": row["max_latency"]}
                           for row in activities if row["kind"].startswith("stage_")],
            }

        runtime = online.control.read(read_runtime)
        gate = runtime["gate"]
        readiness = _fact(
            status=runtime["readiness"][0],
            reason=runtime["readiness"][1],
            observed_at=runtime["readiness"][2],
            now=now,
        )
        cleanup = _fact(
            status="blocked" if runtime["cleanup"] else "healthy",
            reason="cleanup_breaker_open" if runtime["cleanup"] else "cleanup_breaker_closed",
            observed_at=runtime_observed_at,
            now=now,
        )
        restore_active = runtime["restore_until"] is not None and now < runtime["restore_until"]
        restore = _fact(
            status="blocked" if restore_active else "healthy",
            reason="restore_lock_active" if restore_active else "restore_lock_clear",
            observed_at=runtime_observed_at,
            now=now,
        )
        for kind, target in (("chat", "chat"), ("query_embedding", "embedding")):
            row = runtime["providers"].get(kind)
            fact = (
                _fact(
                    status="unknown",
                    reason="provider_observation_missing",
                    observed_at=None,
                    now=now,
                )
                if row is None
                else _fact(
                    status=str(row["status"]),
                    reason=str(row["reason_code"]),
                    observed_at=row["observed_at"],
                    now=now,
                    stale_after=3600,
                )
            )
            if target == "chat":
                chat_provider = fact
            else:
                embedding_provider = fact
        runtime_budgets = runtime["budgets"]
        counts = runtime["counts"]
        latencies = runtime["latencies"]
        activity = DailyActivityView(
            accepted_questions=counts.get("accepted_question", 0),
            rate_limit_decisions=counts.get("rate_limit_decision", 0),
            refusals=counts.get("refusal", 0),
            errors=counts.get("error", 0),
            security_events=counts.get("security", 0),
            latency_ms_min=min(latencies) if latencies else None,
            latency_ms_max=max(latencies) if latencies else None,
            feedback_helpful=runtime["feedback"]["helpful"],
            feedback_unhelpful=runtime["feedback"]["unhelpful"],
            stages=runtime["stages"],
        )
    availability = _availability_view(online, gate)
    manifest = ManifestView(
        generation_id=generation.id if generation else None,
        provider=generation.embedding_provider if generation else None,
        model=generation.embedding_model if generation else None,
        model_version=generation.embedding_model_version if generation else None,
        dimension=generation.vector_dimension if generation else None,
        pipeline_version=generation.pipeline_version if generation else None,
        collection_present=None,
    )
    index_budget = _index_budget(db, day=day, settings=settings, observed_at=observed_at)
    return AssistantAdminSnapshot(
        status="partial" if partial else "complete",
        observed_at=observed_at,
        runtime_observed_at=runtime_observed_at,
        content_observed_at=observed_at,
        deployment=DeploymentView(
            api_capability=bool(settings.assistant_online_enabled),
            single_api_owner=bool(settings.assistant_single_process_confirmed),
            launcher_source="web_runtime_config",
            launcher_mounted=None,
        ),
        availability=availability,
        readiness=readiness,
        cleanup=cleanup,
        restore=restore,
        qdrant=qdrant,
        chat_provider=chat_provider,
        embedding_provider=embedding_provider,
        worker=worker,
        manifest=manifest,
        queue=QueueView(
            pending=queue_counts["pending"],
            leased=queue_counts["leased"],
            succeeded=queue_counts["succeeded"],
            failed=queue_counts["failed"],
            latest_success_at=_iso(latest_success),
        ),
        operation=operation_view(operation) if operation else None,
        budgets=[*runtime_budgets, index_budget],
        daily_activity=activity,
    )


def _runtime_switch_pending(online, *, operation_id: str, target_id: int, token: str) -> None:
    def write(conn):
        from .admin_scope import stop_admin
        stop_admin(conn)
        row = gate_row(conn)
        if row is None:
            raise ApiException(503, "assistant_gate_unavailable", "Assistant gate is unavailable.")
        existing = row.get("switch_pending_operation_id")
        if existing is not None:
            if existing != operation_id or row.get("switch_target_generation_id") != target_id:
                raise ApiException(409, "generation_switch_pending", "Another switch is pending.")
            if row.get("switch_finalize_token") != token:
                raise ApiException(409, "finalize_token_conflict", "Finalize token is stale.")
            return
        conn.execute(
            """
            UPDATE assistant_operational_gate
            SET requested_state = 'disabled', effective_state = 'disabled',
                version = version + 1, operational_epoch = operational_epoch + 1,
                readiness_receipt_id = NULL, config_fingerprint = NULL,
                active_generation_id = NULL, blocked_reason = NULL,
                switch_pending_operation_id = ?, switch_target_generation_id = ?,
                switch_finalize_token = ?, updated_at = ?
            WHERE id = 1 AND switch_pending_operation_id IS NULL
            """,
            (operation_id, target_id, token, online.now()),
        )

    online.control.immediate(write)


def _clear_runtime_switch(online, *, operation_id: str, target_id: int, token: str) -> None:
    def clear(conn):
        row = gate_row(conn)
        if row is None:
            raise ApiException(503, "assistant_gate_unavailable", "Assistant gate is unavailable.")
        if row.get("switch_pending_operation_id") is None:
            return
        if (
            row.get("switch_pending_operation_id") != operation_id
            or row.get("switch_target_generation_id") != target_id
            or row.get("switch_finalize_token") != token
        ):
            raise ApiException(409, "finalize_token_conflict", "Finalize token is stale.")
        conn.execute(
            """
            UPDATE assistant_operational_gate
            SET requested_state = 'disabled', effective_state = 'disabled',
                version = version + 1,
                switch_pending_operation_id = NULL, switch_target_generation_id = NULL,
                switch_finalize_token = NULL, updated_at = ?
            WHERE id = 1
            """,
            (online.now(),),
        )

    online.control.immediate(clear)


def _switch_content(
    database,
    *,
    settings,
    index_runtime,
    operation_id: str,
    expected_version: int,
    idempotency_hash: str,
    token: str,
) -> OperationView:
    with database.session_factory() as db:
        db.info["settings"] = settings
        db.execute(text("BEGIN IMMEDIATE"))
        operation = db.get(AssistantIndexCommand, operation_id)
        if operation is None:
            db.rollback()
            raise ApiException(404, "rebuild_not_found", "Rebuild operation was not found.")
        if operation.status == "switched":
            if operation.finalize_idempotency_hash != idempotency_hash:
                db.rollback()
                raise ApiException(409, "idempotency_conflict", "Finalize key was already used.")
            result = operation_view(operation)
            db.commit()
            return result
        if operation.version != expected_version or operation.status != "ready_to_switch":
            db.rollback()
            raise ApiException(409, "rebuild_version_conflict", "Rebuild state is stale.")
        if operation.generation_id is None:
            db.rollback()
            raise ApiException(409, "rebuild_not_ready", "Rebuild generation is missing.")
        pointer = db.get(AssistantIndexPointer, 1)
        generation = db.get(AssistantIndexGeneration, operation.generation_id)
        if pointer is None or generation is None or generation.status != "staging":
            db.rollback()
            raise ApiException(409, "rebuild_not_ready", "Rebuild generation is not ready.")
        current_documents = iter_public_sources(db)
        current_digest = source_revision_set_digest(current_documents)
        pending_query = select(func.count()).select_from(AssistantIndexTask).where(
            AssistantIndexTask.status.in_(("pending", "leased"))
        )
        if operation.previous_generation_id is None:
            pending_query = pending_query.where(
                AssistantIndexTask.id > int(operation.outbox_high_water or 0)
            )
        pending = int(db.scalar(pending_query) or 0)
        valid = (
            pointer.active_generation_id == operation.previous_generation_id
            and operation.source_revision_set_digest == current_digest
            and generation.source_revision_set_digest == current_digest
            and operation.outbox_high_water == generation.outbox_high_water
            and generation.built_at is not None
            and generation.chunk_count is not None
            and generation.vector_count is not None
            and pending == 0
        )
        if not valid:
            operation.status = "catch_up"
            operation.safe_error_code = "source_changed"
            operation.version += 1
            operation.updated_at = utc_now()
            db.commit()
            raise ApiException(409, "rebuild_requires_catch_up", "Rebuild requires catch-up.")
        from ..assistant_index.integrity import IndexIntegrityError, audit_generation

        try:
            audit_generation(db, index_runtime, generation).require_passed()
        except IndexIntegrityError as exc:
            raise ApiException(
                409, "index_integrity_failed", "Index integrity check failed."
            ) from exc
        old_active_id = pointer.active_generation_id
        if old_active_id is not None and old_active_id != generation.id:
            old = db.get(AssistantIndexGeneration, old_active_id)
            if old is not None:
                old.status = "previous"
                old.updated_at = utc_now()
        if operation.previous_generation_id is None:
            initial_tasks = db.scalars(
                select(AssistantIndexTask).where(
                    AssistantIndexTask.id <= int(operation.outbox_high_water or 0),
                    AssistantIndexTask.status.in_(("pending", "leased", "failed")),
                )
            ).all()
            for task in initial_tasks:
                task.status = "succeeded"
                task.lease_owner = None
                task.lease_expires_at = None
                task.lease_token = None
                task.worker_fence = None
                task.provider_state = "succeeded"
                task.safe_error_code = None
                task.last_error_summary = None
                task.version += 1
                task.updated_at = utc_now()
        generation.status = "active"
        generation.updated_at = utc_now()
        pointer.previous_generation_id = old_active_id
        pointer.active_generation_id = generation.id
        pointer.updated_at = utc_now()
        operation.status = "switched"
        operation.version += 1
        operation.finalize_token = token
        operation.finalize_idempotency_hash = idempotency_hash
        operation.safe_error_code = None
        operation.updated_at = utc_now()
        operation.terminal_at = utc_now()
        db.commit()
        return operation_view(operation)


def finalize_rebuild(
    online,
    *,
    operation_id: str,
    expected_version: int,
    idempotency_key: str,
) -> OperationView:
    if online is None:
        raise ApiException(
            503, "assistant_runtime_unavailable", "Assistant runtime is unavailable."
        )
    key_hash = _key_hash(f"finalize:{operation_id}", idempotency_key)
    with online.database.session_factory() as db:
        operation = db.get(AssistantIndexCommand, operation_id)
        if operation is None:
            raise ApiException(404, "rebuild_not_found", "Rebuild operation was not found.")
        if operation.status == "switched":
            if operation.finalize_idempotency_hash != key_hash:
                raise ApiException(409, "idempotency_conflict", "Finalize key was already used.")
            if operation.generation_id is None or operation.finalize_token is None:
                raise ApiException(
                    503,
                    "switch_reconciliation_failed",
                    "Switch facts are incomplete.",
                )
            _clear_runtime_switch(
                online,
                operation_id=operation.id,
                target_id=operation.generation_id,
                token=operation.finalize_token,
            )
            return operation_view(operation)
        if operation.status != "ready_to_switch" or operation.version != expected_version:
            raise ApiException(409, "rebuild_version_conflict", "Rebuild state is stale.")
        if operation.generation_id is None:
            raise ApiException(409, "rebuild_not_ready", "Rebuild generation is missing.")
        gate = online.control.read(lambda conn: gate_row(conn) or fail_closed_snapshot())
        if gate.get("switch_pending_operation_id") == operation.id:
            token = str(gate.get("switch_finalize_token") or "")
            if not token:
                raise ApiException(503, "switch_reconciliation_failed", "Switch token is missing.")
        else:
            token = random_id()
        target_id = operation.generation_id
    _runtime_switch_pending(
        online,
        operation_id=operation_id,
        target_id=target_id,
        token=token,
    )
    result = _switch_content(
        online.database,
        settings=online.settings,
        index_runtime=online.index_runtime,
        operation_id=operation_id,
        expected_version=expected_version,
        idempotency_hash=key_hash,
        token=token,
    )
    _clear_runtime_switch(
        online,
        operation_id=operation_id,
        target_id=target_id,
        token=token,
    )
    return result


def recover_switch_pending(online) -> None:
    gate = online.control.read(lambda conn: gate_row(conn) or fail_closed_snapshot())
    operation_id = gate.get("switch_pending_operation_id")
    target_id = gate.get("switch_target_generation_id")
    token = gate.get("switch_finalize_token")
    if not operation_id or target_id is None or not token:
        return
    with online.database.session_factory() as db:
        operation = db.get(AssistantIndexCommand, operation_id)
        pointer = db.get(AssistantIndexPointer, 1)
        switched = bool(
            operation
            and pointer
            and operation.status == "switched"
            and operation.generation_id == target_id
            and pointer.active_generation_id == target_id
            and operation.finalize_token == token
        )
        terminal_without_switch = bool(
            operation
            and pointer
            and operation.status in {"failed", "abandoned"}
            and pointer.active_generation_id == operation.previous_generation_id
        )
    if switched or terminal_without_switch:
        _clear_runtime_switch(
            online,
            operation_id=operation_id,
            target_id=int(target_id),
            token=str(token),
        )
