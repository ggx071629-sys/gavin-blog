from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from app.assistant.admin_operations import build_snapshot
from app.assistant.cleanup import sweep
from app.assistant.constants import BODY_RETENTION_SECONDS

from .test_assistant_deepseek import _model
from .test_assistant_online import (
    ORIGIN,
    _create_session,
    _headers,
    _online_client,
    _publish_and_index,
    _sse_body,
)


def prepare(client):
    _publish_and_index(client)
    online = client.app.state.assistant
    online.chat, calls = _model()
    csrf = _create_session(client)
    _, body = _sse_body(client, csrf, "What Python notes are published?", idem="feedback-answer-01")
    assert "event: answer" in body
    turn = client.get("/api/v1/assistant/session").json()["turns"][-1]
    return online, calls, csrf, turn["turn_id"]


def vote(client, csrf, turn, value):
    return client.put(
        f"/api/v1/assistant/turns/{turn}/feedback", json={"value": value}, headers=_headers(csrf)
    )


def test_feedback_authority_idempotence_and_no_model_calls(tmp_path):
    with _online_client(tmp_path, assistant_chat_max_input_tokens=10000) as client:
        online, calls, csrf, turn = prepare(client)
        for choice in ("helpful", "helpful", "unhelpful"):
            response = vote(client, csrf, turn, choice)
            assert response.status_code == 200 and response.json() == {
                "turn_id": turn,
                "value": choice,
            }
            assert response.headers["cache-control"] == "no-store"
        rows = online.control.read(
            lambda c: [
                dict(r)
                for r in c.execute("SELECT * FROM assistant_activity_events WHERE kind='feedback'")
            ]
        )
        assert len(rows) == 1 and rows[0]["outcome"] == "unhelpful"
        assert "Python" not in str(rows) and "FastAPI" not in str(rows)
        assert (
            client.get("/api/v1/assistant/session").json()["turns"][-1]["feedback"] == "unhelpful"
        )
        assert vote(client, "bad-csrf", turn, "helpful").status_code == 403
        assert (
            client.put(
                f"/api/v1/assistant/turns/{turn}/feedback",
                json={"value": "helpful"},
                headers={**_headers(csrf), "Origin": "https://foreign.invalid"},
            ).status_code
            == 403
        )
        assert (
            client.put(
                f"/api/v1/assistant/turns/{turn}/feedback",
                json={"value": "helpful", "text": "secret"},
                headers=_headers(csrf),
            ).status_code
            == 422
        )
        assert vote(client, csrf, turn, "free text").status_code == 422
        assert vote(client, csrf, "missing", "helpful").status_code == 404
        cookies = dict(client.cookies)
        client.cookies.clear()
        other_csrf = _create_session(client)
        assert vote(client, other_csrf, turn, "helpful").status_code == 404
        client.cookies.clear()
        client.cookies.update(cookies)
        assert vote(client, csrf, turn, None).status_code == 200
        assert (
            online.control.read(
                lambda c: c.execute(
                    "SELECT COUNT(*) FROM assistant_activity_events WHERE kind='feedback'"
                ).fetchone()[0]
            )
            == 0
        )
        assert len(calls) == 1
        online.control.immediate(
            lambda c: c.execute(
                "UPDATE assistant_turns SET terminal_event='refusal' WHERE id=?", (turn,)
            )
        )
        assert vote(client, csrf, turn, "helpful").status_code == 404


def test_feedback_expiry_clear_and_diagnostic_retention(tmp_path):
    with _online_client(tmp_path, assistant_chat_max_input_tokens=10000) as client:
        online, calls, csrf, turn = prepare(client)
        assert vote(client, csrf, turn, "helpful").status_code == 200
        terminal_at = online.control.read(
            lambda c: c.execute(
                "SELECT terminal_at FROM assistant_turns WHERE id=?", (turn,)
            ).fetchone()[0]
        )
        expiry = datetime.fromisoformat(str(terminal_at)) + timedelta(
            seconds=BODY_RETENTION_SECONDS
        )
        online.clock = lambda: expiry - timedelta(seconds=1)
        assert vote(client, csrf, turn, "unhelpful").status_code == 200
        online.clock = lambda: expiry
        assert vote(client, csrf, turn, "helpful").status_code == 404
        assert client.get("/api/v1/assistant/session").json()["turns"][-1]["feedback"] is None
        online.control.immediate(
            lambda c: c.execute(
                "INSERT INTO assistant_activity_events "
                "(event_id,beijing_date,kind,outcome,created_at) "
                "VALUES ('old-diagnostic','2000-01-01','stage_checking','completed',?)",
                (expiry - timedelta(days=8),),
            )
        )
        client.portal.call(sweep, online)
        assert (
            online.control.read(
                lambda c: c.execute(
                    "SELECT COUNT(*) FROM assistant_activity_events "
                    "WHERE kind='feedback' OR event_id='old-diagnostic'"
                ).fetchone()[0]
            )
            == 0
        )
        assert len(calls) == 1


def test_feedback_admin_snapshot_and_session_delete(tmp_path):
    with _online_client(tmp_path, assistant_chat_max_input_tokens=10000) as client:
        online, calls, csrf, turn = prepare(client)
        assert vote(client, csrf, turn, "helpful").status_code == 200
        with online.content_session() as db:
            snapshot = build_snapshot(
                settings=online.settings, online=online, db=db, launcher_source="test"
            )
        assert snapshot.daily_activity.feedback_helpful == 1
        assert snapshot.daily_activity.feedback_unhelpful == 0
        assert snapshot.daily_activity.stages
        exported = json.loads(
            (Path(__file__).resolve().parents[3] / "packages/contracts/openapi.json").read_text(
                encoding="utf-8"
            )
        )
        current = client.app.openapi()
        path = "/api/v1/assistant/turns/{turn_id}/feedback"
        assert exported["paths"][path] == current["paths"][path]
        for name in (
            "FeedbackRequest",
            "FeedbackResponse",
            "SessionTurn",
            "DailyActivityView",
            "StageActivityView",
        ):
            assert exported["components"]["schemas"][name] == current["components"]["schemas"][name]
        response = client.delete(
            "/api/v1/assistant/session", headers={"Origin": ORIGIN, "X-Assistant-CSRF": csrf}
        )
        assert response.status_code == 204
        assert (
            online.control.read(
                lambda c: c.execute(
                    "SELECT COUNT(*) FROM assistant_activity_events WHERE kind='feedback'"
                ).fetchone()[0]
            )
            == 0
        )
        assert len(calls) == 1
