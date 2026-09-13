import threading
import time

import pytest

from app.assistant.admin_operations import build_snapshot
from app.assistant.readiness import write_receipt
from app.content_write_fence import content_write_fence

from .conftest import login
from .test_assistant_online import ORIGIN, _online_client, _publish_and_index


@pytest.mark.parametrize("scope", ["public", "admin"])
@pytest.mark.parametrize("operation", ["clear", "stop"])
def test_runtime_revocation_survives_content_fence(tmp_path, scope, operation):
    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        online = client.app.state.assistant
        admin_headers = {"Origin": ORIGIN, "X-CSRF-Token": login(client)}
        assert client.post("/api/v1/admin/assistant/trial/resume",
                           headers=admin_headers).status_code == 200
        prefix = "/api/v1/admin/assistant/trial" if scope == "admin" else "/api/v1/assistant"
        fence = content_write_fence(online.settings)
        fence.acquire()
        try:
            created = client.post(prefix + "/sessions", headers=admin_headers)
            assert created.status_code == 200, created.text
            assert client.post("/api/v1/admin/articles", json={},
                               headers=admin_headers).status_code == 503
            assert client.post("/api/v1/admin/assistant/emergency-stop",
                               headers={"Origin": ORIGIN}).status_code == 403
        finally:
            fence.release()
        headers = {**admin_headers, "X-Assistant-CSRF": created.json()["csrf_token"],
                   "Idempotency-Key": "live-fence-revocation-0001"}
        online.chat.hold()
        result = []
        thread = threading.Thread(target=lambda: result.append(client.post(
            prefix + "/questions", json={"question": "Which notes cover FastAPI?"},
            headers=headers,
        )))
        thread.start()
        try:
            assert online.chat.wait_until_started(10)
            fence.acquire()
            try:
                response = (client.delete(prefix + "/session", headers=headers)
                            if operation == "clear" else client.post(
                                "/api/v1/admin/assistant/emergency-stop", headers=admin_headers))
                assert response.status_code in ({202, 204} if operation == "clear" else {200})
            finally:
                fence.release()
        finally:
            online.chat.release()
            thread.join(15)
        assert not thread.is_alive()
        assert result and "event: answer" not in result[0].text
        restored = client.get(prefix + "/session", headers=headers)
        if operation == "clear":
            assert restored.status_code == 401
        else:
            assert not any(turn.get("answer") for turn in restored.json()["turns"])


def test_dashboard_reconciles_reissued_readiness(tmp_path):
    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        online = client.app.state.assistant
        with online.content_session() as db:
            before = build_snapshot(settings=online.settings, online=online, db=db,
                                    launcher_source="test")
        assert before.availability.effective_state == "enabled"
        write_receipt(online.settings, probe_live=False, lock=online.lock)
        with online.content_session() as db:
            after = build_snapshot(settings=online.settings, online=online, db=db,
                                   launcher_source="test")
        assert after.availability.effective_state == "blocked"
        assert after.availability.blocked_reason == "readiness_drift"
        assert after.availability.version > before.availability.version
        assert client.get("/api/v1/assistant/availability").json() == {"available": False}


def test_e2e_worker_keeps_observation_alive(tmp_path):
    from fastapi.testclient import TestClient

    from scripts.run_assistant_e2e import build_app

    app = build_app(tmp_path, ORIGIN)
    with TestClient(app):
        online = app.state.assistant
        with online.content_session() as db:
            from app.models import AssistantIndexWorkerState
            before = db.get(AssistantIndexWorkerState, 1).heartbeat_at
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with online.content_session() as db:
                after = db.get(AssistantIndexWorkerState, 1).heartbeat_at
            if after > before:
                break
            time.sleep(0.05)
        assert after > before
