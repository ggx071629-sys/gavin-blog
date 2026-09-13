"""Administrator execution scope, independent of the public opt-in gate.

Only authenticated routes set request.state.assistant_admin_scope. Session ids
are server generated; the prefix also fences Saver and publication mutations.
"""

from __future__ import annotations

from .errors import not_ready

ADMIN_PREFIX = "admin_"


def is_admin_session(session_id: str) -> bool:
    return session_id.startswith(ADMIN_PREFIX)


def admin_epoch(conn) -> int:
    row = conn.execute(
        "SELECT value FROM assistant_runtime_meta WHERE key = 'admin_execution_epoch'"
    ).fetchone()
    return int(row[0]) if row else 1


def admin_stopped(conn) -> bool:
    row = conn.execute(
        "SELECT value FROM assistant_runtime_meta WHERE key = 'admin_execution_stopped'"
    ).fetchone()
    return bool(row and row[0] == "1")


def stop_admin(conn) -> None:
    epoch = admin_epoch(conn) + 1
    for key, value in (("admin_execution_epoch", str(epoch)), ("admin_execution_stopped", "1")):
        conn.execute(
            "INSERT INTO assistant_runtime_meta(key,value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def validate_admin_recovery_conditions(conn, *, settings, now):
    from .operational import gate_row
    from .recovery import online_lock_until
    from .store import breaker_open

    gate = gate_row(conn)
    until = online_lock_until(conn)
    if (
        not settings.assistant_online_enabled
        or not settings.assistant_single_process_confirmed
        or gate is None
        or gate.get("switch_pending_operation_id")
        or breaker_open(conn)
        or (until is not None and now < until)
    ):
        raise not_ready()
    return gate


def validate_admin_binding(conn, *, settings, generation, now, resume: bool = False):
    from .errors import AssistantNotReadyError
    from .readiness import verify_receipt

    gate = validate_admin_recovery_conditions(conn, settings=settings, now=now)
    if admin_stopped(conn) and not resume:
        raise not_ready()
    try:
        verify_receipt(settings, conn, generation=generation)
    except (AssistantNotReadyError, ValueError) as exc:
        raise not_ready() from exc
    if resume:
        conn.execute(
            "INSERT INTO assistant_runtime_meta(key,value) VALUES ('admin_execution_stopped','0') "
            "ON CONFLICT(key) DO UPDATE SET value='0'"
        )
    return {**gate, "operational_epoch": admin_epoch(conn)}


def scope_permitted(conn, gate, session_id: str, epoch: int) -> bool:
    if gate is None or gate["switch_pending_operation_id"] is not None:
        return False
    if is_admin_session(session_id):
        return not admin_stopped(conn) and admin_epoch(conn) == epoch
    return gate["effective_state"] == "enabled" and int(gate["operational_epoch"]) == epoch


def request_scope(request) -> str:
    return getattr(request.state, "assistant_admin_scope", "")


def cookie_name(request, *, csrf: bool = False) -> str:
    scope = "trial" if request_scope(request) else "assistant"
    return f"gavin_{scope}_{'csrf' if csrf else 'session'}"


def session_context(request) -> str:
    scope = request_scope(request)
    return f"admin-trial:{scope}" if scope else "assistant-session"
