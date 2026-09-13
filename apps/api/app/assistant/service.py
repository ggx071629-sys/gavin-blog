from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta
from typing import Any

from fastapi import Request

from .admin_scope import cookie_name, request_scope, session_context
from .constants import (
    BODY_RETENTION_SECONDS,
    CODE_BUDGET_EXHAUSTED,
    CODE_CONCURRENCY_LIMITED,
    CODE_RATE_LIMITED,
    CODE_SESSION_REVOKING,
    ENVELOPE_LIMIT,
    ENVELOPE_WINDOW_SECONDS,
    KIND_CHAT,
    KIND_QUERY_EMBEDDING,
    QUESTION_LIMIT_PER_10_MIN,
    QUESTION_LIMIT_PER_MINUTE,
    SESSION_CREATE_LIMIT,
    SESSION_CREATE_WINDOW_SECONDS,
    TERMINAL_REFUSAL,
)
from .crypto import hmac_hex, payload_hmac, random_id, random_token, session_csrf_token
from .errors import (
    AssistantNotReadyError,
    csrf_failed,
    disabled,
    event_cursor_invalid,
    idempotency_conflict,
    idempotency_expired,
    invalid_request,
    limited,
    not_ready,
    session_expired,
    session_missing,
)
from .graph import _worst_chat_cost
from .ip import client_ip
from .money import cny_to_micro, snapshot_json, tokens_cost_micro
from .origin import require_origin
from .preflight import normalize_question, preflight_question
from .store import (
    acquire_leases,
    breaker_open,
    count_rate_events,
    current_receipt,
    earliest_rate_release,
    enforce_session_byte_cap,
    find_turn_by_idempotency,
    get_session,
    get_turn,
    insert_rate_event,
    insert_session,
    insert_turn,
    max_event_seq,
    record_activity_event,
    reserve_chat,
    reserve_query_embedding,
    session_by_hmac,
    session_snapshot,
    set_execution_identity,
    sync_session_csrf,
    tombstone_session,
    touch_session,
    write_terminal,
)
from .time_beijing import beijing_date, in_midnight_overlap, next_beijing_midnight, seconds_until

IDEMPOTENCY_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
PUBLIC_SLUG_RE = r"[a-z0-9]+(?:-[a-z0-9]+)*"
PUBLIC_PATH_RE = re.compile(
    rf"^(?:/|/(?:articles|projects|books|archive|about|search)|"
    rf"/notes/\d{{4}}/(?:0[1-9]|1[0-2])/{PUBLIC_SLUG_RE}|"
    rf"/projects/{PUBLIC_SLUG_RE}|"
    rf"/books/\d{{4}}/(?:0[1-9]|1[0-2])/{PUBLIC_SLUG_RE})$"
)


def require_online(request: Request):
    assistant = getattr(request.app.state, "assistant", None)
    if assistant is None:
        if request.app.state.settings.assistant_online_enabled:
            raise not_ready()
        raise disabled()
    return assistant


def ip_keys(online, ip: str, now: datetime, *, for_leases: bool = False) -> list[str]:
    secret = str(online.settings.assistant_ip_hmac_secret)
    today = beijing_date(now)
    keys = [hmac_hex(secret, ip, context=f"ip|{today.isoformat()}")]
    if for_leases or in_midnight_overlap(now):
        yesterday = today - timedelta(days=1)
        keys.append(hmac_hex(secret, ip, context=f"ip|{yesterday.isoformat()}"))
    return keys


def _envelope(online, ip: str, kind: str, now: datetime, limit: int, window: int) -> int | None:
    keys = ip_keys(online, ip, now)
    since = now - timedelta(seconds=window)

    def _check(conn):
        count = count_rate_events(conn, ip_hmacs=keys, kind=kind, since=since)
        if count >= limit:
            retry_after = (
                earliest_rate_release(
                    conn,
                    ip_hmacs=keys,
                    kind=kind,
                    since=since,
                    window_seconds=window,
                    now=now,
                )
                or 1
            )
            from .crypto import digest

            record_activity_event(
                conn,
                event_id=digest(f"rate|{kind}|{keys[0]}|{now.isoformat()}"),
                kind="rate_limit_decision",
                outcome=f"{kind}:limited",
                now=now,
            )
            return retry_after
        insert_rate_event(conn, ip_hmac=keys[0], kind=kind, now=now)
        from .crypto import digest

        record_activity_event(
            conn,
            event_id=digest(f"rate|{kind}|{keys[0]}|{now.isoformat()}"),
            kind="rate_limit_decision",
            outcome=f"{kind}:allowed",
            now=now,
        )
        return None

    return online.control.immediate(_check)


def charge_envelope(request: Request, online) -> str:
    ip = client_ip(request, online.settings)
    now = online.now()
    retry = _envelope(online, ip, "envelope", now, ENVELOPE_LIMIT, ENVELOPE_WINDOW_SECONDS)
    if retry:
        raise limited(CODE_RATE_LIMITED, retry)
    return ip


def client_policy(settings) -> dict[str, int]:
    question_max = int(settings.assistant_question_max_chars)
    idle = int(settings.assistant_session_idle_seconds)
    absolute = int(settings.assistant_session_absolute_seconds)
    body = int(BODY_RETENTION_SECONDS)
    if question_max < 1 or question_max > 2000 or idle <= 0 or absolute <= 0 or body <= 0:
        raise not_ready()
    return {
        "question_max_chars": question_max,
        "session_idle_seconds": idle,
        "session_absolute_seconds": absolute,
        "body_retention_seconds": body,
    }


def _issue_csrf(online, session_id: str) -> str:
    secret = str(online.settings.assistant_csrf_hmac_secret)
    token = session_csrf_token(secret, session_id)
    csrf_hmac = hmac_hex(secret, token, context="assistant-csrf")
    online.control.immediate(lambda conn: sync_session_csrf(conn, session_id, csrf_hmac))
    return token


def create_session(request: Request, online) -> dict[str, Any]:
    settings = online.settings
    require_origin(request, settings, require_fetch_metadata=settings.environment == "production")
    ip = client_ip(request, settings)
    now = online.now()
    from .recovery import raise_if_restore_locked

    raise_if_restore_locked(online, now)
    retry = _envelope(online, ip, "envelope", now, ENVELOPE_LIMIT, ENVELOPE_WINDOW_SECONDS)
    if retry:
        raise limited(CODE_RATE_LIMITED, retry)
    cookie = request.cookies.get(cookie_name(request))
    if cookie:
        session = online.control.read(
            lambda conn: session_by_hmac(
                conn,
                hmac_hex(
                    str(settings.assistant_session_hmac_secret),
                    cookie,
                    context=session_context(request),
                ),
            )
        )
        if session and session["tombstoned_at"] is None and _session_active(session, now):
            csrf = _issue_csrf(online, session["id"])
            return {"session": session, "cookie": cookie, "csrf": csrf, "created": False}
    if online.control.read(lambda conn: breaker_open(conn)):
        raise not_ready()
    retry = _envelope(
        online,
        ip,
        "session_create",
        now,
        SESSION_CREATE_LIMIT,
        SESSION_CREATE_WINDOW_SECONDS,
    )
    if retry:
        raise limited(CODE_RATE_LIMITED, retry)
    cookie = random_token()
    session_id = ("admin_" if request_scope(request) else "") + random_id()
    csrf_secret = str(settings.assistant_csrf_hmac_secret)
    csrf = session_csrf_token(csrf_secret, session_id)

    def _create(conn):
        from .operational import gate_for_turn_admission

        gate = gate_for_turn_admission(
            conn, online=online, now=now, admin=bool(request_scope(request))
        )
        if gate.get("_blocked"):
            return {"_blocked": True}
        insert_session(
            conn,
            session_id=session_id,
            session_hmac=hmac_hex(
                str(settings.assistant_session_hmac_secret),
                cookie,
                context=session_context(request),
            ),
            csrf_hmac=hmac_hex(
                csrf_secret,
                csrf,
                context="assistant-csrf",
            ),
            now=now,
            idle_seconds=settings.assistant_session_idle_seconds,
            absolute_seconds=settings.assistant_session_absolute_seconds,
        )
        return get_session(conn, session_id)

    session = online.control.immediate(_create)
    if session and session.get("_blocked"):
        raise not_ready()
    return {"session": session, "cookie": cookie, "csrf": csrf, "created": True}


def load_session(request: Request, online, *, require_csrf: bool) -> dict[str, Any]:
    cookie = request.cookies.get(cookie_name(request))
    if not cookie:
        raise session_missing()
    now = online.now()
    session = online.control.read(
        lambda conn: session_by_hmac(
            conn,
            hmac_hex(
                str(online.settings.assistant_session_hmac_secret),
                cookie,
                context=session_context(request),
            ),
        )
    )
    if session is None:
        raise session_missing()
    if session["tombstoned_at"] is not None or not _session_active(session, now):
        raise session_expired()
    if require_csrf:
        from .store import csrf_matches

        header = request.headers.get("x-assistant-csrf", "")
        csrf_cookie = request.cookies.get(cookie_name(request, csrf=True), "")
        if not csrf_matches(
            session,
            header,
            csrf_cookie,
            str(online.settings.assistant_csrf_hmac_secret),
        ):
            raise csrf_failed()
    return session


def session_view(online, session: dict[str, Any]) -> dict[str, Any]:
    policy = client_policy(online.settings)

    def _read(conn):
        return session_snapshot(conn, session["id"], now=online.now())

    try:
        snapshot = online.control.read(_read)
    except AssistantNotReadyError as exc:
        raise not_ready() from exc

    def _turn(item: dict[str, Any]) -> dict[str, Any]:
        payload = dict(item)
        payload["created_at"] = _iso(item["created_at"])
        return payload

    active = snapshot["active_turn"]
    return {
        "session_id": session["id"],
        "created_at": _iso(session["created_at"]),
        "idle_expires_at": _iso(session["idle_expires_at"]),
        "absolute_expires_at": _iso(session["absolute_expires_at"]),
        "policy": policy,
        "turns": [_turn(item) for item in snapshot["turns"]],
        "active_turn": None
        if active is None
        else {
            "turn_id": active["turn_id"],
            "question": active.get("question"),
            "created_at": _iso(active["created_at"]),
            "stage": active.get("stage"),
        },
    }


async def delete_session(online, session: dict[str, Any]) -> tuple[int, str | None]:
    now = online.now()
    from .identity import identity_from_turn
    from .store import clear_cleanup_retry, purge_turn_body, record_cleanup_retry, release_leases

    async with online.serialization.hold(session["id"]):

        def _delete(conn):
            tombstone_session(conn, session["id"], now)
            rows = conn.execute(
                "SELECT * FROM assistant_turns WHERE session_id = ?",
                (session["id"],),
            ).fetchall()
            for row in rows:
                purge_turn_body(conn, row["id"], now)
                release_leases(conn, row["id"])
            return [{key: row[key] for key in row.keys()} for row in rows]

        turns = online.control.immediate(_delete)
        for turn in turns:
            online.hub.close(turn["id"])
        for turn in turns:
            identity = identity_from_turn(turn)
            if identity is None:
                if turn.get("thread_id") is None:
                    online.control.immediate(
                        lambda conn, turn_id=turn["id"]: conn.execute(
                            "UPDATE assistant_turns SET checkpoint_deleted_at = ? "
                            "WHERE id = ? AND thread_id IS NULL",
                            (now, turn_id),
                        )
                    )
                else:
                    online.control.immediate(
                        lambda conn, turn_id=turn["id"]: record_cleanup_retry(
                            conn,
                            kind="checkpoint_delete",
                            target_id=turn_id,
                            now=online.now(),
                            error="execution identity missing",
                        )
                    )
                continue
            try:
                empty = await online.saver.delete_thread_locked(identity)
                if not empty:
                    raise RuntimeError("checkpoint rows remain after delete")

                def _mark_checkpoint_deleted(conn, turn_id=turn["id"]) -> None:
                    conn.execute(
                        "UPDATE assistant_turns SET checkpoint_deleted_at = ? WHERE id = ?",
                        (online.now(), turn_id),
                    )
                    clear_cleanup_retry(conn, kind="checkpoint_delete", target_id=turn_id)

                online.control.immediate(_mark_checkpoint_deleted)
            except Exception as exc:
                online.control.immediate(
                    lambda conn, turn_id=turn["id"], error=str(exc): record_cleanup_retry(
                        conn,
                        kind="checkpoint_delete",
                        target_id=turn_id,
                        now=online.now(),
                        error=error,
                    )
                )

        def _remaining(conn):
            active = conn.execute(
                "SELECT COUNT(*) AS n FROM assistant_turns "
                "WHERE session_id = ? AND status IN ('accepted', 'running')",
                (session["id"],),
            ).fetchone()["n"]
            unsettled = conn.execute(
                "SELECT COUNT(*) AS n FROM assistant_attempts WHERE turn_id IN "
                "(SELECT id FROM assistant_turns WHERE session_id = ?) "
                "AND status IN ('prepared', 'sending')",
                (session["id"],),
            ).fetchone()["n"]
            checkpoints = conn.execute(
                "SELECT COUNT(*) AS n FROM assistant_turns WHERE session_id = ? "
                "AND thread_id IS NOT NULL AND checkpoint_deleted_at IS NULL",
                (session["id"],),
            ).fetchone()["n"]
            return int(active) + int(unsettled) + int(checkpoints)

        remaining = online.control.read(_remaining)
        remaining += sum(
            1
            for turn in turns
            if (task := online.tasks.get(turn["id"])) is not None and not task.done()
        )
        return (202, CODE_SESSION_REVOKING) if remaining else (204, None)


def accept_question(request: Request, online, payload: dict[str, Any]) -> dict[str, Any]:
    settings = online.settings
    require_origin(request, settings, require_fetch_metadata=settings.environment == "production")
    ip = client_ip(request, settings)
    now = online.now()
    from .recovery import raise_if_restore_locked

    raise_if_restore_locked(online, now)
    retry = _envelope(online, ip, "envelope", now, ENVELOPE_LIMIT, ENVELOPE_WINDOW_SECONDS)
    if retry:
        raise limited(CODE_RATE_LIMITED, retry)
    session = load_session(request, online, require_csrf=True)
    question_raw = payload.get("question")
    current_path = payload.get("current_path")
    try:
        question = normalize_question(
            str(question_raw or ""), max_chars=settings.assistant_question_max_chars
        )
    except ValueError as exc:
        raise invalid_request(str(exc)) from exc
    if current_path is not None:
        if (
            not isinstance(current_path, str)
            or len(current_path) > 300
            or not PUBLIC_PATH_RE.fullmatch(current_path)
        ):
            raise invalid_request("current_path is invalid")
    key = request.headers.get("idempotency-key", "")
    if not IDEMPOTENCY_RE.fullmatch(key):
        raise invalid_request("Idempotency-Key is invalid")
    cursor_header = request.headers.get("last-event-id")
    cursor = 0
    if cursor_header:
        if not cursor_header.isdigit():
            raise event_cursor_invalid()
        cursor = int(cursor_header)
    secret = str(settings.assistant_ip_hmac_secret)
    idem_hmac = hmac_hex(secret, key, context="assistant-idempotency")
    body_hmac = payload_hmac(secret, {"question": question, "current_path": current_path})
    existing = online.control.read(
        lambda conn: find_turn_by_idempotency(conn, session["id"], idem_hmac)
    )
    if existing:
        if existing["payload_hmac"] != body_hmac:
            raise idempotency_conflict()
        if existing["body_purged_at"] and existing["status"] == "terminal":
            raise idempotency_expired()
        if cursor:
            max_seq = online.control.read(lambda conn: max_event_seq(conn, existing["id"]))
            if cursor > max_seq:
                raise event_cursor_invalid()
        return {"turn": existing, "cursor": cursor, "replay": True, "ip": ip}

    if online.control.read(lambda conn: breaker_open(conn)):
        raise not_ready()
    preflight = preflight_question(question)
    keys = ip_keys(online, ip, now, for_leases=True)
    rate_keys = ip_keys(online, ip, now)
    minute_since = now - timedelta(seconds=60)
    ten_since = now - timedelta(seconds=600)

    def _admit(conn):
        from .operational import gate_for_turn_admission

        gate = gate_for_turn_admission(
            conn, online=online, now=now, admin=bool(request_scope(request))
        )
        if gate.get("_blocked"):
            return {"blocked_gate": True}
        live = get_session(conn, session["id"])
        if live is None or live["tombstoned_at"] is not None:
            raise session_expired()
        if not _session_active(live, now):
            raise session_expired()
        if live["fencing_epoch"] != session["fencing_epoch"]:
            raise session_expired()
        others = conn.execute(
            """
            SELECT COUNT(*) AS n FROM assistant_turns
            WHERE session_id = ? AND status IN ('accepted', 'running') AND preflight_blocked = 0
            """,
            (session["id"],),
        ).fetchone()["n"]
        if int(others):
            raise limited(CODE_CONCURRENCY_LIMITED, 1)
        receipt = current_receipt(conn)
        if receipt is None:
            raise not_ready()
        from .readiness import verify_receipt

        try:
            verify_receipt(settings, conn, generation=online.active_generation())
        except Exception as exc:
            raise not_ready() from exc
        q_minute = count_rate_events(conn, ip_hmacs=rate_keys, kind="question", since=minute_since)
        q_ten = count_rate_events(conn, ip_hmacs=rate_keys, kind="question", since=ten_since)
        if q_minute >= QUESTION_LIMIT_PER_MINUTE or q_ten >= QUESTION_LIMIT_PER_10_MIN:
            retry_after = (
                earliest_rate_release(
                    conn,
                    ip_hmacs=rate_keys,
                    kind="question",
                    since=minute_since if q_minute >= QUESTION_LIMIT_PER_MINUTE else ten_since,
                    window_seconds=60 if q_minute >= QUESTION_LIMIT_PER_MINUTE else 600,
                    now=now,
                )
                or 1
            )
            from .crypto import digest

            record_activity_event(
                conn,
                event_id=digest(f"question-rate|{rate_keys[0]}|{now.isoformat()}"),
                kind="rate_limit_decision",
                outcome="question:limited",
                now=now,
            )
            return {"limited_retry": retry_after}
        insert_rate_event(conn, ip_hmac=rate_keys[0], kind="question", now=now)
        turn_id = random_id()
        thread_id = None if preflight.blocked else random_id()
        insert_turn(
            conn,
            turn_id=turn_id,
            session_id=session["id"],
            idempotency_hmac=idem_hmac,
            payload_hmac=body_hmac,
            question=None if preflight.blocked else question,
            current_path=None if preflight.blocked else current_path,
            thread_id=thread_id,
            now=now,
            preflight_blocked=preflight.blocked,
        )
        record_activity_event(
            conn,
            event_id=turn_id,
            kind="accepted_question",
            outcome="accepted",
            now=now,
        )
        if preflight.blocked:
            record_activity_event(
                conn,
                event_id=f"{turn_id}:security",
                kind="security",
                outcome=preflight.code or "prompt_blocked",
                now=now,
            )
            write_terminal(
                conn,
                turn_id=turn_id,
                event_name=TERMINAL_REFUSAL,
                code=preflight.code or "prompt_blocked",
                message=preflight.message,
                answer=None,
                citations=None,
                sources=None,
                now=now,
            )
            return {"turn_id": turn_id, "blocked": True}
        lease_seconds = _runner_deadline_seconds(settings)
        token = acquire_leases(
            conn,
            turn_id=turn_id,
            session_id=session["id"],
            ip_keys=keys,
            now=now,
            lease_seconds=lease_seconds,
            day=beijing_date(now).isoformat(),
        )
        if token is None:
            earliest = conn.execute(
                "SELECT MIN(expires_at) AS t FROM assistant_leases WHERE expires_at > ?",
                (now,),
            ).fetchone()["t"]
            retry_after = 1
            if earliest is not None:
                expires = (
                    earliest
                    if isinstance(earliest, datetime)
                    else datetime.fromisoformat(str(earliest))
                )
                retry_after = max(1, int((expires - now).total_seconds() + 0.999))
            raise limited(CODE_CONCURRENCY_LIMITED, retry_after)
        set_execution_identity(
            conn,
            turn_id=turn_id,
            fencing_epoch=int(live["fencing_epoch"]),
            fencing_token=token,
            ip_hmac=keys[0],
            operational_epoch=int(gate["operational_epoch"]),
        )
        chat_cost = _worst_chat_cost(online)
        day = beijing_date(now).isoformat()
        cap = cny_to_micro(settings.assistant_chat_daily_budget_cny)
        if not reserve_chat(conn, day=day, amount=chat_cost, cap=cap):
            retry_after = seconds_until(next_beijing_midnight(now), now) or 1
            raise limited(CODE_BUDGET_EXHAUSTED, retry_after)
        embed_cost = tokens_cost_micro(
            max(1, settings.assistant_chat_max_input_tokens or 1),
            settings.assistant_embedding_input_price_cny_per_million,
        )
        embed_cap = cny_to_micro(settings.assistant_query_embedding_daily_budget_cny)
        dense_skipped = (
            0 if reserve_query_embedding(conn, day=day, amount=embed_cost, cap=embed_cap) else 1
        )
        conn.execute(
            "UPDATE assistant_turns SET dense_skipped = ?, status = 'running' WHERE id = ?",
            (dense_skipped, turn_id),
        )
        touch_session(conn, session["id"], now, settings.assistant_session_idle_seconds)
        from .crypto import digest
        from .store import insert_attempt

        slot_cost = chat_cost // 2
        for slot in (0, 1):
            insert_attempt(
                conn,
                attempt_id=random_id(),
                turn_id=turn_id,
                kind=KIND_CHAT,
                fencing_token=token,
                request_fingerprint=digest(f"chat-slot|{slot}|{question}"),
                price_snapshot_json=snapshot_json(
                    input_cny_per_million=settings.assistant_chat_input_price_cny_per_million,
                    output_cny_per_million=settings.assistant_chat_output_price_cny_per_million,
                ),
                day=day,
                max_cost_micro=slot_cost,
                now=now,
            )
        if dense_skipped == 0:
            insert_attempt(
                conn,
                attempt_id=random_id(),
                turn_id=turn_id,
                kind=KIND_QUERY_EMBEDDING,
                fencing_token=token,
                request_fingerprint=digest(question),
                price_snapshot_json=snapshot_json(
                    input_cny_per_million=settings.assistant_embedding_input_price_cny_per_million,
                    output_cny_per_million=settings.assistant_embedding_input_price_cny_per_million,
                ),
                day=day,
                max_cost_micro=embed_cost,
                now=now,
            )
        from .total_budget import reserve_turn

        if not reserve_turn(online, conn, turn_id, admin=bool(request_scope(request))):
            raise limited(
                CODE_BUDGET_EXHAUSTED, seconds_until(next_beijing_midnight(now), now) or 1
            )
        failed_closed = enforce_session_byte_cap(conn, session["id"], now=now)
        if failed_closed:
            from .store import purge_turn_body, release_leases

            release_leases(conn, turn_id)
            write_terminal(
                conn,
                turn_id=turn_id,
                event_name="error",
                code="provider_result_unknown",
                message="The assistant could not complete this answer.",
                answer=None,
                citations=None,
                sources=None,
                now=now,
                recovery=True,
            )
            purge_turn_body(conn, turn_id, now)
        return {
            "turn_id": turn_id,
            "blocked": bool(failed_closed),
            "dense_skipped": dense_skipped,
        }

    try:
        admitted = online.control.immediate(_admit)
    except Exception as exc:
        raise exc
    if admitted.get("blocked_gate"):
        raise not_ready()
    if admitted.get("limited_retry"):
        raise limited(CODE_RATE_LIMITED, int(admitted["limited_retry"]))
    turn = online.control.read(lambda conn: get_turn(conn, admitted["turn_id"]))
    if not admitted.get("blocked"):
        from .runner import run_turn

        online.tasks[turn["id"]] = asyncio.create_task(run_turn(online, turn["id"]))
    return {"turn": turn, "cursor": cursor, "replay": False, "ip": ip}


def _runner_deadline_seconds(settings) -> int:
    provider = int(settings.assistant_provider_timeout_seconds or 30)
    grace = int(settings.assistant_runner_cleanup_grace_seconds or 5)
    return provider + (2 * provider) + grace


def _session_active(session: dict[str, Any], now: datetime) -> bool:
    idle = session["idle_expires_at"]
    absolute = session["absolute_expires_at"]
    if isinstance(idle, str):
        idle = datetime.fromisoformat(idle)
    if isinstance(absolute, str):
        absolute = datetime.fromisoformat(absolute)
    return idle > now and absolute > now


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
