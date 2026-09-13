from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from typing import Any

from ..http_errors import ApiException
from .errors import AssistantNotReadyError, not_ready
from .readiness import verify_receipt
from .recovery import online_lock_until
from .store import breaker_open, current_receipt, row_dict

GATE_ID = 1
STATE_DISABLED = "disabled"
STATE_ENABLED = "enabled"
STATE_BLOCKED = "blocked"


def gate_row(conn) -> dict[str, Any] | None:
    try:
        row = conn.execute(
            "SELECT * FROM assistant_operational_gate WHERE id = ?", (GATE_ID,)
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    value = row_dict(row)
    if value is None:
        return None
    if value.get("requested_state") not in {STATE_DISABLED, STATE_ENABLED}:
        return None
    if value.get("effective_state") not in {STATE_DISABLED, STATE_ENABLED, STATE_BLOCKED}:
        return None
    if int(value.get("version") or 0) < 1 or int(value.get("operational_epoch") or 0) < 1:
        return None
    return value


def fail_closed_snapshot(reason: str = "runtime_gate_missing") -> dict[str, Any]:
    return {
        "requested_state": STATE_DISABLED,
        "effective_state": STATE_BLOCKED,
        "version": 0,
        "operational_epoch": 0,
        "readiness_receipt_id": None,
        "config_fingerprint": None,
        "active_generation_id": None,
        "switch_pending_operation_id": None,
        "switch_target_generation_id": None,
        "blocked_reason": reason,
        "updated_at": None,
    }


def _receipt_fingerprint(receipt: dict[str, Any]) -> str:
    return hashlib.sha256(str(receipt["receipt_json"]).encode("utf-8")).hexdigest()


def _generation_id(generation) -> int | None:
    value = None if generation is None else getattr(generation, "id", None)
    return int(value) if value is not None else None


def _block(conn, row: dict[str, Any], *, now: datetime, reason: str) -> None:
    from .admin_scope import stop_admin
    stop_admin(conn)
    conn.execute(
        """
        UPDATE assistant_operational_gate
        SET requested_state = 'disabled', effective_state = 'blocked',
            version = version + 1, operational_epoch = operational_epoch + 1,
            readiness_receipt_id = NULL, config_fingerprint = NULL,
            active_generation_id = NULL, blocked_reason = ?, updated_at = ?
        WHERE id = ? AND version = ?
        """,
        (reason, now, GATE_ID, int(row["version"])),
    )


def validate_enabled_binding(
    conn,
    *,
    settings,
    generation,
    now: datetime,
    block_on_drift: bool = True,
    admin: bool = False,
) -> dict[str, Any]:
    if admin:
        from .admin_scope import validate_admin_binding
        return validate_admin_binding(conn, settings=settings, generation=generation, now=now)
    row = gate_row(conn)
    if row is None:
        raise not_ready()
    if row["effective_state"] != STATE_ENABLED or row["requested_state"] != STATE_ENABLED:
        raise not_ready()
    reason: str | None = None
    if row.get("switch_pending_operation_id"):
        reason = "switch_pending"
    elif breaker_open(conn):
        reason = "cleanup_breaker_open"
    else:
        until = online_lock_until(conn)
        if until is not None and now < until:
            reason = "restore_lock_active"
    receipt = current_receipt(conn)
    if reason is None and receipt is None:
        reason = "readiness_missing"
    if reason is None:
        try:
            verify_receipt(settings, conn, generation=generation)
        except (AssistantNotReadyError, ValueError):
            reason = "readiness_drift"
    if reason is None and receipt is not None:
        if row.get("readiness_receipt_id") != receipt.get("id"):
            reason = "readiness_drift"
        elif row.get("config_fingerprint") != _receipt_fingerprint(receipt):
            reason = "config_drift"
        elif row.get("active_generation_id") != _generation_id(generation):
            reason = "generation_drift"
    if reason is not None:
        if block_on_drift:
            _block(conn, row, now=now, reason=reason)
            blocked = fail_closed_snapshot(reason)
            blocked["version"] = int(row["version"]) + 1
            blocked["operational_epoch"] = int(row["operational_epoch"]) + 1
            blocked["_blocked"] = True
            return blocked
        raise not_ready()
    return row


def enable_gate(conn, *, online, expected_version: int, now: datetime) -> dict[str, Any]:
    row = gate_row(conn)
    if row is None:
        raise ApiException(503, "assistant_gate_unavailable", "Assistant gate is unavailable.")
    if int(row["version"]) != int(expected_version):
        raise ApiException(409, "availability_version_conflict", "Availability version is stale.")
    if row.get("switch_pending_operation_id"):
        raise ApiException(409, "generation_switch_pending", "Generation switch is pending.")
    if row["effective_state"] == STATE_ENABLED:
        raise ApiException(409, "assistant_already_enabled", "Assistant is already enabled.")
    if (
        not online.settings.assistant_online_enabled
        or not online.settings.assistant_single_process_confirmed
    ):
        raise ApiException(
            503,
            "assistant_capability_unavailable",
            "Assistant capability is unavailable.",
        )
    if breaker_open(conn):
        raise ApiException(503, "cleanup_breaker_open", "Cleanup breaker is open.")
    until = online_lock_until(conn)
    if until is not None and now < until:
        raise ApiException(503, "restore_lock_active", "Runtime restore lock is active.")
    receipt = current_receipt(conn)
    if receipt is None:
        raise ApiException(503, "readiness_missing", "Readiness receipt is missing.")
    generation = online.active_generation()
    try:
        verify_receipt(online.settings, conn, generation=generation)
    except Exception as exc:
        raise ApiException(503, "readiness_invalid", "Readiness binding is invalid.") from exc
    cur = conn.execute(
        """
        UPDATE assistant_operational_gate
        SET requested_state = 'enabled', effective_state = 'enabled',
            version = version + 1, operational_epoch = operational_epoch + 1,
            readiness_receipt_id = ?, config_fingerprint = ?, active_generation_id = ?,
            blocked_reason = NULL, updated_at = ?
        WHERE id = ? AND version = ? AND switch_pending_operation_id IS NULL
        """,
        (
            receipt["id"],
            _receipt_fingerprint(receipt),
            _generation_id(generation),
            now,
            GATE_ID,
            expected_version,
        ),
    )
    if cur.rowcount != 1:
        raise ApiException(409, "availability_version_conflict", "Availability version is stale.")
    return gate_row(conn) or fail_closed_snapshot()


def disable_gate(conn, *, now: datetime) -> dict[str, Any]:
    row = gate_row(conn)
    if row is None:
        raise ApiException(503, "assistant_gate_unavailable", "Assistant gate is unavailable.")
    if row["requested_state"] == STATE_DISABLED and row["effective_state"] != STATE_ENABLED:
        return row
    conn.execute(
        """
        UPDATE assistant_operational_gate
        SET requested_state = 'disabled', effective_state = 'disabled',
            version = version + 1, operational_epoch = operational_epoch + 1,
            readiness_receipt_id = NULL, config_fingerprint = NULL,
            active_generation_id = NULL, blocked_reason = NULL, updated_at = ?
        WHERE id = ?
        """,
        (now, GATE_ID),
    )
    return gate_row(conn) or fail_closed_snapshot()


def gate_for_turn_admission(conn, *, online, now: datetime, admin: bool = False) -> dict[str, Any]:
    return validate_enabled_binding(
        conn,
        settings=online.settings,
        generation=online.active_generation(),
        now=now,
        admin=admin,
    )


def gate_json(row: dict[str, Any]) -> dict[str, Any]:
    value = dict(row)
    value.pop("switch_finalize_token", None)
    for key in ("updated_at",):
        if isinstance(value.get(key), datetime):
            value[key] = value[key].isoformat()
    return json.loads(json.dumps(value, default=str))
