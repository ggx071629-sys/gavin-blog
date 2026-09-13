from __future__ import annotations

import asyncio
import html
import json
import re
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from langchain_core.messages import HumanMessage
from openai import APIError

from app.assistant.graph import _settle_chat, _usage_from_raw
from app.assistant.output import validate_model_answer
from app.assistant.prompt import build_prompt, estimate_tokens
from app.assistant.providers import bind_answer_model, build_chat_model
from app.config import Settings

from .test_assistant_online import _create_session, _online_client, _publish_and_index, _sse_body
from .test_assistant_runtime_integrity_remediation import _evidence


def _model(*, content=None, finish="stop", usage=True, status=200, **overrides):
    settings = Settings(
        _env_file=None,
        **{
            "environment": "development",
            "assistant_chat_provider": "openai-compatible",
            "assistant_chat_endpoint": "https://api.deepseek.com/v1",
            "assistant_chat_model": "deepseek-v4-flash",
            "assistant_chat_api_key": "test-only-key",
            "assistant_chat_max_output_tokens": 256,
            "assistant_provider_timeout_seconds": 5,
            **overrides,
        },
    )
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        if status != 200:
            return httpx.Response(status, json={"error": {"message": "synthetic error"}})
        reply = content
        if callable(reply):
            reply = reply(requests[-1])
        if reply is None:
            user = requests[-1]["messages"][-1]["content"]
            passages = re.findall(r"<untrusted-evidence descriptor=(.*?)>\n(.*?)\n</untrusted-evidence>",
                                  user, re.DOTALL)
            passage = next((p for p in passages if "FastAPI" in p[1]), None)
            alias, quote = (json.loads(html.unescape(passage[0]))["id"],
                            html.unescape(passage[1])) if passage else ("c1", _evidence()[0].body)
            reply = json.dumps({"blocks": [{"text": "Published notes cover FastAPI.",
                "citation_ids": [alias], "supports": [{"citation_id": alias, "quote": quote}]}]})
        payload = {
            "id": "synthetic",
            "object": "chat.completion",
            "created": 0,
            "model": "deepseek-v4-flash",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": finish,
                    "message": {
                        "role": "assistant",
                        "content": reply,
                    },
                }
            ],
        }
        if usage:
            payload["usage"] = {"prompt_tokens": 90, "completion_tokens": 30, "total_tokens": 120}
        return httpx.Response(200, json=payload)

    chat = build_chat_model(settings)
    # Exercise the pinned LangChain/OpenAI serializer over a synthetic HTTP transport.
    from openai import AsyncOpenAI, OpenAI

    chat.root_client = OpenAI(
        api_key="test",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handle)),
    )
    chat.root_async_client = AsyncOpenAI(
        api_key="test",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
    )
    chat.client = chat.root_client.chat.completions
    chat.async_client = chat.root_async_client.chat.completions
    return chat, requests


def test_deepseek_transport_and_production_boundary():
    for asynchronous in (False, True):
        chat, requests = _model()
        chain = bind_answer_model(chat)
        messages = [HumanMessage(content="Return the published fact.")]
        result = asyncio.run(chain.ainvoke(messages)) if asynchronous else chain.invoke(messages)
        assert result["parsed"].blocks[0].citation_ids == ["c1"]
        assert result["parsing_error"] is None
        (request,) = requests
        assert request["response_format"] == {"type": "json_object"}
        assert request["max_tokens"] == 256
        assert "max_completion_tokens" not in request
        assert request["thinking"] == {"type": "disabled"}
        assert request["stream"] is False and chat.max_retries == 0
        assert "JSON" in request["messages"][0]["content"]
        assert "citation_ids" in request["messages"][0]["content"]
    for overrides in (
        {"environment": "production"},
        {"assistant_chat_endpoint": "https://api.deepseek.com.evil.invalid/v1"},
        {"assistant_chat_endpoint": "https://api.deepseek.com/beta"},
    ):
        chat, requests = _model(**overrides)
        assert type(chat).__name__ == "ChatOpenAI"
        assert chat.max_tokens == 256
        bind_answer_model(chat).invoke([("human", "Return the schema.")])
        assert requests[0]["response_format"]["type"] == "json_schema"
        assert requests[0]["response_format"]["json_schema"]["strict"] is True
        assert requests[0]["max_completion_tokens"] == 256
        assert "thinking" not in requests[0]
    for status in (400, 429, 500):
        chat, requests = _model(status=status)
        with pytest.raises(APIError):
            bind_answer_model(chat).invoke([("human", "JSON")])
        assert len(requests) == 1


def test_deepseek_strict_validation_metadata_and_citations():
    bad = [
        "",
        "{}",
        '{"blocks":null}',
        '{"blocks":[{"text":"x"}]}',
        '{"blocks":[{"text":1,"citation_ids":[]}]}',
        '{"blocks":[{"text":"x","citation_ids":[],"extra":1}]}',
        '{"blocks":[],"extra":1}',
        '{"blocks":[]} trailing',
        '```json\n{"blocks":[]}\n```',
        '{"blocks":[]',
        '{"blocks":[{"text":"x","citation_ids":[1]}]}',
    ]
    for content in bad:
        chat, requests = _model(content=content)
        result = bind_answer_model(chat).invoke([("human", "JSON")])
        assert result["parsed"] is None and result["parsing_error"]
        assert len(requests) == 1
        finish, usage = _usage_from_raw(result["raw"])
        assert finish == "stop" and usage["input_tokens"] == 90
        assert usage["model"] == "deepseek-v4-flash"
        assert usage["model_identity_source"] == "provider-response"
    chat, _ = _model(finish="length")
    result = bind_answer_model(chat).invoke([("human", "JSON")])
    assert (
        validate_model_answer(result["parsed"], _evidence(), finish_reason="length") == "incomplete"
    )
    chat, _ = _model(content='{"blocks":[{"text":"x","citation_ids":["made-up"],"supports":[]}]}', usage=False)
    result = bind_answer_model(chat).invoke([("human", "JSON")])
    assert validate_model_answer(result["parsed"], _evidence(), finish_reason="stop") == "citation"
    _, usage = _usage_from_raw(result["raw"])
    assert usage["usage_source"] == "unknown"
    online = SimpleNamespace(
        settings=SimpleNamespace(
            assistant_chat_input_price_cny_per_million=Decimal("1"),
            assistant_chat_output_price_cny_per_million=Decimal("2"),
        )
    )
    assert _settle_chat(online, usage, 1000) == (1000, True)


def test_deepseek_prompt_budget_covers_actual_schema_message():
    chat, requests = _model()
    args = dict(
        question="What do the notes cover?",
        evidence=_evidence(),
        history=[],
        provider=chat,
        max_input_tokens=8000,
        max_output_tokens=256,
        context_window_tokens=8256,
    )
    prompt = build_prompt(**args)
    assert prompt is not None
    result = bind_answer_model(chat).invoke(prompt.messages)
    assert validate_model_answer(result["parsed"], _evidence(), finish_reason="stop").citations
    sent = requests[0]["messages"]
    # Verify evidence identity survives into the actual provider request. Without
    # this distinction an article's taxonomy can be mistaken for profile skills.
    human = next(message["content"] for message in sent if message["role"] == "user")
    descriptor = re.search(r"<untrusted-evidence descriptor=(.*?)>", human)
    assert descriptor is not None
    identity = json.loads(html.unescape(descriptor.group(1)))
    assert identity == {
        "id": "c1",
        "source_type": "article",
        "title": "Python notes",
        "heading": "Python",
    }
    assert "Published notes cover FastAPI and SQLite." in human
    size = sum(len(str(m["content"]).encode("utf-8")) for m in sent)
    assert prompt.estimated_tokens >= size
    plain, _ = _model(assistant_chat_endpoint="https://example.invalid/v1")
    assert estimate_tokens(prompt.messages, chat) > estimate_tokens(prompt.messages, plain)
    assert build_prompt(**{**args, "max_input_tokens": prompt.estimated_tokens - 1}) is None
    assert len(requests) == 1


@pytest.mark.parametrize("invalid", [False, True])
def test_deepseek_online_graph_settles_and_rejects_invalid_body(tmp_path, invalid):
    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        online = client.app.state.assistant
        chat, requests = _model(content='{"blocks":[]' if invalid else None)
        online.chat = chat
        csrf = _create_session(client)
        status, body = _sse_body(
            client, csrf, "What Python notes are published?", idem="deepseek-transport-integration"
        )
        assert status == 200
        assert ("event: answer" in body) is not invalid
        if invalid:
            assert "Published notes cover" not in body
        else:
            assert "FastAPI" in body and '"title":"Python notes"' in body
            assert '"supports"' not in body and '"quote"' not in body
        assert 1 <= len(requests) <= 2
        attempts = online.control.read(
            lambda conn: conn.execute(
                "SELECT usage_json, settled_micro, parsed_json FROM assistant_attempts "
                "WHERE kind = 'chat' AND usage_json IS NOT NULL"
            ).fetchall()
        )
        assert len(attempts) == len(requests)
        assert all(json.loads(a["usage_json"])["input_tokens"] == 90 for a in attempts)
        assert all(a["settled_micro"] > 0 for a in attempts)
        if invalid:
            assert all(a["parsed_json"] is None for a in attempts)


@pytest.mark.parametrize("finish", ["stop", "length"])
def test_deepseek_empty_blocks_refuses_only_complete_response(tmp_path, finish):
    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        online = client.app.state.assistant
        chat, requests = _model(content='{"blocks":[]}', finish=finish)
        online.chat = chat
        csrf = _create_session(client)
        status, body = _sse_body(
            client, csrf, "What Python notes are published?", idem="empty-blocks-refusal"
        )
        assert status == 200 and "event: answer" not in body
        if finish == "stop":
            assert '"code":"insufficient_evidence"' in body
            assert len(requests) == 1
        else:
            assert '"code":"output_invalid"' in body
            assert len(requests) == 2
        rows = online.control.read(
            lambda conn: conn.execute(
                "SELECT usage_json, settled_micro FROM assistant_attempts "
                "WHERE kind = 'chat' AND usage_json IS NOT NULL"
            ).fetchall()
        )
        assert len(rows) == len(requests) and all(row["settled_micro"] > 0 for row in rows)


def test_schema_keywords_never_become_answer_data_or_get_repaired():
    from copy import deepcopy

    from app.assistant.providers import answer_schema_instruction

    instruction = answer_schema_instruction()
    example, _ = json.JSONDecoder().raw_decode(
        instruction.split("Data shape example only: ", 1)[1]
    )
    for location in ("top", "block", "support"):
        payload = deepcopy(example)
        target = (payload if location == "top" else payload["blocks"][0]
                  if location == "block" else payload["blocks"][0]["supports"][0])
        target["additionalProperties"] = False
        raw = json.dumps(payload)
        chat, requests = _model(content=raw)
        result = bind_answer_model(chat).invoke([("human", "Use only current source JSON.")])
        assert result["parsed"] is None and result["parsing_error"]
        assert result["raw"].content == raw and len(requests) == 1
    chat, _ = _model(content=json.dumps(example))
    result = bind_answer_model(chat).invoke([("human", "Use current evidence JSON.")])
    assert result["parsed"] is not None
    # An illustrative shape must never become valid evidence for a real question.
    assert validate_model_answer(result["parsed"], _evidence(), finish_reason="stop") == "grounding"
