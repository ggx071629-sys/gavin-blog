from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from ..time_utils import as_utc
from .constants import (
    ATTEMPT_FAILED,
    ATTEMPT_PREPARED,
    ATTEMPT_SENDING,
    ATTEMPT_SUCCEEDED,
    ATTEMPT_UNKNOWN,
    BODY_RETENTION_SECONDS,
    IDEMPOTENCY_TOMBSTONE_HOURS,
    KIND_CHAT,
    KIND_QUERY_EMBEDDING,
    LEASE_GLOBAL,
    LEASE_IP,
    LEASE_SESSION,
    MAX_EVENTS_PER_TURN,
    MAX_HISTORY_TURNS,
    SESSION_BYTE_LIMIT,
    STAGE_EVENTS,
)
from .crypto import compare, random_id
from .errors import AssistantNotReadyError
from .identity import ExecutionIdentity, identity_from_turn, normal_mutation_permit
from .time_beijing import beijing_date


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def breaker_open(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT breaker_open FROM assistant_cleanup_state WHERE id = 1").fetchone()
    return bool(row and row["breaker_open"])


def open_cleanup_breaker(conn: sqlite3.Connection, now: datetime, error: str) -> None:
    conn.execute(
        "UPDATE assistant_cleanup_state "
        "SET breaker_open = 1, last_sweep_at = ?, last_error = ? WHERE id = 1",
        (now, error[:240]),
    )


def record_cleanup_retry(
    conn: sqlite3.Connection,
    *,
    kind: str,
    target_id: str,
    now: datetime,
    error: str,
) -> None:
    conn.execute(
        """
        INSERT INTO assistant_cleanup_retries
            (kind, target_id, attempts, last_error, last_attempt_at)
        VALUES (?, ?, 1, ?, ?)
        ON CONFLICT(kind, target_id) DO UPDATE SET
            attempts = attempts + 1,
            last_error = excluded.last_error,
            last_attempt_at = excluded.last_attempt_at
        """,
        (kind, target_id, error[:240], now),
    )
    open_cleanup_breaker(conn, now, f"{kind}: {error}")


def clear_cleanup_retry(conn: sqlite3.Connection, *, kind: str, target_id: str) -> None:
    conn.execute(
        "DELETE FROM assistant_cleanup_retries WHERE kind = ? AND target_id = ?",
        (kind, target_id),
    )


def session_is_live(conn: sqlite3.Connection, session_id: str, now: datetime) -> bool:
    session = get_session(conn, session_id)
    if session is None or session["tombstoned_at"] is not None:
        return False
    idle = session["idle_expires_at"]
    absolute = session["absolute_expires_at"]
    if isinstance(idle, str):
        idle = datetime.fromisoformat(idle)
    if isinstance(absolute, str):
        absolute = datetime.fromisoformat(absolute)
    return idle > now and absolute > now


def turn_session_live(conn: sqlite3.Connection, turn_id: str, now: datetime) -> bool:
    turn = get_turn(conn, turn_id)
    if turn is None:
        return False
    return session_is_live(conn, turn["session_id"], now)


def session_by_hmac(conn: sqlite3.Connection, session_hmac: str) -> dict[str, Any] | None:
    return row_dict(
        conn.execute(
            "SELECT * FROM assistant_sessions WHERE session_hmac = ?",
            (session_hmac,),
        ).fetchone()
    )


def get_session(conn: sqlite3.Connection, session_id: str) -> dict[str, Any] | None:
    return row_dict(
        conn.execute("SELECT * FROM assistant_sessions WHERE id = ?", (session_id,)).fetchone()
    )


def insert_session(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    session_hmac: str,
    csrf_hmac: str,
    now: datetime,
    idle_seconds: int,
    absolute_seconds: int,
) -> None:
    conn.execute(
        """
        INSERT INTO assistant_sessions (
            id, session_hmac, csrf_hmac, created_at, last_activity_at,
            idle_expires_at, absolute_expires_at, fencing_epoch, persisted_bytes, cleanup_breaker
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0)
        """,
        (
            session_id,
            session_hmac,
            csrf_hmac,
            now,
            now,
            now + timedelta(seconds=idle_seconds),
            now + timedelta(seconds=absolute_seconds),
        ),
    )


def touch_session(
    conn: sqlite3.Connection, session_id: str, now: datetime, idle_seconds: int
) -> None:
    conn.execute(
        """
        UPDATE assistant_sessions
        SET last_activity_at = ?, idle_expires_at = ?
        WHERE id = ? AND tombstoned_at IS NULL
        """,
        (now, now + timedelta(seconds=idle_seconds), session_id),
    )


def tombstone_session(conn: sqlite3.Connection, session_id: str, now: datetime) -> int:
    conn.execute(
        "DELETE FROM assistant_activity_events WHERE kind='feedback' AND event_id IN "
        "(SELECT id || ':feedback' FROM assistant_turns WHERE session_id=?)", (session_id,),
    )
    conn.execute(
        """
        UPDATE assistant_sessions
        SET tombstoned_at = ?, fencing_epoch = fencing_epoch + 1
        WHERE id = ? AND tombstoned_at IS NULL
        """,
        (now, session_id),
    )
    return conn.execute(
        "SELECT fencing_epoch FROM assistant_sessions WHERE id = ?", (session_id,)
    ).fetchone()["fencing_epoch"]


def set_execution_identity(
    conn: sqlite3.Connection,
    *,
    turn_id: str,
    fencing_epoch: int,
    fencing_token: str,
    ip_hmac: str,
    operational_epoch: int,
) -> None:
    conn.execute(
        """
        UPDATE assistant_turns
        SET execution_epoch = ?, execution_token = ?, ip_hmac = ?, operational_epoch = ?
        WHERE id = ?
        """,
        (fencing_epoch, fencing_token, ip_hmac, operational_epoch, turn_id),
    )


def insert_rate_event(
    conn: sqlite3.Connection,
    *,
    ip_hmac: str,
    kind: str,
    now: datetime,
) -> None:
    conn.execute(
        "INSERT INTO assistant_rate_events "
        "(ip_hmac, kind, created_at, beijing_date) VALUES (?, ?, ?, ?)",
        (ip_hmac, kind, now, beijing_date(now).isoformat()),
    )


def record_activity_event(
    conn: sqlite3.Connection,
    *,
    event_id: str,
    kind: str,
    outcome: str,
    now: datetime,
    latency_ms: int | None = None,
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO assistant_activity_events
            (event_id, beijing_date, kind, outcome, latency_ms, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (event_id, beijing_date(now).isoformat(), kind, outcome, latency_ms, now),
    )


def count_rate_events(
    conn: sqlite3.Connection,
    *,
    ip_hmacs: list[str],
    kind: str,
    since: datetime,
) -> int:
    if not ip_hmacs:
        return 0
    placeholders = ",".join("?" for _ in ip_hmacs)
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS n FROM assistant_rate_events
        WHERE kind = ? AND created_at >= ? AND ip_hmac IN ({placeholders})
        """,
        (kind, since, *ip_hmacs),
    ).fetchone()
    return int(row["n"] if row else 0)


def earliest_rate_release(
    conn: sqlite3.Connection,
    *,
    ip_hmacs: list[str],
    kind: str,
    since: datetime,
    window_seconds: int,
    now: datetime,
) -> int:
    placeholders = ",".join("?" for _ in ip_hmacs)
    row = conn.execute(
        f"""
        SELECT created_at FROM assistant_rate_events
        WHERE kind = ? AND created_at >= ? AND ip_hmac IN ({placeholders})
        ORDER BY created_at ASC LIMIT 1
        """,
        (kind, since, *ip_hmacs),
    ).fetchone()
    if row is None:
        return 0
    created = row["created_at"]
    if isinstance(created, str):
        created = datetime.fromisoformat(created)
    release = created + timedelta(seconds=window_seconds)
    return max(0, int((release - now).total_seconds() + 0.999))


def find_turn_by_idempotency(
    conn: sqlite3.Connection,
    session_id: str,
    idempotency_hmac: str,
) -> dict[str, Any] | None:
    return row_dict(
        conn.execute(
            "SELECT * FROM assistant_turns WHERE session_id = ? AND idempotency_hmac = ?",
            (session_id, idempotency_hmac),
        ).fetchone()
    )


def insert_turn(
    conn: sqlite3.Connection,
    *,
    turn_id: str,
    session_id: str,
    idempotency_hmac: str,
    payload_hmac: str,
    question: str | None,
    current_path: str | None,
    thread_id: str | None,
    now: datetime,
    preflight_blocked: bool,
) -> None:
    conn.execute(
        """
        INSERT INTO assistant_turns (
            id, session_id, idempotency_hmac, payload_hmac, thread_id, status,
            question, current_path, created_at, preflight_blocked
        ) VALUES (?, ?, ?, ?, ?, 'accepted', ?, ?, ?, ?)
        """,
        (
            turn_id,
            session_id,
            idempotency_hmac,
            payload_hmac,
            thread_id,
            question,
            current_path,
            now,
            1 if preflight_blocked else 0,
        ),
    )


def get_turn(conn: sqlite3.Connection, turn_id: str) -> dict[str, Any] | None:
    return row_dict(
        conn.execute("SELECT * FROM assistant_turns WHERE id = ?", (turn_id,)).fetchone()
    )


def list_completed_turns(
    conn: sqlite3.Connection, session_id: str, limit: int = 20
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, created_at, terminal_at, terminal_event, terminal_code, terminal_message, answer,
               question, citations_json, sources_json, body_purged_at, preflight_blocked
        FROM assistant_turns
        WHERE session_id = ? AND status = 'terminal' AND preflight_blocked = 0
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()
    items = [row_dict(row) or {} for row in rows]
    items.reverse()
    return items


def list_active_turns(conn: sqlite3.Connection, session_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, question, created_at, status
        FROM assistant_turns
        WHERE session_id = ? AND status IN ('accepted', 'running') AND preflight_blocked = 0
        ORDER BY created_at ASC
        """,
        (session_id,),
    ).fetchall()
    return [row_dict(row) or {} for row in rows]


def latest_stage(conn: sqlite3.Connection, turn_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT event_name FROM assistant_event_journal
        WHERE turn_id = ? AND event_name IN (?, ?, ?, ?)
        ORDER BY seq DESC LIMIT 1
        """,
        (turn_id, *STAGE_EVENTS),
    ).fetchone()
    return str(row["event_name"]) if row else None


def load_json_list(raw: str | None) -> list[dict[str, Any]] | None:
    if raw is None:
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, list):
        return None
    return value


def public_completed_turn_at(row: dict[str, Any], now: datetime) -> dict[str, Any]:
    terminal_at = row.get("terminal_at")
    if isinstance(terminal_at, str):
        terminal_at = datetime.fromisoformat(terminal_at)
    expired = bool(
        terminal_at is not None
        and now >= terminal_at + timedelta(seconds=BODY_RETENTION_SECONDS)
    )
    purged = row.get("body_purged_at") is not None or expired
    citations = None if purged else load_json_list(row.get("citations_json"))
    sources = None if purged else load_json_list(row.get("sources_json"))
    return {
        "turn_id": row["id"],
        "created_at": row["created_at"],
        "status": row.get("terminal_event"),
        "code": row.get("terminal_code"),
        "message": None if purged else row.get("terminal_message"),
        "question": None if purged else row.get("question"),
        "answer": None if purged else row.get("answer"),
        "citations": citations,
        "sources": sources,
        "body_available": not purged,
    }


def session_snapshot(
    conn: sqlite3.Connection, session_id: str, *, now: datetime | None = None
) -> dict[str, Any]:
    now = now or datetime.now()
    completed = list_completed_turns(conn, session_id, limit=20)
    active = list_active_turns(conn, session_id)
    active_view: dict[str, Any] | None = None
    if len(active) > 1:
        raise AssistantNotReadyError("multiple active assistant turns")
    if len(active) == 1:
        item = active[0]
        active_view = {
            "turn_id": item["id"],
            "question": item.get("question"),
            "created_at": item["created_at"],
            "stage": latest_stage(conn, item["id"]),
        }
    turns = [public_completed_turn_at(item, now) for item in completed]
    for turn in turns:
        vote = conn.execute(
            "SELECT outcome FROM assistant_activity_events WHERE event_id = ? AND kind='feedback'",
            (f"{turn['turn_id']}:feedback",),
        ).fetchone() if turn["body_available"] and turn["status"] == "answer" else None
        turn["feedback"] = vote["outcome"] if vote else None
    return {
        "turns": turns,
        "active_turn": active_view,
    }


def load_history(
    conn: sqlite3.Connection, session_id: str, limit: int = MAX_HISTORY_TURNS
) -> list[dict[str, str]]:
    rows = conn.execute(
        """
        SELECT question, answer FROM assistant_history
        WHERE session_id = ? AND purged_at IS NULL
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()
    items = [{"question": row["question"], "answer": row["answer"]} for row in rows]
    items.reverse()
    return items


def load_history_questions(
    conn: sqlite3.Connection,
    session_id: str,
    *,
    now: datetime,
    limit: int = MAX_HISTORY_TURNS,
) -> list[str]:
    if not session_is_live(conn, session_id, now):
        return []
    rows = conn.execute(
        """
        SELECT question FROM assistant_history
        WHERE session_id = ? AND purged_at IS NULL
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()
    questions = [str(row["question"]) for row in rows]
    questions.reverse()
    return questions


def ensure_chat_budget(conn: sqlite3.Connection, day: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO assistant_chat_budgets (beijing_date) VALUES (?)",
        (day,),
    )


def ensure_query_budget(conn: sqlite3.Connection, day: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO assistant_query_embedding_budgets (beijing_date) VALUES (?)",
        (day,),
    )


def reserve_chat(
    conn: sqlite3.Connection,
    *,
    day: str,
    amount: int,
    cap: int,
) -> bool:
    ensure_chat_budget(conn, day)
    row = conn.execute(
        "SELECT reserved_micro, settled_micro, circuit_open "
        "FROM assistant_chat_budgets WHERE beijing_date = ?",
        (day,),
    ).fetchone()
    if row["circuit_open"]:
        return False
    if row["settled_micro"] + row["reserved_micro"] + amount > cap:
        return False
    conn.execute(
        "UPDATE assistant_chat_budgets "
        "SET reserved_micro = reserved_micro + ? WHERE beijing_date = ?",
        (amount, day),
    )
    return True


def reserve_query_embedding(conn: sqlite3.Connection, *, day: str, amount: int, cap: int) -> bool:
    ensure_query_budget(conn, day)
    row = conn.execute(
        "SELECT reserved_micro, settled_micro, circuit_open "
        "FROM assistant_query_embedding_budgets WHERE beijing_date = ?",
        (day,),
    ).fetchone()
    if (
        row["circuit_open"]
        or row["settled_micro"] + row["reserved_micro"] + amount > cap
    ):
        return False
    conn.execute(
        "UPDATE assistant_query_embedding_budgets "
        "SET reserved_micro = reserved_micro + ? WHERE beijing_date = ?",
        (amount, day),
    )
    return True


def settle_budget(
    conn: sqlite3.Connection,
    *,
    kind: str,
    day: str,
    reserved: int,
    settled: int,
    open_circuit: bool = False,
) -> None:
    table = "assistant_chat_budgets" if kind == KIND_CHAT else "assistant_query_embedding_budgets"
    conn.execute(
        f"""
        UPDATE {table}
        SET reserved_micro = MAX(0, reserved_micro - ?),
            settled_micro = settled_micro + ?,
            circuit_open = CASE WHEN ? THEN 1 ELSE circuit_open END
        WHERE beijing_date = ?
        """,
        (reserved, settled, 1 if open_circuit else 0, day),
    )


def count_active_leases(conn: sqlite3.Connection, scope: str, scope_key: str, now: datetime) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS n FROM assistant_leases
        WHERE scope = ? AND scope_key = ? AND expires_at > ?
        """,
        (scope, scope_key, now),
    ).fetchone()
    return int(row["n"])


def acquire_leases(
    conn: sqlite3.Connection,
    *,
    turn_id: str,
    session_id: str,
    ip_keys: list[str],
    now: datetime,
    lease_seconds: int,
    day: str,
) -> str | None:
    conn.execute("DELETE FROM assistant_leases WHERE expires_at <= ?", (now,))
    global_count = count_active_leases(conn, "global", "all", now)
    session_count = count_active_leases(conn, "session", session_id, now)
    ip_count = 0
    for key in ip_keys:
        ip_count += count_active_leases(conn, "ip", key, now)
    if session_count >= LEASE_SESSION or ip_count >= LEASE_IP or global_count >= LEASE_GLOBAL:
        return None
    token = random_id()
    expires = now + timedelta(seconds=lease_seconds)
    conn.execute(
        """
        INSERT INTO assistant_leases (
            scope, scope_key, fencing_token, owner_turn_id,
            heartbeat_at, expires_at, beijing_date
        )
        VALUES ('session', ?, ?, ?, ?, ?, ?)
        """,
        (session_id, token, turn_id, now, expires, day),
    )
    conn.execute(
        """
        INSERT INTO assistant_leases (
            scope, scope_key, fencing_token, owner_turn_id,
            heartbeat_at, expires_at, beijing_date
        )
        VALUES ('ip', ?, ?, ?, ?, ?, ?)
        """,
        (ip_keys[0], token, turn_id, now, expires, day),
    )
    conn.execute(
        """
        INSERT INTO assistant_leases (
            scope, scope_key, fencing_token, owner_turn_id,
            heartbeat_at, expires_at, beijing_date
        )
        VALUES ('global', 'all', ?, ?, ?, ?, ?)
        """,
        (token, turn_id, now, expires, day),
    )
    return token


def release_leases(conn: sqlite3.Connection, turn_id: str) -> None:
    conn.execute("DELETE FROM assistant_leases WHERE owner_turn_id = ?", (turn_id,))


def lease_still_valid(conn: sqlite3.Connection, turn_id: str, token: str, now: datetime) -> bool:
    turn = get_turn(conn, turn_id)
    identity = identity_from_turn(turn or {})
    return bool(
        identity
        and identity.fencing_token == token
        and normal_mutation_permit(conn, identity, now)
    )


def heartbeat_leases(
    conn: sqlite3.Connection,
    *,
    turn_id: str,
    token: str,
    now: datetime,
    lease_seconds: int,
    absolute_expires_at: datetime,
) -> bool:
    if not turn_session_live(conn, turn_id, now):
        return False
    if not lease_still_valid(conn, turn_id, token, now):
        return False
    deadline = now + timedelta(seconds=lease_seconds)
    if isinstance(absolute_expires_at, str):
        absolute_expires_at = datetime.fromisoformat(absolute_expires_at)
    if deadline > absolute_expires_at:
        deadline = absolute_expires_at
    if deadline <= now:
        return False
    cur = conn.execute(
        """
        UPDATE assistant_leases
        SET heartbeat_at = ?, expires_at = ?
        WHERE owner_turn_id = ? AND fencing_token = ? AND expires_at > ?
        """,
        (now, deadline, turn_id, token, now),
    )
    return cur.rowcount == 3


def sync_session_csrf(conn: sqlite3.Connection, session_id: str, csrf_hmac: str) -> None:
    conn.execute(
        "UPDATE assistant_sessions SET csrf_hmac = ? WHERE id = ? AND tombstoned_at IS NULL",
        (csrf_hmac, session_id),
    )


def list_attempts(
    conn: sqlite3.Connection, turn_id: str, kind: str
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM assistant_attempts
        WHERE turn_id = ? AND kind = ?
        ORDER BY created_at ASC
        """,
        (turn_id, kind),
    ).fetchall()
    return [row_dict(row) or {} for row in rows]


def next_cleanup_deadline(conn: sqlite3.Connection, now: datetime) -> datetime | None:
    body = conn.execute(
        """
        SELECT MIN(terminal_at) AS t FROM assistant_turns
        WHERE status = 'terminal' AND terminal_at IS NOT NULL AND body_purged_at IS NULL
        """,
    ).fetchone()
    tombstone = conn.execute(
        """
        SELECT MIN(body_purged_at) AS t FROM assistant_turns
        WHERE body_purged_at IS NOT NULL
        """,
    ).fetchone()
    candidates: list[datetime] = []
    if body and body["t"] is not None:
        stamp = body["t"]
        if not isinstance(stamp, datetime):
            stamp = datetime.fromisoformat(str(stamp))
        candidates.append(stamp + timedelta(seconds=BODY_RETENTION_SECONDS))
    if tombstone and tombstone["t"] is not None:
        stamp = (
            tombstone["t"]
            if isinstance(tombstone["t"], datetime)
            else datetime.fromisoformat(str(tombstone["t"]))
        )
        candidates.append(stamp + timedelta(hours=48))
    overdue = conn.execute(
        """
        SELECT MIN(idle_expires_at) AS t FROM assistant_sessions
        WHERE tombstoned_at IS NULL
        """,
    ).fetchone()
    if overdue and overdue["t"] is not None:
        stamp = (
            overdue["t"]
            if isinstance(overdue["t"], datetime)
            else datetime.fromisoformat(str(overdue["t"]))
        )
        candidates.append(stamp)
    return min(candidates) if candidates else None


def insert_attempt(
    conn: sqlite3.Connection,
    *,
    attempt_id: str,
    turn_id: str,
    kind: str,
    fencing_token: str,
    request_fingerprint: str,
    price_snapshot_json: str,
    day: str,
    max_cost_micro: int,
    now: datetime,
) -> None:
    conn.execute(
        """
        INSERT INTO assistant_attempts (
            id, turn_id, kind, status, fencing_token, request_fingerprint,
            price_snapshot_json, beijing_date, max_cost_micro, settled_micro, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
        """,
        (
            attempt_id,
            turn_id,
            kind,
            ATTEMPT_PREPARED,
            fencing_token,
            request_fingerprint,
            price_snapshot_json,
            day,
            max_cost_micro,
            now,
            now,
        ),
    )


def mark_attempt_sending(
    conn: sqlite3.Connection,
    *,
    attempt_id: str,
    fencing_token: str,
    now: datetime,
    request_fingerprint: str | None = None,
    identity: ExecutionIdentity | None = None,
) -> bool:
    attempt = get_attempt(conn, attempt_id)
    if attempt is None:
        return False
    if identity is not None:
        if attempt["turn_id"] != identity.turn_id or not normal_mutation_permit(
            conn, identity, now
        ):
            return False
    elif not turn_session_live(conn, attempt["turn_id"], now):
        return False
    if request_fingerprint:
        cur = conn.execute(
            """
            UPDATE assistant_attempts
            SET status = ?, request_fingerprint = ?, updated_at = ?
            WHERE id = ? AND fencing_token = ? AND status = ?
            """,
            (
                ATTEMPT_SENDING,
                request_fingerprint,
                now,
                attempt_id,
                fencing_token,
                ATTEMPT_PREPARED,
            ),
        )
    else:
        cur = conn.execute(
            """
            UPDATE assistant_attempts
            SET status = ?, updated_at = ?
            WHERE id = ? AND fencing_token = ? AND status = ?
            """,
            (ATTEMPT_SENDING, now, attempt_id, fencing_token, ATTEMPT_PREPARED),
        )
    return cur.rowcount == 1


def complete_attempt(
    conn: sqlite3.Connection,
    *,
    attempt_id: str,
    fencing_token: str,
    status: str,
    settled_micro: int,
    usage_json: str | None,
    finish_reason: str | None,
    parsed_json: str | None,
    vector_json: str | None,
    now: datetime,
) -> bool:
    cur = conn.execute(
        """
        UPDATE assistant_attempts
        SET status = ?, settled_micro = ?, usage_json = ?, finish_reason = ?,
            parsed_json = ?, vector_json = ?, updated_at = ?
        WHERE id = ? AND fencing_token = ? AND status IN (?, ?)
        """,
        (
            status,
            settled_micro,
            usage_json,
            finish_reason,
            parsed_json,
            vector_json,
            now,
            attempt_id,
            fencing_token,
            ATTEMPT_SENDING,
            ATTEMPT_PREPARED,
        ),
    )
    return cur.rowcount == 1


def settle_attempt(
    conn: sqlite3.Connection,
    *,
    attempt: dict[str, Any],
    status: str,
    settled_micro: int,
    usage_json: str | None = None,
    finish_reason: str | None = None,
    parsed_json: str | None = None,
    vector_json: str | None = None,
    now: datetime,
    open_circuit: bool = False,
    provider_fact_status: str | None = None,
    provider_fact_reason: str | None = None,
    provider_fact_outcome: str | None = None,
    metered_outcome: str | None = None,
    latency_ms: int | None = None,
) -> bool:
    """CAS the attempt into a terminal status, then change the day bucket once.

    Attempt identity: reservation = unused_released + settled; overage adds
    `reservation + overage = unused_released + settled` with unused_released=0.
    The day bucket always drops the original reservation from reserved_micro.
    """
    reservation = int(attempt["max_cost_micro"])
    actual = int(settled_micro)
    overage = actual > reservation
    requested_body = parsed_json is not None or vector_json is not None
    body_permitted = True
    if requested_body:
        turn = get_turn(conn, attempt["turn_id"])
        identity = identity_from_turn(turn or {})
        body_permitted = bool(identity and normal_mutation_permit(conn, identity, now))
        if not body_permitted:
            parsed_json = None
            vector_json = None
            status = ATTEMPT_UNKNOWN
    ok = complete_attempt(
        conn,
        attempt_id=attempt["id"],
        fencing_token=attempt["fencing_token"],
        status=status,
        settled_micro=actual,
        usage_json=usage_json,
        finish_reason=finish_reason,
        parsed_json=parsed_json,
        vector_json=vector_json,
        now=now,
    )
    if not ok:
        return False
    settle_budget(
        conn,
        kind=attempt["kind"],
        day=attempt["beijing_date"],
        reserved=reservation,
        settled=actual,
        open_circuit=open_circuit or overage,
    )
    if attempt.get("status") == ATTEMPT_SENDING:
        try:
            usage = json.loads(usage_json) if usage_json else {}
        except (TypeError, json.JSONDecodeError):
            usage = {}
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        derived_outcome = "success" if status == ATTEMPT_SUCCEEDED else "unknown"
        conn.execute(
            """
            INSERT OR IGNORE INTO assistant_metered_events
                (event_id, beijing_date, kind, outcome, input_tokens, output_tokens,
                 cost_micro, latency_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt["id"],
                attempt["beijing_date"],
                attempt["kind"],
                metered_outcome or derived_outcome,
                int(input_tokens) if isinstance(input_tokens, int) and input_tokens >= 0 else None,
                int(output_tokens)
                if isinstance(output_tokens, int) and output_tokens >= 0
                else None,
                actual,
                latency_ms,
                now,
            ),
        )
        fact_status = provider_fact_status or (
            "healthy" if status == ATTEMPT_SUCCEEDED else "unknown"
        )
        fact_outcome = provider_fact_outcome or derived_outcome
        reason = provider_fact_reason or (
            "provider_call_succeeded"
            if status == ATTEMPT_SUCCEEDED
            else "provider_result_unknown"
        )
        conn.execute(
            """
            INSERT INTO assistant_provider_facts(kind, status, reason_code, outcome, observed_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(kind) DO UPDATE SET status = excluded.status,
                reason_code = excluded.reason_code, outcome = excluded.outcome,
                observed_at = excluded.observed_at
            """,
            (attempt["kind"], fact_status, reason, fact_outcome, now),
        )
    turn = get_turn(conn, attempt["turn_id"])
    if turn is not None:
        enforce_session_byte_cap(conn, turn["session_id"], now=now)
    return body_permitted


def fail_unused_attempts(
    conn: sqlite3.Connection, turn_id: str, *, kind: str, now: datetime
) -> None:
    rows = conn.execute(
        """
        SELECT * FROM assistant_attempts
        WHERE turn_id = ? AND kind = ? AND status = ?
        """,
        (turn_id, kind, ATTEMPT_PREPARED),
    ).fetchall()
    for row in rows:
        attempt = row_dict(row) or {}
        settle_attempt(
            conn,
            attempt=attempt,
            status=ATTEMPT_FAILED,
            settled_micro=0,
            now=now,
        )


def get_attempt(conn: sqlite3.Connection, attempt_id: str) -> dict[str, Any] | None:
    return row_dict(
        conn.execute("SELECT * FROM assistant_attempts WHERE id = ?", (attempt_id,)).fetchone()
    )


def latest_attempt(conn: sqlite3.Connection, turn_id: str, kind: str) -> dict[str, Any] | None:
    return row_dict(
        conn.execute(
            """
            SELECT * FROM assistant_attempts
            WHERE turn_id = ? AND kind = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (turn_id, kind),
        ).fetchone()
    )


def persist_event(
    conn: sqlite3.Connection,
    *,
    turn_id: str,
    event_name: str,
    data: dict[str, Any],
    now: datetime,
    identity: ExecutionIdentity | None = None,
) -> dict[str, Any]:
    if identity is not None:
        permitted = identity.turn_id == turn_id and normal_mutation_permit(conn, identity, now)
    else:
        permitted = turn_session_live(conn, turn_id, now)
    if not permitted:
        return {"seq": 0, "event_name": event_name, "data_json": "{}", "inserted": False}
    existing = conn.execute(
        """
        SELECT * FROM assistant_event_journal
        WHERE turn_id = ? AND event_name = ? AND json_extract(data_json, '$.idempotent') = 1
        ORDER BY seq DESC LIMIT 1
        """,
        (turn_id, event_name),
    ).fetchone()
    if existing and event_name not in {"answer", "refusal", "error"}:
        replay = row_dict(existing) or {}
        replay["inserted"] = False
        return replay
    row = conn.execute(
        "SELECT COALESCE(MAX(seq), 0) AS seq FROM assistant_event_journal WHERE turn_id = ?",
        (turn_id,),
    ).fetchone()
    seq = int(row["seq"]) + 1
    if seq > MAX_EVENTS_PER_TURN:
        raise AssistantNotReadyError("event journal overflow")
    payload = dict(data)
    payload["event_id"] = seq
    payload["turn_id"] = turn_id
    payload["idempotent"] = 1
    conn.execute(
        """
        INSERT INTO assistant_event_journal (turn_id, seq, event_name, data_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (turn_id, seq, event_name, json_dumps(payload), now),
    )
    result = {
        "seq": seq,
        "event_name": event_name,
        "data_json": json_dumps(payload),
        "inserted": True,
    }
    if identity is not None:
        result.update(identity.as_state())
        result["terminal"] = False
    turn = get_turn(conn, turn_id)
    session_id = identity.session_id if identity else (turn or {})["session_id"]
    enforce_session_byte_cap(conn, session_id, now=now)
    return result


def events_after(conn: sqlite3.Connection, turn_id: str, cursor: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT seq, event_name, data_json FROM assistant_event_journal
        WHERE turn_id = ? AND seq > ?
        ORDER BY seq ASC
        """,
        (turn_id, cursor),
    ).fetchall()
    return [row_dict(row) or {} for row in rows]


def max_event_seq(conn: sqlite3.Connection, turn_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(seq), 0) AS seq FROM assistant_event_journal WHERE turn_id = ?",
        (turn_id,),
    ).fetchone()
    return int(row["seq"])


def write_terminal(
    conn: sqlite3.Connection,
    *,
    turn_id: str,
    event_name: str,
    code: str,
    message: str,
    answer: str | None,
    citations: list[dict[str, Any]] | None,
    sources: list[dict[str, Any]] | None,
    now: datetime,
    identity: ExecutionIdentity | None = None,
    history_question: str | None = None,
    history_answer: str | None = None,
    recovery: bool = False,
) -> dict[str, Any]:
    turn = get_turn(conn, turn_id)
    if turn is None:
        return {"seq": 0, "event_name": event_name, "data_json": "{}", "inserted": False}
    live = turn_session_live(conn, turn_id, now)
    if turn["status"] == "terminal":
        return {"seq": 0, "event_name": event_name, "data_json": "{}", "inserted": False}
    if identity is not None and not normal_mutation_permit(conn, identity, now):
        return {"seq": 0, "event_name": event_name, "data_json": "{}", "inserted": False}
    # Internal model support quotes are only needed while a turn can resume.
    # Clear on every authorized terminal path, including refusals and recovery.
    conn.execute(
        "UPDATE assistant_attempts SET parsed_json = NULL WHERE turn_id = ?",
        (turn_id,),
    )
    if not live or recovery:
        conn.execute(
            """
            UPDATE assistant_turns
            SET status = 'terminal', terminal_at = ?, terminal_event = ?, terminal_code = ?,
                terminal_message = ?, answer = NULL, citations_json = NULL, sources_json = NULL
            WHERE id = ? AND status IN ('accepted', 'running')
            """,
            (now, event_name, code, None, turn_id),
        )
        fail_unused_attempts(conn, turn_id, kind=KIND_CHAT, now=now)
        fail_unused_attempts(conn, turn_id, kind=KIND_QUERY_EMBEDDING, now=now)
        return {"seq": 0, "event_name": event_name, "data_json": "{}", "inserted": False}
    updated = conn.execute(
        """
        UPDATE assistant_turns
        SET status = 'terminal', terminal_at = ?, terminal_event = ?, terminal_code = ?,
            terminal_message = ?, answer = ?, citations_json = ?, sources_json = ?
        WHERE id = ? AND status IN ('accepted', 'running')
        """,
        (
            now,
            event_name,
            code,
            message,
            answer,
            json_dumps(citations) if citations is not None else None,
            json_dumps(sources) if sources is not None else None,
            turn_id,
        ),
    )
    if updated.rowcount != 1:
        return {"seq": 0, "event_name": event_name, "data_json": "{}", "inserted": False}
    record_activity_event(
        conn,
        event_id=f"{turn_id}:{event_name}",
        kind=event_name if event_name in {"refusal", "error"} else "answer",
        outcome=code,
        now=now,
        latency_ms=max(0, round((as_utc(now) - as_utc(datetime.fromisoformat(
            str(turn["created_at"])
        ))).total_seconds() * 1000)),
    )
    data: dict[str, Any] = {
        "type": event_name,
        "code": code,
        "message": message,
    }
    if event_name == "answer":
        data["answer"] = answer
        data["citations"] = citations or []
        data["sources"] = sources or []
    event = persist_event(conn, turn_id=turn_id, event_name=event_name, data=data, now=now)
    if history_question and history_answer and event_name == "answer":
        add_history(
            conn,
            session_id=turn["session_id"],
            turn_id=turn_id,
            question=history_question,
            answer=history_answer,
            now=now,
        )
    fail_unused_attempts(conn, turn_id, kind=KIND_CHAT, now=now)
    fail_unused_attempts(conn, turn_id, kind=KIND_QUERY_EMBEDDING, now=now)
    session_row = conn.execute(
        "SELECT session_id FROM assistant_turns WHERE id = ?",
        (turn_id,),
    ).fetchone()
    if session_row is not None:
        enforce_session_byte_cap(conn, session_row["session_id"], now=now)
    if event.get("inserted") and identity is not None:
        event.update(identity.as_state())
        event["terminal"] = True
    return event


def add_history(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    turn_id: str,
    question: str,
    answer: str,
    now: datetime,
) -> None:
    conn.execute(
        """
        INSERT INTO assistant_history (session_id, turn_id, question, answer, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, turn_id, question, answer, now),
    )


def current_receipt(conn: sqlite3.Connection) -> dict[str, Any] | None:
    return row_dict(
        conn.execute(
            """
            SELECT * FROM assistant_readiness_receipts
            WHERE revoked_at IS NULL
            ORDER BY created_at DESC LIMIT 1
            """
        ).fetchone()
    )


def csrf_matches(
    session: dict[str, Any], header: str, cookie: str, secret: str, raw_csrf: str | None = None
) -> bool:
    if not header or not cookie or not compare(header, cookie):
        return False
    from .crypto import hmac_hex

    return compare(hmac_hex(secret, header, context="assistant-csrf"), session["csrf_hmac"])


def purge_billing_tombstones(conn: sqlite3.Connection, now: datetime) -> None:
    cutoff = now - timedelta(hours=IDEMPOTENCY_TOMBSTONE_HOURS)
    rows = conn.execute(
        """
        SELECT id, thread_id, session_id FROM assistant_turns
        WHERE body_purged_at IS NOT NULL AND body_purged_at <= ?
        """,
        (cutoff,),
    ).fetchall()
    for row in rows:
        turn_id = row["id"]
        unsettled = conn.execute(
            """
            SELECT COUNT(*) AS n FROM assistant_attempts
            WHERE turn_id = ? AND status IN ('prepared', 'sending')
            """,
            (turn_id,),
        ).fetchone()["n"]
        if int(unsettled):
            open_cleanup_breaker(conn, now, "unsettled attempt blocked 48h purge")
            continue
        if row["thread_id"]:
            marker = conn.execute(
                "SELECT checkpoint_deleted_at FROM assistant_turns WHERE id = ?",
                (turn_id,),
            ).fetchone()
            if marker is None or marker["checkpoint_deleted_at"] is None:
                record_cleanup_retry(
                    conn,
                    kind="checkpoint_delete",
                    target_id=turn_id,
                    now=now,
                    error="checkpoint marker missing at 48h purge",
                )
                continue
        try:
            conn.execute("DELETE FROM assistant_event_journal WHERE turn_id = ?", (turn_id,))
            conn.execute("DELETE FROM assistant_history WHERE turn_id = ?", (turn_id,))
            conn.execute("DELETE FROM assistant_attempts WHERE turn_id = ?", (turn_id,))
            conn.execute("DELETE FROM assistant_leases WHERE owner_turn_id = ?", (turn_id,))
            conn.execute("DELETE FROM assistant_turns WHERE id = ?", (turn_id,))
        except sqlite3.Error:
            open_cleanup_breaker(conn, now, "48h purge foreign key failure")
            raise
    sessions = conn.execute(
        """
        SELECT id FROM assistant_sessions
        WHERE tombstoned_at IS NOT NULL OR idle_expires_at <= ? OR absolute_expires_at <= ?
        """,
        (now, now),
    ).fetchall()
    for item in sessions:
        children = conn.execute(
            "SELECT COUNT(*) AS n FROM assistant_turns WHERE session_id = ?",
            (item["id"],),
        ).fetchone()["n"]
        leases = conn.execute(
            "SELECT COUNT(*) AS n FROM assistant_leases WHERE scope = 'session' AND scope_key = ?",
            (item["id"],),
        ).fetchone()["n"]
        if int(children) or int(leases):
            continue
        try:
            conn.execute("DELETE FROM assistant_sessions WHERE id = ?", (item["id"],))
        except sqlite3.Error:
            open_cleanup_breaker(conn, now, "session purge foreign key failure")
            raise


def _utf8_sum(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...]) -> int:
    row = conn.execute(sql, params).fetchone()
    return int(row[0] if row and row[0] is not None else 0)


def session_utf8_bytes(conn: sqlite3.Connection, session_id: str) -> int:
    turn_bytes = _utf8_sum(
        conn,
        """
        SELECT COALESCE(SUM(
            LENGTH(CAST(IFNULL(question, '') AS BLOB))
            + LENGTH(CAST(IFNULL(answer, '') AS BLOB))
            + LENGTH(CAST(IFNULL(terminal_message, '') AS BLOB))
            + LENGTH(CAST(IFNULL(citations_json, '') AS BLOB))
            + LENGTH(CAST(IFNULL(sources_json, '') AS BLOB))
        ), 0)
        FROM assistant_turns WHERE session_id = ?
        """,
        (session_id,),
    )
    journal_bytes = _utf8_sum(
        conn,
        """
        SELECT COALESCE(SUM(LENGTH(CAST(data_json AS BLOB))), 0)
        FROM assistant_event_journal
        WHERE turn_id IN (SELECT id FROM assistant_turns WHERE session_id = ?)
        """,
        (session_id,),
    )
    history_bytes = _utf8_sum(
        conn,
        """
        SELECT COALESCE(SUM(
            LENGTH(CAST(IFNULL(question, '') AS BLOB))
            + LENGTH(CAST(IFNULL(answer, '') AS BLOB))
        ), 0)
        FROM assistant_history WHERE session_id = ?
        """,
        (session_id,),
    )
    attempt_bytes = _utf8_sum(
        conn,
        """
        SELECT COALESCE(SUM(
            LENGTH(CAST(IFNULL(parsed_json, '') AS BLOB))
            + LENGTH(CAST(IFNULL(vector_json, '') AS BLOB))
        ), 0)
        FROM assistant_attempts
        WHERE turn_id IN (SELECT id FROM assistant_turns WHERE session_id = ?)
        """,
        (session_id,),
    )
    checkpoint_bytes = _utf8_sum(
            conn,
            """
            SELECT COALESCE(SUM(
                LENGTH(CAST(IFNULL(checkpoint, '') AS BLOB))
                + LENGTH(CAST(IFNULL(metadata, '') AS BLOB))
            ), 0)
            FROM checkpoints
            WHERE thread_id IN (
                SELECT thread_id FROM assistant_turns
                WHERE session_id = ? AND thread_id IS NOT NULL
            )
            """,
            (session_id,),
        )
    writes_bytes = _utf8_sum(
            conn,
            """
            SELECT COALESCE(SUM(LENGTH(CAST(IFNULL(value, '') AS BLOB))), 0)
            FROM writes
            WHERE thread_id IN (
                SELECT thread_id FROM assistant_turns
                WHERE session_id = ? AND thread_id IS NOT NULL
            )
            """,
            (session_id,),
        )
    return (
        turn_bytes
        + journal_bytes
        + history_bytes
        + attempt_bytes
        + checkpoint_bytes
        + writes_bytes
    )


def purge_turn_body(conn: sqlite3.Connection, turn_id: str, now: datetime) -> None:
    conn.execute("DELETE FROM assistant_activity_events WHERE event_id = ?",
                 (f"{turn_id}:feedback",))
    conn.execute(
        """
        UPDATE assistant_turns
        SET question = NULL, answer = NULL, citations_json = NULL, sources_json = NULL,
            terminal_message = terminal_code, body_purged_at = ?
        WHERE id = ? AND body_purged_at IS NULL
        """,
        (now, turn_id),
    )
    conn.execute("DELETE FROM assistant_event_journal WHERE turn_id = ?", (turn_id,))
    conn.execute(
        "UPDATE assistant_history SET question = '', answer = '', purged_at = ? WHERE turn_id = ?",
        (now, turn_id),
    )
    conn.execute(
        "UPDATE assistant_attempts SET parsed_json = NULL, vector_json = NULL, updated_at = ? "
        "WHERE turn_id = ?",
        (now, turn_id),
    )


def enforce_session_byte_cap(
    conn: sqlite3.Connection, session_id: str, now: datetime | None = None
) -> bool:
    if now is None:
        now = datetime.now()
    def _measure() -> int | None:
        try:
            return session_utf8_bytes(conn, session_id)
        except sqlite3.Error as exc:
            record_cleanup_retry(
                conn,
                kind="byte_accounting",
                target_id=session_id,
                now=now,
                error=str(exc),
            )
            conn.execute(
                "UPDATE assistant_sessions SET cleanup_breaker = 1 WHERE id = ?",
                (session_id,),
            )
            return None

    total = _measure()
    if total is None:
        return True
    conn.execute(
        "UPDATE assistant_sessions SET persisted_bytes = ? WHERE id = ?",
        (total, session_id),
    )
    if total <= SESSION_BYTE_LIMIT:
        return False
    old = conn.execute(
        """
        SELECT id FROM assistant_turns
        WHERE session_id = ? AND status = 'terminal' AND body_purged_at IS NULL
        ORDER BY created_at ASC
        """,
        (session_id,),
    ).fetchall()
    for item in old:
        purge_turn_body(conn, item["id"], now)
        measured = _measure()
        if measured is None:
            return True
        total = measured
        conn.execute(
            "UPDATE assistant_sessions SET persisted_bytes = ? WHERE id = ?",
            (total, session_id),
        )
        if total <= SESSION_BYTE_LIMIT:
            return False
    if total > SESSION_BYTE_LIMIT:
        active = conn.execute(
            "SELECT id FROM assistant_turns WHERE session_id = ? "
            "AND status IN ('accepted', 'running') ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()
        for item in active:
            turn_id = item["id"]
            release_leases(conn, turn_id)
            attempts = conn.execute(
                "SELECT * FROM assistant_attempts WHERE turn_id = ? "
                "AND status IN ('prepared', 'sending')",
                (turn_id,),
            ).fetchall()
            for row in attempts:
                attempt = row_dict(row) or {}
                actual = int(attempt["max_cost_micro"]) if attempt["status"] == "sending" else 0
                terminal_status = "unknown" if attempt["status"] == "sending" else "failed"
                if complete_attempt(
                    conn,
                    attempt_id=attempt["id"],
                    fencing_token=attempt["fencing_token"],
                    status=terminal_status,
                    settled_micro=actual,
                    usage_json=None,
                    finish_reason=None,
                    parsed_json=None,
                    vector_json=None,
                    now=now,
                ):
                    settle_budget(
                        conn,
                        kind=attempt["kind"],
                        day=attempt["beijing_date"],
                        reserved=int(attempt["max_cost_micro"]),
                        settled=actual,
                        open_circuit=attempt["status"] == "sending",
                    )
            conn.execute("DELETE FROM assistant_event_journal WHERE turn_id = ?", (turn_id,))
            conn.execute(
                "UPDATE assistant_history SET question = '', answer = '', purged_at = ? "
                "WHERE turn_id = ?",
                (now, turn_id),
            )
            conn.execute(
                """
                UPDATE assistant_turns
                SET status = 'terminal', terminal_at = ?, terminal_event = 'error',
                    terminal_code = 'provider_result_unknown', terminal_message = NULL,
                    question = NULL, current_path = NULL, answer = NULL,
                    citations_json = NULL, sources_json = NULL, body_purged_at = ?
                WHERE id = ?
                """,
                (now, now, turn_id),
            )
        open_cleanup_breaker(conn, now, "session utf-8 cap exceeded")
        conn.execute(
            "UPDATE assistant_sessions SET cleanup_breaker = 1 WHERE id = ?",
            (session_id,),
        )
        return True
    return False
