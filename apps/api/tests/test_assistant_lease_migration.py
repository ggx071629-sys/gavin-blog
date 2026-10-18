import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from alembic import command

from app.assistant.provisioning import provision_runtime, runtime_alembic_config, setup_saver_schema
from app.assistant.store import acquire_leases, release_leases
from app.time_utils import utc_now

from .test_assistant_online import _settings


def test_lease_migration_preserves_ledger_saver_and_admits_contract_capacity(tmp_path):
    settings = _settings(tmp_path)
    path = tmp_path / "assistant_runtime.db"
    settings.assistant_runtime_path = str(path)
    command.upgrade(runtime_alembic_config(path), "20260829_rt0003")
    asyncio.run(setup_saver_schema(path))
    now = utc_now()
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        acquire_leases(
            conn,
            turn_id="one",
            session_id="s1",
            ip_keys=["ip1"],
            now=now,
            lease_seconds=120,
            day="2026-09-06",
        )
        conn.execute(
            "INSERT INTO assistant_chat_budgets"
            "(beijing_date,reserved_micro,settled_micro,circuit_open) "
            "VALUES ('2026-09-06',12,345,0)"
        )
        conn.execute(
            "INSERT INTO checkpoints"
            "(thread_id,checkpoint_ns,checkpoint_id,type,checkpoint,metadata) "
            "VALUES ('t','','1','json',?,?)",
            (b"{}", b"{}"),
        )
    provision_runtime(settings)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        assert tuple(
            conn.execute(
                "SELECT reserved_micro,settled_micro FROM assistant_chat_budgets"
            ).fetchone()
        ) == (12, 345)
        assert conn.execute("SELECT checkpoint FROM checkpoints").fetchone()[0] == b"{}"
        assert conn.execute("SELECT COUNT(*) FROM assistant_leases").fetchone()[0] == 3

        def take(turn, session, ip):
            return acquire_leases(
                conn,
                turn_id=turn,
                session_id=session,
                ip_keys=[ip],
                now=now,
                lease_seconds=120,
                day="2026-09-06",
            )

        assert take("two", "s2", "ip1")
        assert take("ip-full", "s3", "ip1") is None
        assert take("same-session", "s1", "ip2") is None
        assert take("three", "s3", "ip2")
        assert take("global-full", "s4", "ip3") is None
        release_leases(conn, "two")
        assert take("replacement", "s4", "ip1")
        assert (
            conn.execute("SELECT COUNT(*) FROM assistant_leases WHERE scope='global'").fetchone()[0]
            == 3
        )
    # Downgrade must never discard active leases to satisfy the old constraint.
    with pytest.raises(RuntimeError, match="active leases"):
        command.downgrade(runtime_alembic_config(path), "20260829_rt0003")


def test_concurrent_graphs_finish_without_blocking_control_on_saver_transaction(tmp_path):
    from .test_assistant_deepseek import _model
    from .test_assistant_online import _create_session, _headers, _online_client, _publish_and_index

    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        online = client.app.state.assistant
        online.chat, requests = _model()
        sessions = []
        for _ in range(2):
            client.cookies.clear()
            csrf = _create_session(client)
            sessions.append((csrf, "; ".join(f"{k}={v}" for k, v in client.cookies.items())))

        async def saver_write_then_control():
            # Reproduce the write/await/control ordering without a paid provider.
            await online.saver_conn.execute("DELETE FROM writes WHERE thread_id = ?", ("absent",))
            online.control.immediate(lambda conn: conn.execute("SELECT 1"), retries=1)
            await online.saver_conn.commit()

        client.portal.call(saver_write_then_control)

        def ask(index):
            csrf, cookie = sessions[index]
            response = client.post(
                "/api/v1/assistant/questions",
                json={"question": "FastAPI"},
                headers={**_headers(csrf, idem=f"concurrent-graph-{index}"), "Cookie": cookie},
            )
            return response.status_code, response.text

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(ask, i) for i in range(2)]
            results = [f.result(timeout=15) for f in futures]
        assert all(status == 200 and "event: answer" in body for status, body in results)
        assert len(requests) == 2
        assert (
            online.control.read(
                lambda conn: conn.execute("SELECT COUNT(*) FROM assistant_leases").fetchone()[0]
            )
            == 0
        )
