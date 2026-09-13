from __future__ import annotations

import asyncio
import logging

from .constants import (
    ATTEMPT_SENDING,
    ATTEMPT_UNKNOWN,
    CODE_PROVIDER_UNKNOWN,
    GENERIC_ERROR_MESSAGE,
    HEARTBEAT_SECONDS,
    TERMINAL_ERROR,
)
from .identity import identity_from_turn
from .store import (
    clear_cleanup_retry,
    get_session,
    get_turn,
    heartbeat_leases,
    record_cleanup_retry,
    release_leases,
    settle_attempt,
    write_terminal,
)

logger = logging.getLogger("gavin.assistant")


async def run_turn(online, turn_id: str, *, resume: bool = False) -> None:
    turn = online.control.immediate(lambda conn: get_turn(conn, turn_id))
    if turn is None:
        return
    identity = identity_from_turn(turn)
    if identity is None:
        return
    config = {
        "configurable": {
            "thread_id": identity.thread_id,
            "assistant_session_id": identity.session_id,
            "assistant_turn_id": identity.turn_id,
            "assistant_fencing_epoch": identity.fencing_epoch,
            "assistant_fencing_token": identity.fencing_token,
            "assistant_operational_epoch": identity.operational_epoch,
        },
        "durability": "sync",
    }
    payload = (
        None
        if resume
        else {
            **identity.as_state(),
            "question": turn["question"],
            "current_path": turn["current_path"],
            "dense_skipped": bool(turn["dense_skipped"]),
            "reservation_micro": _chat_reservation(online, turn_id),
            "query_attempt_id": _query_attempt(online, turn_id),
        }
    )
    token = identity.fencing_token
    online.saver.bind(identity)
    heartbeat = asyncio.create_task(_heartbeat_loop(online, turn_id, token))
    try:
        if resume:
            await online.graph.aupdate_state(config, identity.as_state())
        async for chunk in online.graph.astream(
            payload,
            config,
            stream_mode="custom",
            version="v2",
            durability="sync",
        ):
            _ = chunk
        await online.saver_conn.commit()
    except Exception as exc:
        logger.warning(
            "assistant turn failed turn_id=%s type=%s", turn_id, type(exc).__name__
        )
    finally:
        heartbeat.cancel()
        await _finish(online, turn_id)
        online.hub.close(turn_id)
        online.tasks.pop(turn_id, None)
        try:
            empty = await online.saver.delete_thread(identity)
            if not empty:
                raise RuntimeError("checkpoint rows remain after delete")

            def _mark_checkpoint_deleted(conn, turn_id=turn_id) -> None:
                conn.execute(
                    "UPDATE assistant_turns SET checkpoint_deleted_at = ? WHERE id = ?",
                    (online.now(), turn_id),
                )
                clear_cleanup_retry(conn, kind="checkpoint_delete", target_id=turn_id)

            online.control.immediate(_mark_checkpoint_deleted)
        except Exception as exc:
            logger.warning("assistant checkpoint delete failed")
            online.control.immediate(
                lambda conn, error=str(exc): record_cleanup_retry(
                    conn,
                    kind="checkpoint_delete",
                    target_id=turn_id,
                    now=online.now(),
                    error=error,
                )
            )
        finally:
            online.saver.unbind(identity)


async def resume_turn(online, turn_id: str) -> None:
    await run_turn(online, turn_id, resume=True)


async def _heartbeat_loop(online, turn_id: str, token: str) -> None:
    from .service import _runner_deadline_seconds

    while True:
        try:
            await asyncio.sleep(HEARTBEAT_SECONDS)
        except asyncio.CancelledError:
            raise
        lease_seconds = _runner_deadline_seconds(online.settings)

        def _beat(conn, hold=lease_seconds):
            turn = get_turn(conn, turn_id)
            if turn is None:
                return False
            session = get_session(conn, turn["session_id"])
            if session is None:
                return False
            return heartbeat_leases(
                conn,
                turn_id=turn_id,
                token=token,
                now=online.now(),
                lease_seconds=hold,
                absolute_expires_at=session["absolute_expires_at"],
            )

        ok = online.control.immediate(_beat)
        if not ok:
            return


async def _finish(online, turn_id: str) -> None:
    turn = online.control.read(lambda conn: get_turn(conn, turn_id))
    if turn is None:
        return
    async with online.serialization.hold(turn["session_id"]):
        def _write(conn):
            now = online.now()
            current = get_turn(conn, turn_id)
            if current is None:
                return
            attempts = conn.execute(
                "SELECT * FROM assistant_attempts WHERE turn_id = ? AND status = ?",
                (turn_id, ATTEMPT_SENDING),
            ).fetchall()
            for row in attempts:
                attempt = {key: row[key] for key in row.keys()}
                settle_attempt(
                    conn,
                    attempt=attempt,
                    status=ATTEMPT_UNKNOWN,
                    settled_micro=int(attempt["max_cost_micro"]),
                    now=now,
                    open_circuit=True,
                )
            if current["status"] in {"accepted", "running"}:
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
            conn.execute(
                "UPDATE assistant_turns SET runner_quiescent_at = ? WHERE id = ?",
                (now, turn_id),
            )
            release_leases(conn, turn_id)

        online.control.immediate(_write)


def _chat_reservation(online, turn_id: str) -> int:
    row = online.control.immediate(
        lambda conn: conn.execute(
            "SELECT max_cost_micro FROM assistant_attempts "
            "WHERE turn_id = ? AND kind = 'chat' ORDER BY created_at LIMIT 1",
            (turn_id,),
        ).fetchone()
    )
    return int(row["max_cost_micro"]) if row else 0


def _query_attempt(online, turn_id: str) -> str | None:
    row = online.control.immediate(
        lambda conn: conn.execute(
            "SELECT id FROM assistant_attempts "
            "WHERE turn_id = ? AND kind = 'query_embedding' "
            "ORDER BY created_at DESC LIMIT 1",
            (turn_id,),
        ).fetchone()
    )
    return row["id"] if row else None
