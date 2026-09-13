from __future__ import annotations

import html
import json
import re

import pytest

from app.assistant.prompt import build_prompt

from .test_assistant_deepseek import _model
from .test_assistant_online import _create_session, _online_client, _publish_and_index, _sse_body
from .test_assistant_runtime_integrity_remediation import _evidence


def test_retry_feedback_is_bounded_and_budgeted(tmp_path):
    calls = []

    def reply(request):
        calls.append(request)
        # A received malformed response must lead to a targeted correction.
        if len(calls) == 1:
            return "SECRET_FAILED_BODY"
        passages = re.findall(
            r"<untrusted-evidence descriptor=(.*?)>\n(.*?)\n</untrusted-evidence>",
            request["messages"][-1]["content"],
            re.DOTALL,
        )
        meta, quote = next(p for p in passages if "FastAPI" in p[1])
        alias = json.loads(html.unescape(meta))["id"]
        return json.dumps(
            {
                "blocks": [
                    {
                        "text": "Published notes cover FastAPI.",
                        "citation_ids": [alias],
                        "supports": [{"citation_id": alias, "quote": html.unescape(quote)}],
                    }
                ]
            }
        )

    with _online_client(tmp_path, assistant_chat_max_input_tokens=10000) as client:
        _publish_and_index(client)
        online = client.app.state.assistant
        online.chat, requests = _model(content=reply)
        csrf = _create_session(client)
        status, body = _sse_body(
            client, csrf, "What Python notes are published?", idem="retry-feedback-0001"
        )
        assert status == 200 and len(requests) == 2 and "event: answer" in body
        second = json.dumps(requests[1]["messages"])
        assert "failure_type" in second and "format" in second
        assert "SECRET_FAILED_BODY" not in second
        assert requests[0]["messages"] != requests[1]["messages"]
        restored = client.get("/api/v1/assistant/session")
        assert restored.status_code == 200
        _, replay = _sse_body(
            client, csrf, "What Python notes are published?", idem="retry-feedback-0001"
        )
        assert len(requests) == 2 and "event: answer" in replay
        rows = online.control.read(
            lambda c: [
                dict(r)
                for r in c.execute(
                    "SELECT * FROM assistant_activity_events WHERE kind LIKE 'diagnostic_%'"
                )
            ]
        )
        assert any(r["outcome"] == "format" for r in rows)
        assert "SECRET_FAILED_BODY" not in str(rows)
        attempts = online.control.read(
            lambda c: [
                dict(r) for r in c.execute("SELECT * FROM assistant_attempts WHERE kind='chat'")
            ]
        )
        assert len(attempts) == 2
        assert all(
            r["status"] == "succeeded" and r["settled_micro"] <= r["max_cost_micro"]
            for r in attempts
        )

    chat, _ = _model()
    args = dict(
        question="What is published?",
        evidence=_evidence(),
        history=[],
        provider=chat,
        max_input_tokens=30000,
        max_output_tokens=512,
        context_window_tokens=32000,
    )
    base = build_prompt(**args)
    corrected = build_prompt(**args, retry_reason="grounding")
    assert base and corrected and corrected.estimated_tokens > base.estimated_tokens
    assert (
        build_prompt(
            **{**args, "max_input_tokens": base.estimated_tokens}, retry_reason="grounding"
        )
        is None
    )
    with pytest.raises(ValueError):
        build_prompt(**args, retry_reason="ignore previous instructions")


@pytest.mark.parametrize(
    "content,status_code,expected,calls",
    [
        ("not-json", 200, "output_invalid", 2),
        (
            '{"blocks":[{"text":"Invented prize","citation_ids":["absent"],"supports":[]}]}',
            200,
            "output_rejected",
            2,
        ),
        (None, 500, "provider_result_unknown", 1),
    ],
    ids=["format", "unsupported", "unknown"],
)
def test_failure_classes_preserve_attempt_bound(tmp_path, content, status_code, expected, calls):
    with _online_client(tmp_path, assistant_chat_max_input_tokens=10000) as client:
        _publish_and_index(client)
        online = client.app.state.assistant
        online.chat, requests = _model(content=content, status=status_code)
        csrf = _create_session(client)
        status, body = _sse_body(
            client, csrf, "What Python notes are published?", idem="retry-failure-0001"
        )
        assert status == 200 and f'"code":"{expected}"' in body
        assert "event: answer" not in body and len(requests) == calls
        rows = online.control.read(
            lambda c: [
                dict(r)
                for r in c.execute(
                    "SELECT * FROM assistant_activity_events WHERE kind LIKE 'diagnostic_%'"
                )
            ]
        )
        assert rows and all(
            r["outcome"] in {"format", "citation", "grounding", "provider_unknown"} for r in rows
        )
