from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from sqlalchemy import select, text

from app.assistant.admin_scope import admin_epoch, scope_permitted
from app.assistant.total_budget import reserve, settle, view
from app.models import AssistantBudgetReservation

from .conftest import login
from .test_assistant_online import ORIGIN, _online_client, _publish_and_index


@pytest.mark.parametrize("defect", [
    "none", "incremental", "version", "chunk", "fts", "fts_duplicate", "body",
    "no_success", "offline", "delete",
])
def test_sync_attention_uses_current_index_and_preserves_failed_history(
    tmp_path, monkeypatch, defect,
):
    from app.assistant.admin_operations import build_snapshot
    from app.assistant_index.projector import project_source
    from app.models import AssistantChunk, AssistantIndexCommand, AssistantIndexTask

    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        online = client.app.state.assistant
        login(client)
        with online.content_session() as db:
            chunk = db.scalar(select(AssistantChunk).where(
                AssistantChunk.generation_id == online.active_generation().id,
                AssistantChunk.source_type == "article",
            ))
            document = project_source(db, "article", chunk.source_id)
            failure = AssistantIndexTask(
                source_type="article", source_id=chunk.source_id,
                target_version="old-version", pipeline_version=document.pipeline_version,
                operation="delete" if defect == "delete" else "upsert", status="failed",
                provider_state="unknown", safe_error_code="provider_result_unknown",
            )
            db.add(failure)
            db.flush()
            failed_id = failure.id
            if defect == "version":
                chunk.source_version = "stale-version"
            elif defect == "body":
                chunk.page_content = "incomplete body"
            elif defect == "chunk":
                db.delete(chunk)
            elif defect == "fts":
                db.execute(text("DELETE FROM assistant_chunk_fts WHERE generation_id=:g"),
                           {"g": chunk.generation_id})
            elif defect == "fts_duplicate":
                db.execute(text("INSERT INTO assistant_chunk_fts SELECT * FROM assistant_chunk_fts "
                                "WHERE generation_id=:g"), {"g": chunk.generation_id})
            elif defect in {"no_success", "incremental"}:
                for command in db.scalars(select(AssistantIndexCommand)):
                    command.status = "failed"
                for task in db.scalars(select(AssistantIndexTask).where(
                    AssistantIndexTask.status == "succeeded",
                )):
                    task.status = "pending"
                if defect == "incremental":
                    db.add(AssistantIndexTask(
                        source_type="article", source_id=chunk.source_id,
                        target_version=document.source_version,
                        pipeline_version=document.pipeline_version,
                        operation="upsert", status="succeeded", provider_state="succeeded",
                    ))
            db.commit()
        provider_reads = []

        def forbidden(*args, **kwargs):
            provider_reads.append(1)
            raise AssertionError("passive snapshot must not access providers")

        monkeypatch.setattr(online.index_runtime.store, "collection_exists", forbidden)
        monkeypatch.setattr(online.index_runtime.store.client, "scroll", forbidden)
        monkeypatch.setattr(online.embeddings, "embed_query_metered", forbidden)
        monkeypatch.setattr(online.embeddings, "embed_documents", forbidden)
        if defect == "offline":
            with online.content_session() as db:
                snapshot = build_snapshot(settings=online.settings, online=None, db=db,
                                          launcher_source="web_runtime_config")
            assert snapshot.queue.failed == 1
        else:
            snapshot = client.get("/api/v1/admin/assistant").json()
            assert snapshot["queue"]["failed"] == (0 if defect in {"none", "incremental"} else 1)
        history = client.get("/api/v1/admin/assistant/sync?status=failed&limit=10").json()
        row = next(item for item in history["items"] if item["id"] == failed_id)
        assert row["status"] == "failed" and row["provider_state"] == "unknown"
        assert row["safe_error_code"] == "provider_result_unknown"
        assert row["resolved_by_current_index"] is (defect in {"none", "incremental", "offline"})
        assert history["total"] == 1
        assert provider_reads == []
        with online.content_session() as db:
            task = db.get(AssistantIndexTask, failed_id)
            assert task.status == "failed" and task.provider_state == "unknown"


@pytest.mark.parametrize(
    "defect", ["none", "fts", "probe", "cleanup", "restore", "switch", "nonlocal", "csrf"],
)
def test_trial_revalidates_local_generation_without_reopening_public(tmp_path, monkeypatch, defect):
    from app.assistant import development
    from app.assistant.admin_operations import finalize_rebuild
    from app.assistant.readiness import verify_receipt
    from app.assistant.store import current_receipt
    from app.assistant_index.worker import rebuild_generation
    from app.models import AssistantIndexCommand

    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        online = client.app.state.assistant
        csrf = login(client)
        headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf}
        old_receipt = online.control.read(current_receipt)["id"]
        generation = rebuild_generation(online.index_runtime)
        with online.content_session() as db:
            command = db.scalar(select(AssistantIndexCommand).where(
                AssistantIndexCommand.generation_id == generation,
            ))
            operation_id, version = command.id, command.version
        finalize_rebuild(online, operation_id=operation_id, expected_version=version,
                         idempotency_key="trial-revalidation-switch")
        # The deterministic fixture supplies no real providers. Retain the real
        # integrity, receipt signing/binding, route and maintenance checks.
        monkeypatch.setattr(development, "validate_real_development_settings", lambda s: None)
        probes = []

        def validate_probe(*args):
            probes.append(1)
            if defect == "probe":
                raise ValueError("private-invalid-probe-detail")

        monkeypatch.setattr(
            "app.assistant_qualification.provider_probe.validate_local_chat_probe_artifact",
            validate_probe,
        )
        if defect != "nonlocal":
            def revalidate():
                try:
                    development.revalidate_local_readiness(
                        online, tmp_path / "probe.json", content_fence_held=True,
                    )
                except Exception as exc:
                    if defect == "none":
                        raise AssertionError(repr(exc.__cause__)) from exc
                    raise
            client.app.state.assistant_local_revalidate = revalidate
        if defect == "fts":
            with online.content_session() as db:
                db.execute(text("DELETE FROM assistant_chunk_fts WHERE generation_id=:g"),
                           {"g": generation})
                db.commit()
        if defect == "cleanup":
            monkeypatch.setattr("app.assistant.store.breaker_open", lambda conn: True)
        if defect == "restore":
            from datetime import timedelta
            monkeypatch.setattr("app.assistant.recovery.online_lock_until",
                                lambda conn: online.now() + timedelta(days=1))
        if defect == "switch":
            online.control.immediate(lambda conn: conn.execute(
                "UPDATE assistant_operational_gate SET switch_pending_operation_id='pending'"
            ))
        if defect == "csrf":
            headers.pop("X-CSRF-Token")
        attempts = online.control.read(lambda conn: conn.execute(
            "SELECT count(*) FROM assistant_attempts"
        ).fetchone()[0])
        response = client.post("/api/v1/admin/assistant/trial/resume", headers=headers)
        assert online.control.read(lambda conn: conn.execute(
            "SELECT count(*) FROM assistant_attempts"
        ).fetchone()[0]) == attempts
        assert "private-invalid-probe-detail" not in response.text
        if defect == "none":
            assert response.status_code == 200, response.text
            assert online.control.read(current_receipt)["id"] != old_receipt
            online.control.read(lambda conn: verify_receipt(
                online.settings, conn, online.active_generation(),
            ))
            assert client.get("/api/v1/admin/assistant/management").json()["trial_available"]
            created = client.post("/api/v1/admin/assistant/trial/sessions", headers=headers)
            assert created.status_code == 200
        else:
            assert response.status_code in (403, 503), response.text
            assert online.control.read(current_receipt)["id"] == old_receipt
            from app.assistant.admin_scope import admin_stopped
            assert online.control.read(admin_stopped)
        assert client.get("/api/v1/assistant/availability").json() == {"available": False}
        if defect in ("cleanup", "restore", "switch", "nonlocal", "csrf"):
            assert not probes


@pytest.mark.parametrize("enabled", [False, True])
def test_real_restart_preserves_operator_states(tmp_path, monkeypatch, enabled):
    import asyncio
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    from app.assistant import development
    from app.assistant.admin_operations import update_availability
    from app.assistant.admin_scope import admin_stopped
    from app.assistant.operational import gate_row

    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        online = client.app.state.assistant
        if not enabled:
            update_availability(online, enabled=False, expected_version=0)
        before = online.control.read(gate_row)
        stopped = online.control.read(admin_stopped)
        generation = online.active_generation().id
        monkeypatch.setattr(development, "validate_real_development_settings", lambda s: None)
        monkeypatch.setattr(development, "revalidate_local_readiness", lambda *args: None)
        monkeypatch.setattr("app.local_embedding.client.E5Embeddings", type(online.embeddings))

        @asynccontextmanager
        async def original(app):
            yield

        app = SimpleNamespace(router=SimpleNamespace(lifespan_context=original),
                              state=SimpleNamespace(assistant=online))
        development.attach_real_development_lifespan(app, online.settings, tmp_path / "probe.json")

        async def restart():
            for _ in range(2):
                async with app.router.lifespan_context(app):
                    assert online.control.read(gate_row) == before
                    assert callable(app.state.assistant_local_revalidate)
                assert not hasattr(app.state, "assistant_local_revalidate")
                assert online.control.read(gate_row) == before
                assert online.control.read(admin_stopped) == stopped
                assert online.active_generation().id == generation

        asyncio.run(restart())


def test_index_budget_defers_paid_batch_but_deletion_still_completes(tmp_path):
    from app.assistant_index.index_ledger import (
        DeferredIndexEmbeddingError,
        LedgeredIndexEmbeddings,
    )
    from app.assistant_index.worker import process_once
    from app.models import Article, AssistantIndexEmbeddingAttempt, AssistantIndexTask

    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        csrf = login(client)
        headers = {"X-CSRF-Token": csrf}
        online = client.app.state.assistant
        current = client.get("/api/v1/admin/assistant/management").json()["budget"]
        saved = client.patch(
            "/api/v1/admin/assistant/budget",
            headers=headers,
            json={"cap_micro_cny": 0, "expected_version": current["version"]},
        )
        assert saved.status_code == 200
        with online.content_session() as db:
            count = len(db.scalars(select(AssistantIndexEmbeddingAttempt)).all())
            with pytest.raises(DeferredIndexEmbeddingError):
                LedgeredIndexEmbeddings(
                    online.embeddings, online.index_runtime, db, generation_id=9876
                ).embed_documents(["a new paid batch"])
            db.rollback()
            article_id = db.scalar(select(Article.id).where(Article.slug == "python-notes"))
        assert (
            client.delete(f"/api/v1/admin/articles/{article_id}", headers=headers).status_code
            == 204
        )
        assert process_once(online.index_runtime)
        with online.content_session() as db:
            task = db.scalar(
                select(AssistantIndexTask)
                .where(
                    AssistantIndexTask.source_id == article_id,
                    AssistantIndexTask.operation == "delete",
                )
                .order_by(AssistantIndexTask.id.desc())
            )
            assert task.status == "succeeded"
            assert len(db.scalars(select(AssistantIndexEmbeddingAttempt)).all()) == count


def test_admin_trial_closed_public_isolated_authenticated_and_emergency_stopped(tmp_path):
    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        assert client.post("/api/v1/admin/assistant/trial/sessions").status_code == 403
        csrf = login(client)
        headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf}
        # Finalize stops both scopes; resume after the new readiness receipt.
        assert (
            client.post("/api/v1/admin/assistant/trial/resume", headers=headers).status_code == 200
        )
        assert (
            client.patch(
                "/api/v1/admin/assistant/availability",
                json={"enabled": False, "expected_version": 0},
                headers=headers,
            ).status_code
            == 200
        )
        assert client.get("/api/v1/assistant/availability").json() == {"available": False}
        created = client.post("/api/v1/admin/assistant/trial/sessions", headers=headers)
        assert created.status_code == 200, created.text
        assert created.json()["session_id"].startswith("admin_")
        assert not client.cookies.get("gavin_assistant_session")
        headers["X-Assistant-CSRF"] = created.json()["csrf_token"]
        headers["Idempotency-Key"] = "admin-trial-question-0001"
        answer = client.post(
            "/api/v1/admin/assistant/trial/questions",
            json={"question": "What does Gavin write about FastAPI?"},
            headers=headers,
        )
        assert answer.status_code == 200, answer.text
        assert "event: answer" in answer.text, answer.text
        assert '"excerpt":' in answer.text
        assert '"supports"' not in answer.text and '"quote"' not in answer.text
        restored = client.get("/api/v1/admin/assistant/trial/session", headers=headers)
        assert restored.status_code == 200, restored.text
        assert '"supports"' not in restored.text and '"quote"' not in restored.text
        assert restored.json()["turns"][0]["cost_micro_cny"] > 0
        assert "feedback" not in restored.json()["turns"][0]
        assert restored.json()["turns"][0]["citations"][0]["excerpt"]
        management = client.get("/api/v1/admin/assistant/management").json()
        assert management["trial_available"] is True
        assert any(
            row["scope"] == "admin" and row["settled_micro_cny"] > 0
            for row in management["scope_costs"]
        )
        assert client.post("/api/v1/assistant/sessions", headers=headers).status_code == 503
        online = client.app.state.assistant
        epoch = online.control.read(admin_epoch)
        assert (
            client.post("/api/v1/admin/assistant/emergency-stop", headers=headers).status_code
            == 200
        )
        assert not online.control.read(
            lambda conn: scope_permitted(
                conn,
                {
                    "switch_pending_operation_id": None,
                    "effective_state": "disabled",
                    "operational_epoch": 1,
                },
                created.json()["session_id"],
                epoch,
            )
        )
        headers["Idempotency-Key"] = "admin-trial-question-0002"
        assert (
            client.post(
                "/api/v1/admin/assistant/trial/questions",
                json={"question": "What does Gavin write?"},
                headers=headers,
            ).status_code
            == 503
        )
        assert client.delete(
            "/api/v1/admin/assistant/trial/session", headers=headers
        ).status_code in {202, 204}
        client.cookies.delete("gavin_session")
        assert (
            client.get("/api/v1/admin/assistant/trial/session", headers=headers).status_code == 401
        )


def test_budget_edit_conflict_zero_and_deployment_ceiling(tmp_path):
    with _online_client(tmp_path) as client:
        csrf = login(client)
        url = "/api/v1/admin/assistant/budget"
        initial = client.get("/api/v1/admin/assistant/management").json()["budget"]
        headers = {"X-CSRF-Token": csrf}
        assert (
            client.patch(url, json={"cap_micro_cny": 0, "expected_version": 0}).status_code == 403
        )
        saved = client.patch(
            url, json={"cap_micro_cny": 0, "expected_version": initial["version"]}, headers=headers
        )
        assert saved.status_code == 200, saved.text
        assert client.get("/api/v1/assistant/availability").json() == {"available": False}
        assert (
            client.patch(
                url,
                json={"cap_micro_cny": 1, "expected_version": initial["version"]},
                headers=headers,
            ).status_code
            == 409
        )
        assert (
            client.patch(
                url,
                json={
                    "cap_micro_cny": initial["ceiling_micro_cny"] + 1,
                    "expected_version": saved.json()["version"],
                },
                headers=headers,
            ).status_code
            == 400
        )
        raised = client.patch(
            url,
            json={"cap_micro_cny": 100000, "expected_version": saved.json()["version"]},
            headers=headers,
        )
        assert raised.status_code == 200, raised.text
        assert (
            client.patch(
                url, json={"cap_micro_cny": 1.2, "expected_version": 2}, headers=headers
            ).status_code
            == 400
        )


def test_atomic_shared_budget_question_priority_and_monotonic_settlement(tmp_path):
    with _online_client(
        tmp_path,
        assistant_chat_daily_budget_cny=Decimal("1"),
        assistant_query_embedding_daily_budget_cny=Decimal("1"),
        assistant_index_embedding_daily_budget_cny=Decimal("1"),
    ) as client:
        online = client.app.state.assistant
        day = online.beijing_day()

        def attempt(index):
            with online.content_session() as db:
                db.execute(text("BEGIN IMMEDIATE"))
                ok = reserve(
                    db,
                    online.settings,
                    day=day,
                    entries=[
                        {
                            "id": f"race:{index}",
                            "kind": "chat" if index else "index_embedding",
                            "scope": "public" if index else "index",
                            "reserved_micro_cny": 600000,
                        }
                    ],
                )
                db.commit()
                return ok

        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(attempt, (0, 1))) == [False, True]
        with online.content_session() as db:
            db.execute(text("BEGIN IMMEDIATE"))
            assert not reserve(
                db,
                online.settings,
                day=day,
                headroom=100000,
                entries=[
                    {
                        "id": "index-headroom",
                        "kind": "index_embedding",
                        "scope": "index",
                        "reserved_micro_cny": 350000,
                    }
                ],
            )
            assert reserve(
                db,
                online.settings,
                day=day,
                entries=[
                    {
                        "id": "question",
                        "kind": "chat",
                        "scope": "public",
                        "reserved_micro_cny": 350000,
                    }
                ],
            )
            settle(db, "question", 50000)
            settle(db, "question", 10000)
            db.commit()
            assert db.get(AssistantBudgetReservation, "question").settled_micro_cny == 50000
            assert view(db, online.settings, day)["reserved_micro_cny"] == 600000
            assert len(db.scalars(select(AssistantBudgetReservation)).all()) == 2


def test_sync_is_bounded_and_public_availability_is_passive(tmp_path):
    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        login(client)
        online = client.app.state.assistant
        before = online.control.read(
            lambda conn: conn.execute("SELECT COUNT(*) FROM assistant_sessions").fetchone()[0]
        )
        for _ in range(2):
            availability = client.get("/api/v1/assistant/availability")
            assert availability.json() == {"available": True}
            assert availability.headers["cache-control"] == "no-store"
        assert (
            online.control.read(
                lambda conn: conn.execute("SELECT COUNT(*) FROM assistant_sessions").fetchone()[0]
            )
            == before
        )
        tasks = client.get("/api/v1/admin/assistant/sync?limit=1&offset=0").json()
        assert len(tasks["items"]) == 1
        assert tasks["total"] >= 1
        assert tasks["items"][0]["title"]
        assert "current_revision" in tasks["items"][0]
        assert client.get("/api/v1/admin/assistant/sync?limit=51").status_code == 400
        online.control.immediate(lambda conn: conn.execute(
            "INSERT OR REPLACE INTO assistant_chat_budgets "
            "(beijing_date, settled_micro, reserved_micro, circuit_open) VALUES (?, 0, 0, 1)",
            (online.beijing_day(),),
        ))
        assert client.get("/api/v1/assistant/availability").json() == {"available": False}
        online.control.immediate(lambda conn: conn.execute(
            "UPDATE assistant_chat_budgets SET circuit_open = 0, settled_micro = ? "
            "WHERE beijing_date = ?", (
                int(online.settings.assistant_chat_daily_budget_cny * 1000000),
                online.beijing_day(),
            ),
        ))
        assert client.get("/api/v1/assistant/availability").json() == {"available": False}
