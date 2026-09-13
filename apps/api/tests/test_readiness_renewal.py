from datetime import timedelta

import pytest
from sqlalchemy import select, text

from app.assistant.admin_operations import finalize_rebuild
from app.assistant.admin_scope import admin_stopped
from app.assistant.operational import gate_row
from app.assistant.readiness import verify_receipt
from app.assistant.store import current_receipt
from app.assistant_index.worker import rebuild_generation
from app.models import AssistantIndexCommand

from .conftest import login
from .test_assistant_online import _online_client, _publish_and_index

URL = "/api/v1/admin/assistant/readiness/renew"


def _switch(online):
    generation = rebuild_generation(online.index_runtime)
    with online.content_session() as db:
        command = db.scalar(
            select(AssistantIndexCommand).where(
                AssistantIndexCommand.generation_id == generation,
            )
        )
        operation_id, version = command.id, command.version
    finalize_rebuild(
        online,
        operation_id=operation_id,
        expected_version=version,
        idempotency_key=f"renewal-switch-{generation}",
    )
    return {
        "expected_generation_id": generation,
        "expected_version": online.control.read(gate_row)["version"],
    }


def _forbidden(*args, **kwargs):
    raise AssertionError("renewal must not call Chat or embeddings")


def test_renewal_after_each_switch_keeps_gates_stopped_and_resume_succeeds(tmp_path, monkeypatch):
    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        online = client.app.state.assistant
        headers = {"X-CSRF-Token": login(client)}
        for _ in range(2):
            body = _switch(online)
            old = online.control.read(current_receipt)
            assert (
                client.post("/api/v1/admin/assistant/trial/resume", headers=headers).status_code
                == 503
            )
            with monkeypatch.context() as patch:
                patch.setattr(type(online.chat), "_generate", _forbidden)
                patch.setattr(online.embeddings, "embed_query_metered", _forbidden)
                patch.setattr(online.embeddings, "embed_documents", _forbidden)
                response = client.post(URL, json=body, headers=headers)
            assert response.status_code == 200, response.text
            assert response.headers["cache-control"] == "no-store"
            assert response.json() == {
                "qualified": True,
                "generation_id": body["expected_generation_id"],
            }
            renewed = online.control.read(current_receipt)
            assert renewed["id"] != old["id"]
            online.control.read(
                lambda conn: verify_receipt(online.settings, conn, online.active_generation())
            )
            assert online.control.read(admin_stopped)
            assert online.control.read(gate_row)["requested_state"] == "disabled"
            assert client.post(URL, json=body, headers=headers).status_code == 200
            assert online.control.read(current_receipt)["id"] == renewed["id"]
            assert (
                client.post("/api/v1/admin/assistant/trial/resume", headers=headers).status_code
                == 200
            )
            assert online.control.read(gate_row)["requested_state"] == "disabled"


@pytest.mark.parametrize(
    "defect,code",
    [
        ("generation", "readiness_generation_changed"),
        ("version", "readiness_state_changed"),
        ("missing", "readiness_initial_required"),
        ("signature", "readiness_configuration_changed"),
        ("credential", "readiness_configuration_changed"),
        ("model", "readiness_configuration_changed"),
        ("price", "readiness_configuration_changed"),
        ("fts", "readiness_index_invalid"),
        ("vector", "readiness_index_invalid"),
        ("cleanup", "readiness_maintenance_blocked"),
        ("restore", "readiness_maintenance_blocked"),
        ("switch", "readiness_switch_pending"),
        ("running", "readiness_stop_required"),
        ("config", "readiness_configuration_invalid"),
        ("race", "readiness_state_changed"),
        ("checkpoint", "readiness_cleanup_pending"),
    ],
)
def test_renewal_fails_closed_without_replacing_receipt(tmp_path, monkeypatch, defect, code):
    from app.assistant import readiness_renewal as renewal

    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        online = client.app.state.assistant
        headers = {"X-CSRF-Token": login(client)}
        body = _switch(online)
        if defect in {"generation", "version"}:
            body["expected_generation_id" if defect == "generation" else "expected_version"] += 1
        if defect == "missing":
            online.control.immediate(
                lambda conn: conn.execute("DELETE FROM assistant_readiness_receipts")
            )
        if defect == "signature":
            online.control.immediate(
                lambda conn: conn.execute(
                    "UPDATE assistant_readiness_receipts SET receipt_hmac='invalid'"
                )
            )
        for name, field in {
            "credential": "assistant_chat_api_key",
            "model": "assistant_chat_model",
            "price": "assistant_chat_output_price_cny_per_million",
        }.items():
            if defect == name:
                value = 99 if name == "price" else "private-changed-value"
                monkeypatch.setattr(online.settings, field, value)
        if defect == "fts":
            with online.content_session() as db:
                db.execute(text("DELETE FROM assistant_chunk_fts"))
                db.commit()
        if defect == "vector":
            monkeypatch.setattr(online.index_runtime.store.client, "scroll", _forbidden)
        if defect == "cleanup":
            monkeypatch.setattr(renewal, "breaker_open", lambda conn: True)
        if defect == "restore":
            monkeypatch.setattr(
                renewal, "online_lock_until", lambda conn: online.now() + timedelta(days=1)
            )
        if defect == "switch":
            online.control.immediate(
                lambda conn: conn.execute(
                    "UPDATE assistant_operational_gate SET switch_pending_operation_id='pending'"
                )
            )
        if defect == "running":
            online.control.immediate(
                lambda conn: conn.execute(
                    "UPDATE assistant_runtime_meta SET value='0' "
                    "WHERE key='admin_execution_stopped'"
                )
            )
        if defect == "checkpoint":
            online.control.immediate(
                lambda conn: conn.execute(
                    "INSERT INTO checkpoints "
                    "(thread_id,checkpoint_ns,checkpoint_id,type,checkpoint,metadata) "
                    "VALUES ('renewal-cleanup','','1','json',?,?)",
                    (b"{}", b"{}"),
                )
            )
        if defect == "config":
            monkeypatch.setattr(type(online.settings), "validate_runtime", _forbidden)
        if defect == "race":
            audit = renewal.audit_generation

            def race(*args):
                result = audit(*args)
                online.control.immediate(
                    lambda conn: conn.execute(
                        "UPDATE assistant_operational_gate SET version=version+1"
                    )
                )
                return result

            monkeypatch.setattr(renewal, "audit_generation", race)
        before = online.control.read(current_receipt)
        response = client.post(URL, json=body, headers=headers)
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == code
        assert "private-changed-value" not in response.text
        assert online.control.read(current_receipt) == before


def test_renewal_requires_auth_csrf_and_strict_request(tmp_path):
    with _online_client(tmp_path) as client:
        assert (
            client.post(URL, json={"expected_generation_id": 1, "expected_version": 1}).status_code
            == 401
        )
        headers = {"X-CSRF-Token": login(client)}
        body = {"expected_generation_id": 1, "expected_version": 1}
        assert client.post(URL, json=body).status_code == 403
        assert (
            client.post(URL, json={**body, "skip_checks": True}, headers=headers).status_code == 400
        )
        assert client.get(URL).status_code == 405
