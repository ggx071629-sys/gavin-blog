from types import SimpleNamespace

import pytest

from .test_assistant_online import _create_session, _online_client, _publish_and_index, _sse_body


@pytest.mark.parametrize("result", [None, {"raw": None, "parsed": None}], ids=["none", "empty"])
def test_unobserved_provider_result_is_unknown_and_never_retried(tmp_path, monkeypatch, result):
    from app.assistant import graph

    calls = []

    async def invoke(messages):
        calls.append(messages)
        return result

    with _online_client(tmp_path, assistant_chat_max_input_tokens=10000) as client:
        _publish_and_index(client)
        monkeypatch.setattr(graph, "bind_answer_model", lambda _: SimpleNamespace(ainvoke=invoke))
        csrf = _create_session(client)
        _, body = _sse_body(client, csrf, "Which notes cover FastAPI?", idem="unobserved-result-01")
        assert "provider_result_unknown" in body and "event: answer" not in body
        online = client.app.state.assistant
        attempts = online.control.read(
            lambda c: [
                dict(r)
                for r in c.execute(
                    "SELECT * FROM assistant_attempts WHERE kind='chat' AND status != 'prepared'"
                )
            ]
        )
        sent = [r for r in attempts if r["status"] == "unknown"]
        assert len(sent) == 1 and sent[0]["status"] == "unknown"
        assert all(r["settled_micro"] == 0 for r in attempts if r["status"] != "unknown")
        assert sent[0]["settled_micro"] == sent[0]["max_cost_micro"]
        assert sent[0]["parsed_json"] is None
        _, replay = _sse_body(
            client, csrf, "Which notes cover FastAPI?", idem="unobserved-result-01"
        )
        assert "provider_result_unknown" in replay and len(calls) == 1
        rows = online.control.read(
            lambda c: [
                dict(r)
                for r in c.execute("SELECT * FROM assistant_metered_events WHERE kind='chat'")
            ]
        )
        assert len(rows) == 1 and rows[0]["cost_micro"] == sent[0]["max_cost_micro"]
