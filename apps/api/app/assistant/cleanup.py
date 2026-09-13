from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import timedelta
from pathlib import Path

from .constants import (
    ATTEMPT_FAILED,
    ATTEMPT_UNKNOWN,
    BODY_RETENTION_SECONDS,
    CLEANUP_SWEEP_SECONDS,
    CODE_PROVIDER_UNKNOWN,
    GENERIC_ERROR_MESSAGE,
    RATE_EVENT_GRACE_MINUTES,
    TERMINAL_ERROR,
)
from .store import (
    acquire_leases,
    get_session,
    get_turn,
    next_cleanup_deadline,
    open_cleanup_breaker,
    purge_billing_tombstones,
    purge_turn_body,
    release_leases,
    session_is_live,
    set_execution_identity,
    settle_attempt,
    tombstone_session,
    write_terminal,
)
from .time_beijing import beijing_date

logger = logging.getLogger("gavin.assistant")


class CleanupError(RuntimeError):
    """WAL truncate or purge SLA failure."""


async def recover_inflight(online) -> None:
    now = online.now()

    def _recover(conn):
        resume: list[str] = []
        rows = conn.execute(
            "SELECT * FROM assistant_attempts WHERE status IN ('prepared', 'sending')"
        ).fetchall()
        sending_turns: set[str] = set()
        for row in rows:
            attempt = {key: row[key] for key in row.keys()}
            turn = get_turn(conn, attempt["turn_id"])
            session = get_session(conn, turn["session_id"]) if turn else None
            live = False
            if session is not None and session["tombstoned_at"] is None:
                idle = session["idle_expires_at"]
                absolute = session["absolute_expires_at"]
                if isinstance(idle, str):
                    from datetime import datetime

                    idle = datetime.fromisoformat(idle)
                if isinstance(absolute, str):
                    from datetime import datetime

                    absolute = datetime.fromisoformat(absolute)
                live = idle > now and absolute > now
            if attempt["status"] == "prepared":
                if not live or not turn or turn["status"] not in {"accepted", "running"}:
                    settle_attempt(
                        conn,
                        attempt=attempt,
                        status=ATTEMPT_FAILED,
                        settled_micro=0,
                        now=now,
                    )
                continue
            settle_attempt(
                conn,
                attempt=attempt,
                status=ATTEMPT_UNKNOWN,
                settled_micro=attempt["max_cost_micro"],
                now=now,
                open_circuit=True,
            )
            write_terminal(
                conn,
                turn_id=attempt["turn_id"],
                event_name=TERMINAL_ERROR,
                code=CODE_PROVIDER_UNKNOWN,
                message=GENERIC_ERROR_MESSAGE,
                answer=None,
                citations=None,
                sources=None,
                now=now,
                recovery=True,
            )
            sending_turns.add(attempt["turn_id"])
        turns = conn.execute(
            "SELECT id, session_id FROM assistant_turns "
            "WHERE status IN ('accepted', 'running') AND preflight_blocked = 0"
        ).fetchall()
        for row in turns:
            if row["id"] in sending_turns:
                continue
            session = get_session(conn, row["session_id"])
            if session is None or not session_is_live(conn, row["session_id"], now):
                write_terminal(
                    conn,
                    turn_id=row["id"],
                    event_name=TERMINAL_ERROR,
                    code=CODE_PROVIDER_UNKNOWN,
                    message=GENERIC_ERROR_MESSAGE,
                    answer=None,
                    citations=None,
                    sources=None,
                    now=now,
                    recovery=True,
                )
                continue
            sending = conn.execute(
                "SELECT COUNT(*) AS n FROM assistant_attempts "
                "WHERE turn_id = ? AND status IN ('sending', 'unknown')",
                (row["id"],),
            ).fetchone()["n"]
            if int(sending):
                write_terminal(
                    conn,
                    turn_id=row["id"],
                    event_name=TERMINAL_ERROR,
                    code=CODE_PROVIDER_UNKNOWN,
                    message=GENERIC_ERROR_MESSAGE,
                    answer=None,
                    citations=None,
                    sources=None,
                    now=now,
                    recovery=True,
                )
                continue
            turn = get_turn(conn, row["id"])
            ip_hmac = turn.get("ip_hmac") if turn else None
            if not turn or not ip_hmac:
                write_terminal(
                    conn,
                    turn_id=row["id"],
                    event_name=TERMINAL_ERROR,
                    code=CODE_PROVIDER_UNKNOWN,
                    message=GENERIC_ERROR_MESSAGE,
                    answer=None,
                    citations=None,
                    sources=None,
                    now=now,
                    recovery=True,
                )
                continue
            release_leases(conn, row["id"])
            from .service import _runner_deadline_seconds

            token = acquire_leases(
                conn,
                turn_id=row["id"],
                session_id=row["session_id"],
                ip_keys=[str(ip_hmac)],
                now=now,
                lease_seconds=_runner_deadline_seconds(online.settings),
                day=beijing_date(now).isoformat(),
            )
            if token is None:
                write_terminal(
                    conn,
                    turn_id=row["id"],
                    event_name=TERMINAL_ERROR,
                    code=CODE_PROVIDER_UNKNOWN,
                    message=GENERIC_ERROR_MESSAGE,
                    answer=None,
                    citations=None,
                    sources=None,
                    now=now,
                    recovery=True,
                )
                continue
            set_execution_identity(
                conn,
                turn_id=row["id"],
                fencing_epoch=int(session["fencing_epoch"]),
                fencing_token=token,
                ip_hmac=str(ip_hmac),
            )
            conn.execute(
                "UPDATE assistant_attempts SET fencing_token = ?, updated_at = ? "
                "WHERE turn_id = ? AND status = 'prepared'",
                (token, now, row["id"]),
            )
            resume.append(row["id"])
        return list(dict.fromkeys(resume))

    turn_ids = online.control.immediate(_recover)
    for turn_id in turn_ids:
        from .runner import resume_turn

        online.tasks[turn_id] = asyncio.create_task(resume_turn(online, turn_id))


async def start_cleanup_loop(online) -> None:
    while True:
        try:
            delay = CLEANUP_SWEEP_SECONDS
            deadline = online.control.read(lambda conn: next_cleanup_deadline(conn, online.now()))
            if deadline is not None:
                remaining = (deadline - online.now()).total_seconds()
                delay = max(0.05, min(CLEANUP_SWEEP_SECONDS, remaining))
            await asyncio.sleep(delay)
            await sweep(online)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("assistant cleanup sweep failed", exc_info=False)
            try:
                online.control.immediate(
                    lambda conn: open_cleanup_breaker(conn, online.now(), "cleanup sweep failed")
                )
            except Exception:
                logger.warning("assistant cleanup breaker open failed", exc_info=True)


def _expired_session_ids(online, now) -> list[str]:
    return online.control.read(
        lambda conn: [
            str(row["id"])
            for row in conn.execute(
                """
                SELECT id FROM assistant_sessions
                WHERE tombstoned_at IS NULL
                  AND (idle_expires_at <= ? OR absolute_expires_at <= ?)
                """,
                (now, now),
            ).fetchall()
        ]
    )


def _expire_session(conn, session_id: str, now) -> list[str]:
    session = conn.execute(
        """
        SELECT id FROM assistant_sessions
        WHERE id = ? AND tombstoned_at IS NULL
          AND (idle_expires_at <= ? OR absolute_expires_at <= ?)
        """,
        (session_id, now, now),
    ).fetchone()
    if session is None:
        return []
    tombstone_session(conn, session_id, now)
    turn_ids = [
        str(row["id"])
        for row in conn.execute(
            """
            SELECT id FROM assistant_turns
            WHERE session_id = ? AND status IN ('accepted', 'running')
            """,
            (session_id,),
        ).fetchall()
    ]
    for turn_id in turn_ids:
        write_terminal(
            conn,
            turn_id=turn_id,
            event_name=TERMINAL_ERROR,
            code=CODE_PROVIDER_UNKNOWN,
            message=GENERIC_ERROR_MESSAGE,
            answer=None,
            citations=None,
            sources=None,
            now=now,
            recovery=True,
        )
        release_leases(conn, turn_id)
    return turn_ids


async def sweep(online) -> None:
    now = online.now()

    for session_id in _expired_session_ids(online, now):
        async with online.serialization.hold(session_id):
            decision_now = online.now()
            turn_ids = online.control.immediate(
                lambda conn, target=session_id, expired_at=decision_now: _expire_session(
                    conn, target, expired_at
                )
            )
            for turn_id in turn_ids:
                online.hub.close(turn_id)

    def _sweep(conn):
        stale = conn.execute(
            """
            SELECT id FROM assistant_turns
            WHERE status = 'terminal' AND terminal_at IS NOT NULL
              AND terminal_at <= ? AND body_purged_at IS NULL
            """,
            (now - timedelta(seconds=BODY_RETENTION_SECONDS),),
        ).fetchall()
        failed = False
        for row in stale:
            try:
                purge_turn_body(conn, row["id"], now)
                release_leases(conn, row["id"])
            except Exception:
                failed = True
                logger.warning(
                    "assistant turn purge failed turn_id=%s", row["id"], exc_info=True
                )
        try:
            purge_billing_tombstones(conn, now)
        except Exception:
            failed = True
            logger.warning("assistant billing tombstone purge failed", exc_info=True)
        rate_cutoff = now - timedelta(minutes=RATE_EVENT_GRACE_MINUTES + 10)
        conn.execute("DELETE FROM assistant_rate_events WHERE created_at <= ?", (rate_cutoff,))
        conn.execute(
            "DELETE FROM assistant_activity_events WHERE "
            "(kind = 'feedback' AND created_at <= ?) OR "
            "((kind GLOB 'stage_*' OR kind GLOB 'diagnostic_*') AND created_at <= ?)",
            (now - timedelta(seconds=BODY_RETENTION_SECONDS), now - timedelta(days=7)),
        )
        if failed:
            open_cleanup_breaker(conn, now, "purge SLA missed")
        else:
            conn.execute(
                "UPDATE assistant_cleanup_state SET last_sweep_at = ? WHERE id = 1",
                (now,),
            )
        checkpoint_candidates = conn.execute(
            "SELECT * FROM assistant_turns WHERE body_purged_at IS NOT NULL "
            "AND thread_id IS NOT NULL AND checkpoint_deleted_at IS NULL"
        ).fetchall()
        return [{key: row[key] for key in row.keys()} for row in checkpoint_candidates], failed

    turns, failed = online.control.immediate(_sweep)
    from .identity import identity_from_turn
    from .store import clear_cleanup_retry, record_cleanup_retry

    for turn in turns:
        identity = identity_from_turn(turn)
        if identity is None:
            online.control.immediate(
                lambda conn, turn_id=turn["id"]: record_cleanup_retry(
                    conn,
                    kind="checkpoint_delete",
                    target_id=turn_id,
                    now=online.now(),
                    error="execution identity missing",
                )
            )
            failed = True
            continue
        try:
            empty = await online.saver.delete_thread(identity)
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
            failed = True
            online.control.immediate(
                lambda conn, turn_id=turn["id"], error=str(exc): record_cleanup_retry(
                    conn,
                    kind="checkpoint_delete",
                    target_id=turn_id,
                    now=online.now(),
                    error=error,
                )
            )
    copy_daily_metrics(online, now)
    if failed:
        return
    if getattr(online, "allow_wal_truncate", False):
        try:
            wal_truncate(Path(str(online.settings.assistant_runtime_path)))
        except CleanupError as exc:
            message = str(exc)[:240]
            online.control.immediate(
                lambda conn, error=message: record_cleanup_retry(
                    conn,
                    kind="wal_truncate",
                    target_id="global",
                    now=online.now(),
                    error=error,
                )
            )


def copy_daily_metrics(online, now) -> None:
    day = beijing_date(now).isoformat()

    def _read(conn):
        chat = conn.execute(
            "SELECT reserved_micro, settled_micro FROM assistant_chat_budgets "
            "WHERE beijing_date = ?",
            (day,),
        ).fetchone()
        query = conn.execute(
            "SELECT reserved_micro, settled_micro FROM assistant_query_embedding_budgets "
            "WHERE beijing_date = ?",
            (day,),
        ).fetchone()
        turns = conn.execute(
            "SELECT COUNT(*) AS n FROM assistant_turns WHERE status = 'terminal'"
        ).fetchone()["n"]
        return chat, query, int(turns)

    try:
        chat, query, turns = online.control.read(_read)
    except Exception:
        logger.debug("assistant daily metrics source read failed", exc_info=True)
        return
    try:
        from ..models import AssistantDailyMetric

        db = online.content_session()
        try:
            row = db.get(AssistantDailyMetric, day)
            if row is None:
                row = AssistantDailyMetric(beijing_date=day)
                db.add(row)
            row.chat_turns = turns
            row.chat_reserved_micro_cny = int(chat["reserved_micro"]) if chat else 0
            row.chat_settled_micro_cny = int(chat["settled_micro"]) if chat else 0
            row.query_embedding_micro_cny = int(query["settled_micro"]) if query else 0
            row.copied_at = now
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.warning("assistant daily metric copy skipped", exc_info=False)


def wal_truncate(runtime_path: Path, online=None) -> None:
    if online is not None:

        def _busy(conn):
            leases = conn.execute("SELECT COUNT(*) AS n FROM assistant_leases").fetchone()["n"]
            running = conn.execute(
                "SELECT COUNT(*) AS n FROM assistant_turns "
                "WHERE status IN ('accepted', 'running')"
            ).fetchone()["n"]
            return int(leases) + int(running)

        if online.control.read(_busy):
            raise CleanupError("active readers or writers present")
    conn = sqlite3.connect(runtime_path.as_posix(), timeout=1)
    try:
        row = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        busy, log, checkpointed = int(row[0]), int(row[1]), int(row[2])
        if busy:
            raise CleanupError("SQLITE_BUSY")
        if log != 0 and log != checkpointed:
            raise CleanupError("wal frames remain")
        remaining = conn.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone()
        if remaining is not None and int(remaining[1]) != 0:
            raise CleanupError("wal frames remain")
    except sqlite3.OperationalError as exc:
        raise CleanupError(str(exc)) from exc
    finally:
        conn.close()
