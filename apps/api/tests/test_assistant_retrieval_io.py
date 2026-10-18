from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import pytest

from .test_assistant_online import (
    ORIGIN,
    _create_session,
    _online_client,
    _publish_and_index,
    _sse_body,
)


@pytest.mark.parametrize("stage", ["embedding", "hydrate"])
def test_slow_retrieval_leaves_app_loop_and_heartbeat_responsive(
    tmp_path: Path, monkeypatch, stage: str,
) -> None:
    from app.assistant import graph, runner
    from app.assistant.cleanup import sweep

    started, release, finished, heartbeat = (threading.Event() for _ in range(4))
    result = {}
    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        csrf = _create_session(client)
        online = client.app.state.assistant
        target = online.embeddings if stage == "embedding" else graph
        name = "embed_query_metered" if stage == "embedding" else "hydrate_evidence"
        original = getattr(target, name)

        def slow(*args, **kwargs):
            started.set()
            try:
                release.wait(3)
                return original(*args, **kwargs)
            finally:
                finished.set()

        beat = runner.heartbeat_leases

        def observed_beat(*args, **kwargs):
            value = beat(*args, **kwargs)
            if started.is_set() and not finished.is_set() and value:
                heartbeat.set()
            return value

        monkeypatch.setattr(target, name, slow)
        monkeypatch.setattr(runner, "HEARTBEAT_SECONDS", 0.02)
        monkeypatch.setattr(runner, "heartbeat_leases", observed_beat)
        worker = threading.Thread(target=lambda: result.setdefault("response", _sse_body(
            client, csrf, "Which published notes cover FastAPI?", idem=f"slow-io-{stage}-0001",
        )))
        worker.start()
        try:
            assert started.wait(5)
            assert client.get("/api/v1/assistant/session").status_code == 200
            assert not finished.is_set(), "session read waited for blocking retrieval"
            assert heartbeat.wait(1), "lease heartbeat was blocked by retrieval"
            client.portal.call(sweep, online)
            assert not finished.is_set(), "cleanup waited for blocking retrieval"
            # A separate visitor can obtain a session while the first is retrieving.
            client.cookies.clear()
            _create_session(client)
            assert not finished.is_set()
        finally:
            release.set()
            worker.join(10)
        assert not worker.is_alive()
        status, body = result["response"]
        assert status == 200
        assert "event: answer" in body


def test_retrieval_executor_capacity_cancellation_and_shutdown() -> None:
    from app.assistant.retrieval_io import RetrievalIO

    async def scenario():
        pool = RetrievalIO(1)
        started, release, second_started = (threading.Event() for _ in range(3))

        def blocked():
            started.set()
            assert release.wait(5)

        first = asyncio.create_task(pool.run(blocked))
        try:
            while not started.is_set():
                await asyncio.sleep(0.001)
            first.cancel()
            with pytest.raises(asyncio.CancelledError):
                await first
            second = asyncio.create_task(pool.run(second_started.set))
            await asyncio.sleep(0.02)
            assert not second_started.is_set(), "cancellation released a live worker slot"
            second.cancel()
            with pytest.raises(asyncio.CancelledError):
                await second
            closing = asyncio.create_task(pool.aclose())
            await asyncio.sleep(0.02)
            assert not closing.done(), "shutdown abandoned a live worker"
            with pytest.raises(RuntimeError, match="closed"):
                await pool.run(lambda: None)
        finally:
            release.set()
            await pool.aclose()
        await closing
        assert not second_started.is_set(), "cancelled queued work was submitted"

    asyncio.run(scenario())


def test_runtime_shutdown_drains_retrieval_before_releasing_resources() -> None:
    from types import SimpleNamespace

    from app.assistant.retrieval_io import RetrievalIO
    from app.assistant.runtime import stop_assistant_online

    async def scenario():
        started, release = threading.Event(), threading.Event()
        closed = []
        pool = RetrievalIO(1)

        def blocked():
            started.set()
            assert release.wait(5)
            closed.append("work")

        async def close_saver():
            closed.append("saver")

        consumer = asyncio.create_task(pool.run(blocked))
        online = SimpleNamespace(
            cleanup_task=None, tasks={"turn": consumer}, retrieval_io=pool,
            saver_conn=SimpleNamespace(close=close_saver),
            control=SimpleNamespace(dispose=lambda: closed.append("control")),
            lock=SimpleNamespace(release=lambda: closed.append("lock")),
        )
        while not started.is_set():
            await asyncio.sleep(0.001)
        shutdown = asyncio.create_task(stop_assistant_online(online))
        try:
            await asyncio.sleep(0.02)
            assert consumer.cancelled()
            assert not shutdown.done() and closed == []
        finally:
            release.set()
            await shutdown
        assert closed == ["work", "saver", "control", "lock"]

    asyncio.run(scenario())


@pytest.mark.parametrize("cancel_runner", [False, True])
def test_deleted_session_drops_late_embedding_and_settles_once(
    tmp_path: Path, monkeypatch, cancel_runner: bool,
) -> None:
    started, release = threading.Event(), threading.Event()
    result = {}
    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        csrf = _create_session(client)
        online = client.app.state.assistant
        original = online.embeddings.embed_query_metered
        calls = []

        def slow(query):
            calls.append(query)
            started.set()
            assert release.wait(5)
            return original(query)

        monkeypatch.setattr(online.embeddings, "embed_query_metered", slow)
        worker = threading.Thread(target=lambda: result.setdefault("response", _sse_body(
            client, csrf, "Which published notes cover FastAPI?", idem="delete-slow-embedding-0001",
        )))
        worker.start()
        try:
            assert started.wait(5)
            deleted = client.delete("/api/v1/assistant/session", headers={
                "Origin": ORIGIN, "X-Assistant-CSRF": csrf,
            })
            assert deleted.status_code == 202
            if cancel_runner:
                async def cancel():
                    tasks = list(online.tasks.values())
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)

                client.portal.call(cancel)
        finally:
            release.set()
            worker.join(10)
        assert not worker.is_alive()
        client.portal.call(online.retrieval_io.aclose)
        assert len(calls) == 1
        assert len(online.chat.calls) == 0
        assert "event: answer" not in result["response"][1]

        def facts(conn):
            attempt = dict(conn.execute(
                "SELECT * FROM assistant_attempts WHERE kind = 'query_embedding'"
            ).fetchone())
            turn = dict(conn.execute("SELECT * FROM assistant_turns").fetchone())
            counts = [conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in (
                "assistant_event_journal", "assistant_history", "checkpoints", "writes",
            )]
            budget = conn.execute(
                "SELECT reserved_micro, settled_micro FROM assistant_query_embedding_budgets"
            ).fetchone()
            return attempt, turn, counts, tuple(budget)

        attempt, turn, counts, budget = online.control.read(facts)
        assert attempt["status"] == "unknown"
        if cancel_runner:
            assert attempt["settled_micro"] == attempt["max_cost_micro"]
        else:
            import json

            from app.assistant.money import tokens_cost_micro

            assert attempt["settled_micro"] == tokens_cost_micro(
                json.loads(attempt["usage_json"])["input_tokens"],
                online.settings.assistant_embedding_input_price_cny_per_million,
            )
        assert attempt["vector_json"] is None and attempt["parsed_json"] is None
        assert turn["question"] is None and turn["answer"] is None
        assert counts == [0, 0, 0, 0]
        assert budget == (0, attempt["settled_micro"])


def test_persistent_qdrant_can_query_from_retrieval_worker(tmp_path: Path) -> None:
    from qdrant_client import QdrantClient, models

    from app.assistant.retrieval_io import RetrievalIO

    client = QdrantClient(path=str(tmp_path / "qdrant"))
    client.create_collection("notes", vectors_config=models.VectorParams(
        size=2, distance=models.Distance.COSINE,
    ))
    client.upsert("notes", points=[models.PointStruct(id=1, vector=[1.0, 0.0])])

    async def scenario():
        pool = RetrievalIO(2)
        try:
            result = await pool.run(lambda: client.query_points("notes", query=[1.0, 0.0]))
            assert [point.id for point in result.points] == [1]
        finally:
            await pool.aclose()

    try:
        asyncio.run(scenario())
    finally:
        client.close()
