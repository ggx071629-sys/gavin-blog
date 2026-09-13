from __future__ import annotations

import asyncio
import threading
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from app.assistant.cleanup import sweep
from app.assistant.constants import CODE_PROVIDER_UNKNOWN
from app.assistant.identity import identity_from_turn

from .test_assistant_online import (
    _create_session,
    _online_client,
    _publish_and_index,
    _sse_body,
)


async def _stop_cleanup_loop(online) -> None:
    task = online.cleanup_task
    online.cleanup_task = None
    if task is None:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


def _as_datetime(value: Any) -> datetime:
    return datetime.fromisoformat(value) if isinstance(value, str) else value


def test_expiry_waits_for_saver_and_fences_old_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _online_client(tmp_path, assistant_chat_max_input_tokens=4000) as client:
        _publish_and_index(client)
        csrf = _create_session(client)
        online = client.app.state.assistant
        client.portal.call(_stop_cleanup_loop, online)

        saver_entered = threading.Event()
        release_saver = threading.Event()
        lock_attempted = threading.Event()
        sweep_done = threading.Event()
        captured: dict[str, Any] = {}
        delegate_calls = 0
        original_aput = online.saver.delegate.aput

        async def paused_aput(*args, **kwargs):
            nonlocal delegate_calls
            delegate_calls += 1
            if delegate_calls == 1:
                captured["args"] = args
                captured["kwargs"] = kwargs
                saver_entered.set()
                released = await asyncio.to_thread(release_saver.wait, 10)
                if not released:
                    raise TimeoutError("test did not release Saver barrier")
            return await original_aput(*args, **kwargs)

        monkeypatch.setattr(online.saver.delegate, "aput", paused_aput)
        ask_result: dict[str, object] = {}

        def _ask() -> None:
            ask_result["response"] = _sse_body(
                client,
                csrf,
                "Which published notes cover FastAPI?",
                idem="expiry-saver-fence-0001",
            )

        ask_thread = threading.Thread(target=_ask, daemon=True)
        ask_thread.start()
        assert saver_entered.wait(10)

        turn = online.control.read(
            lambda conn: dict(conn.execute("SELECT * FROM assistant_turns").fetchone())
        )
        identity = identity_from_turn(turn)
        assert identity is not None
        session = online.control.read(
            lambda conn: dict(
                conn.execute(
                    "SELECT * FROM assistant_sessions WHERE id = ?",
                    (identity.session_id,),
                ).fetchone()
            )
        )
        initial_epoch = int(session["fencing_epoch"])
        expires_at = min(
            _as_datetime(session["idle_expires_at"]),
            _as_datetime(session["absolute_expires_at"]),
        )
        online.clock = lambda: expires_at + timedelta(seconds=1)

        original_hold = online.serialization.hold

        @asynccontextmanager
        async def observed_hold(session_id: str):
            if session_id == identity.session_id:
                lock_attempted.set()
            async with original_hold(session_id):
                yield

        monkeypatch.setattr(online.serialization, "hold", observed_hold)
        sweep_errors: list[BaseException] = []

        def _run_sweep() -> None:
            try:
                client.portal.call(sweep, online)
            except BaseException as exc:  # pragma: no cover - surfaced by assertion below
                sweep_errors.append(exc)
            finally:
                sweep_done.set()

        sweep_thread = threading.Thread(target=_run_sweep, daemon=True)
        sweep_thread.start()
        try:
            assert lock_attempted.wait(10)
            assert not sweep_done.is_set()
            blocked = online.control.read(
                lambda conn: (
                    dict(
                        conn.execute(
                            "SELECT tombstoned_at, fencing_epoch FROM assistant_sessions "
                            "WHERE id = ?",
                            (identity.session_id,),
                        ).fetchone()
                    ),
                    dict(
                        conn.execute(
                            "SELECT status FROM assistant_turns WHERE id = ?",
                            (identity.turn_id,),
                        ).fetchone()
                    ),
                    conn.execute(
                        "SELECT COUNT(*) FROM assistant_leases WHERE owner_turn_id = ?",
                        (identity.turn_id,),
                    ).fetchone()[0],
                )
            )
            blocked_session, blocked_turn, blocked_leases = blocked
            assert blocked_session["tombstoned_at"] is None
            assert int(blocked_session["fencing_epoch"]) == initial_epoch
            assert blocked_turn["status"] in {"accepted", "running"}
            assert int(blocked_leases) == 3
        finally:
            release_saver.set()

        assert sweep_done.wait(10)
        sweep_thread.join(timeout=10)
        ask_thread.join(timeout=10)
        assert not sweep_thread.is_alive()
        assert not ask_thread.is_alive()
        assert not sweep_errors

        final = online.control.read(
            lambda conn: (
                dict(
                    conn.execute(
                        "SELECT tombstoned_at, fencing_epoch FROM assistant_sessions WHERE id = ?",
                        (identity.session_id,),
                    ).fetchone()
                ),
                dict(
                    conn.execute(
                        "SELECT status, terminal_code FROM assistant_turns WHERE id = ?",
                        (identity.turn_id,),
                    ).fetchone()
                ),
                conn.execute(
                    "SELECT COUNT(*) FROM assistant_leases WHERE owner_turn_id = ?",
                    (identity.turn_id,),
                ).fetchone()[0],
            )
        )
        final_session, final_turn, final_leases = final
        assert final_session["tombstoned_at"] is not None
        assert int(final_session["fencing_epoch"]) == initial_epoch + 1
        assert final_turn == {"status": "terminal", "terminal_code": CODE_PROVIDER_UNKNOWN}
        assert int(final_leases) == 0
        assert delegate_calls == 1

        online.saver.bind(identity)

        async def _write_with_old_identity() -> None:
            await online.saver.aput(*captured["args"], **captured["kwargs"])

        try:
            with pytest.raises(PermissionError, match="checkpoint write fence rejected"):
                client.portal.call(_write_with_old_identity)
        finally:
            online.saver.unbind(identity)
        assert delegate_calls == 1
