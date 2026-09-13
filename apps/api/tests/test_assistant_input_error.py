from __future__ import annotations

import logging

from .test_assistant_deepseek import _model
from .test_assistant_online import _create_session, _online_client, _publish_and_index, _sse_body


def test_input_budget_error_is_persisted_without_chat_call(tmp_path, caplog):
    with _online_client(tmp_path, assistant_chat_max_input_tokens=100) as client:
        _publish_and_index(client)
        online = client.app.state.assistant
        chat, requests = _model()
        online.chat = chat
        csrf = _create_session(client)
        question = "What Python notes are published?"
        logger = logging.getLogger("gavin.assistant")
        assert not logger.disabled
        # Alembic replaces root handlers; attach capture to the application logger.
        logger.addHandler(caplog.handler)
        try:
            with caplog.at_level(logging.WARNING, logger="gavin.assistant"):
                status, body = _sse_body(client, csrf, question, idem="input-budget-diagnostic")
        finally:
            logger.removeHandler(caplog.handler)
        assert status == 200
        assert '"code":"input_budget_exceeded"' in body
        assert "provider_result_unknown" not in body
        assert "event: answer" not in body
        assert requests == []
        restored = client.get("/api/v1/assistant/session")
        assert restored.status_code == 200
        assert restored.json()["active_turn"] is None
        assert restored.json()["turns"][-1]["code"] == "input_budget_exceeded"
        messages = [
            r.getMessage() for r in caplog.records if "input_budget_exceeded" in r.getMessage()
        ]
        assert len(messages) == 1
        assert "estimated_tokens=" in messages[0]
        assert "max_input_tokens=100" in messages[0]
        assert "evidence_count=" in messages[0]
        assert question not in messages[0]
        assert "I write about FastAPI" not in messages[0]
