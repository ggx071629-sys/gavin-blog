from __future__ import annotations

import json
import threading

import httpx
import pytest
from sqlalchemy import select

from app.assistant.article_tools import bind_article_tool_model, tool_prompt
from app.assistant.providers import LocalDeepSeekChatOpenAI, ScriptedChatTurn
from app.models import Article

from .assistant_tool_model import tool_online_client as _online_client
from .test_assistant_online import (
    ORIGIN,
    _create_session,
    _publish_and_index,
    _sse_body,
)


def _tool_call(**args):
    return dict(
        name="list_recent_articles",
        id="call-1",
        args={
            "order": "updated",
            "limit": 5,
            "window": None,
            **args,
        },
    )


@pytest.mark.parametrize("kind", ["valid", "invalid_arguments", "unknown", "multiple", "decline"])
def test_article_native_tool_wire_and_validation(kind):
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        call = _tool_call()
        if kind == "invalid_arguments":
            call["args"]["limit"] = 100
        if kind == "unknown":
            call["name"] = "execute_sql"
        wire = dict(
            id=call["id"],
            type="function",
            function=dict(
                name=call["name"],
                arguments=json.dumps(call["args"]),
            ),
        )
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [wire, wire] if kind == "multiple" else [wire],
        }
        if kind == "decline":
            message = {"role": "assistant", "content": "Unsupported query."}
        return httpx.Response(
            200,
            json={
                "id": "synthetic",
                "object": "chat.completion",
                "created": 0,
                "model": "deepseek-v4-flash",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop" if kind == "decline" else "tool_calls",
                        "message": message,
                    }
                ],
                "usage": {"prompt_tokens": 90, "completion_tokens": 30, "total_tokens": 120},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handle)) as transport:
        chat = LocalDeepSeekChatOpenAI(
            model="deepseek-v4-flash",
            api_key="test",
            max_tokens=256,
            http_client=transport,
            max_retries=0,
        )
        messages = tool_prompt(
            "最近更新了什么文章",
            retry_reason=None,
            max_input=8000,
            max_output=256,
            context_window=16384,
        )
        result = bind_article_tool_model(chat).invoke(messages)
        wire = requests[0]
        assert wire["tools"][0]["function"]["name"] == "list_recent_articles"
        assert wire["tool_choice"] == "auto"
        assert wire["max_tokens"] == 256
        assert wire["thinking"] == {"type": "disabled"}
        assert "response_format" not in wire and "max_completion_tokens" not in wire
        if kind == "valid":
            assert result["parsed"].arguments.order == "updated"
        elif kind == "decline":
            assert result["parsed"].arguments is None
        else:
            assert result["parsed"] is None
        assert result["raw"].response_metadata["token_usage"]["prompt_tokens"] == 90
        size = len(json.dumps(wire, ensure_ascii=False).encode("utf-8"))
        assert (
            tool_prompt(
                "最近更新了什么文章",
                retry_reason=None,
                max_input=size - 1,
                max_output=256,
                context_window=16384,
            )
            is None
        )


@pytest.mark.parametrize(
    "args",
    [
        {"limit": 100},
        {"limit": True},
        {"order": "sql"},
        {"window": "yesterday"},
        {"sql": "SELECT * FROM articles"},
    ],
)
def test_article_tool_invalid_args_never_execute(tmp_path, monkeypatch, args):
    from app.assistant import graph

    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        online = client.app.state.assistant
        online.chat.script.extend(
            [
                ScriptedChatTurn(
                    parsed={"tool_calls": [_tool_call(**args)]}, finish_reason="tool_calls"
                )
                for _ in range(2)
            ]
        )

        def forbidden(*args, **kwargs):
            raise AssertionError("invalid tool arguments must not reach the database")

        monkeypatch.setattr(graph, "execute_article_tool", forbidden)
        csrf = _create_session(client)
        status, body = _sse_body(client, csrf, "最近更新了什么文章", idem="bad-tool-args-0001")
        assert status == 200 and "output_invalid" in body and "event: answer" not in body
        assert len(online.chat.calls) == 2


def test_article_tool_budget_rejects_before_model(tmp_path):
    with _online_client(tmp_path, assistant_chat_max_input_tokens=1000) as client:
        _publish_and_index(client)
        status, body = _sse_body(
            client, _create_session(client), "最近更新了什么文章", idem="tool-input-budget-0001"
        )
        assert status == 200 and "input_budget_exceeded" in body
        assert not client.app.state.assistant.chat.calls


def test_article_tool_declines_unsupported_query(tmp_path):
    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        status, body = _sse_body(
            client, _create_session(client), "最近更新的草稿文章", idem="tool-unsupported-0001"
        )
        assert status == 200 and "clarification_required" in body
        assert "event: answer" not in body
        assert len(client.app.state.assistant.chat.calls) == 1


@pytest.mark.parametrize("mutation", ["unpublish", "delete_session"])
def test_article_tool_reads_current_state_after_model(tmp_path, mutation):
    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        online = client.app.state.assistant
        csrf = _create_session(client)
        online.chat.hold()
        responses = []
        worker = threading.Thread(
            target=lambda: responses.append(
                _sse_body(
                    client,
                    csrf,
                    "最近更新了什么文章",
                    idem="tool-current-facts-0001",
                )
            ),
            daemon=True,
        )
        worker.start()
        try:
            assert online.chat.wait_until_started()
            if mutation == "unpublish":
                with online.content_session() as db:
                    article = db.scalar(select(Article))
                    article.status = "draft"
                    db.commit()
            else:
                deleted = client.delete(
                    "/api/v1/assistant/session",
                    headers={
                        "Origin": ORIGIN,
                        "X-Assistant-CSRF": csrf,
                    },
                )
                assert deleted.status_code in (202, 204)
        finally:
            online.chat.release()
            worker.join(timeout=15)
        assert not worker.is_alive()
        status, body = responses[0]
        assert status == 200
        assert "Python notes" not in body
        if mutation == "unpublish":
            assert "event: answer" in body and "没有" in body
        else:
            assert "event: answer" not in body
            assert (
                online.control.read(
                    lambda c: c.execute(
                        "SELECT count(*) FROM assistant_turns WHERE answer IS NOT NULL"
                    ).fetchone()[0]
                )
                == 0
            )
