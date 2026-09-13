from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from threading import Barrier

import pytest
from sqlalchemy import func, select

from app.assistant.operational import gate_row
from app.assistant.store import reserve_chat, reserve_query_embedding, settle_budget
from app.assistant_index.index_ledger import DeferredIndexEmbeddingError, LedgeredIndexEmbeddings
from app.assistant_index.runtime import build_test_runtime
from app.assistant_index.worker import rebuild_generation
from app.models import AssistantIndexCommand, AssistantIndexEmbeddingAttempt

from .conftest import login
from .test_assistant_online import _online_client, _publish_and_index


def test_static_off_snapshot_is_authenticated_partial_and_no_store(client) -> None:
    unauthenticated = client.get("/api/v1/admin/assistant")
    assert unauthenticated.status_code == 401
    assert unauthenticated.headers["cache-control"] == "no-store"
    login(client)
    response = client.get("/api/v1/admin/assistant")
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["status"] == "partial"
    assert body["deployment"]["api_capability"] is False
    assert body["availability"]["effective_state"] == "blocked"
    assert body["manifest"]["collection_present"] is None
    assert {item["kind"] for item in body["budgets"]} == {
        "chat",
        "query_embedding",
        "index_embedding",
    }


def test_admin_contract_rejects_unknown_fields_and_gets_never_mutate(client) -> None:
    csrf = login(client)
    before = client.get("/api/v1/admin/assistant").json()
    invalid = client.patch(
        "/api/v1/admin/assistant/availability",
        json={"enabled": True, "expected_version": 0, "provider": "forbidden"},
        headers={"X-CSRF-Token": csrf},
    )
    assert invalid.status_code == 400
    assert invalid.headers["cache-control"] == "no-store"
    assert invalid.json()["error"]["code"] == "invalid_request"
    after = client.get("/api/v1/admin/assistant").json()
    assert before["availability"] == after["availability"]


def test_safety_disable_beats_stale_version_and_blocks_new_sessions(tmp_path: Path) -> None:
    with _online_client(tmp_path) as client:
        csrf = login(client)
        before = client.get("/api/v1/admin/assistant").json()["availability"]
        disabled = client.patch(
            "/api/v1/admin/assistant/availability",
            json={"enabled": False, "expected_version": max(0, before["version"] - 1)},
            headers={"X-CSRF-Token": csrf},
        )
        assert disabled.status_code == 200, disabled.text
        assert disabled.json()["effective_state"] == "disabled"
        assert disabled.json()["version"] > before["version"]
        blocked = client.post(
            "/api/v1/assistant/sessions", headers={"Origin": "http://testserver"}
        )
        assert blocked.status_code == 503


def test_rebuild_request_is_durable_and_finalize_leaves_gate_disabled(tmp_path: Path) -> None:
    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        csrf = login(client)
        online = client.app.state.assistant
        with online.database.session_factory() as db:
            provider_calls = int(
                db.scalar(select(func.count(AssistantIndexEmbeddingAttempt.id))) or 0
            )
        qdrant_collections = len(online.index_runtime.store.client.get_collections().collections)
        requested = client.post(
            "/api/v1/admin/assistant/index/rebuilds",
            json={},
            headers={
                "X-CSRF-Token": csrf,
                "Idempotency-Key": "admin-rebuild-request-0001",
            },
        )
        assert requested.status_code == 202, requested.text
        operation = requested.json()
        assert operation["status"] == "pending"
        with online.database.session_factory() as db:
            attempts_after_request = int(
                db.scalar(select(func.count(AssistantIndexEmbeddingAttempt.id))) or 0
            )
            assert attempts_after_request == provider_calls
        assert (
            len(online.index_runtime.store.client.get_collections().collections)
            == qdrant_collections
        )
        repeated = client.post(
            "/api/v1/admin/assistant/index/rebuilds",
            json={},
            headers={
                "X-CSRF-Token": csrf,
                "Idempotency-Key": "admin-rebuild-request-0001",
            },
        )
        assert repeated.status_code == 202
        assert repeated.json()["operation_id"] == operation["operation_id"]

        generation_id = rebuild_generation(online.index_runtime)
        with online.database.session_factory() as db:
            ready = db.scalar(
                select(AssistantIndexCommand).where(
                    AssistantIndexCommand.id == operation["operation_id"]
                )
            )
            assert ready is not None
            assert ready.generation_id == generation_id
            expected_version = ready.version
        finalized = client.post(
            f"/api/v1/admin/assistant/index/rebuilds/{operation['operation_id']}/finalize",
            json={"expected_version": expected_version},
            headers={
                "X-CSRF-Token": csrf,
                "Idempotency-Key": "admin-finalize-request-0001",
            },
        )
        assert finalized.status_code == 200, finalized.text
        assert finalized.json()["status"] == "switched"
        gate = online.control.read(lambda conn: gate_row(conn))
        assert gate is not None
        assert gate["effective_state"] == "disabled"
        assert gate["switch_pending_operation_id"] is None


def test_runtime_ledgers_count_settled_plus_reserved_exactly_and_serialize(tmp_path: Path) -> None:
    with _online_client(tmp_path) as client:
        online = client.app.state.assistant

        def sequential(conn) -> None:
            assert reserve_chat(conn, day="2026-08-30", amount=600, cap=1_000)
            settle_budget(
                conn, kind="chat", day="2026-08-30", reserved=600, settled=600
            )
            assert reserve_chat(conn, day="2026-08-30", amount=400, cap=1_000)
            assert not reserve_chat(conn, day="2026-08-30", amount=1, cap=1_000)
            assert reserve_query_embedding(
                conn, day="2026-08-30", amount=1_000, cap=1_000
            )
            assert not reserve_query_embedding(
                conn, day="2026-08-30", amount=1, cap=1_000
            )
            assert reserve_chat(conn, day="2026-08-31", amount=1_000, cap=1_000)

        online.control.immediate(sequential)
        barrier = Barrier(2)

        def contender(index: int) -> bool:
            barrier.wait()
            return online.control.immediate(
                lambda conn: reserve_chat(
                    conn, day="2026-09-01", amount=600 + index, cap=1_000
                )
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(contender, (0, 1)))
        assert sorted(outcomes) == [False, True]


def test_index_ledger_exact_cap_then_defers_without_second_call(client) -> None:
    settings = client.app.state.settings.model_copy(
        update={
            "assistant_embedding_provider": "test",
            "assistant_embedding_model": "deterministic-hash",
            "assistant_embedding_model_version": "test-v1",
            "assistant_embedding_dimension": 32,
            "assistant_embedding_input_price_cny_per_million": Decimal("0.10"),
            "assistant_index_embedding_daily_budget_cny": Decimal("0.000001"),
        }
    )
    runtime = build_test_runtime(settings, client.app.state.database)
    with client.app.state.database.session_factory() as db:
        first = LedgeredIndexEmbeddings(
            runtime.embeddings, runtime, db, generation_id=9001
        ).embed_documents_metered(["a"])
        assert first.input_tokens >= 0
        with pytest.raises(DeferredIndexEmbeddingError):
            LedgeredIndexEmbeddings(
                runtime.embeddings, runtime, db, generation_id=9002
            ).embed_documents_metered(["b"])
