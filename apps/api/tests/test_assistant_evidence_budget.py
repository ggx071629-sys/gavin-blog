from __future__ import annotations

from dataclasses import replace
import html
import json
import re

import pytest

from app.assistant.prompt import build_prompt, estimate_tokens

from .test_assistant_deepseek import _model
from .test_assistant_online import _create_session, _online_client, _publish_and_index, _sse_body
from .test_assistant_runtime_integrity_remediation import _evidence, _Tokenizer


def _build(items, **kwargs):
    return build_prompt(**{
        "question": "介绍一下本站作者与项目。",
        "evidence": items,
        "history": [],
        "provider": _Tokenizer(),
        "max_input_tokens": 8000,
        "max_output_tokens": 512,
        "context_window_tokens": 8512,
        **kwargs,
    })


def test_evidence_budget_preserves_whole_ranked_diverse_sources():
    first = replace(_evidence()[0], body="完整的个人介绍。" * 50, source_type="profile")
    repeated = replace(first, alias="c2", chunk_id="other-chunk")
    more = replace(first, alias="c3", body="同一个人的工作经历。" * 120)
    project = replace(first, alias="c4", source_type="project", source_id=2,
                      body="完整项目说明。" * 80)
    small = replace(project, alias="c5", source_id=3, body="另一项项目记录。")
    items = [first, repeated, more, project, small]
    result = _build(items)
    assert result is not None
    # The fixed prompt grew during G07. Keep the first synthetic source short
    # enough to fit with c5 at the unchanged 8000 limit, so the test exercises
    # source diversity instead of rejecting its own first-source precondition.
    assert [item.alias for item in result.evidence] == ["c1", "c5"]
    assert result.estimated_tokens <= 8000
    assert result.estimated_tokens + 512 <= 8512
    assert result.estimated_tokens == estimate_tokens(result.messages, _Tokenizer())
    for item in result.evidence:
        assert item in items  # Complete original bodies, aliases and versions.
    assert items == [first, repeated, more, project, small]


def test_evidence_budget_skips_oversized_chunk_and_honors_context_reserve():
    huge = replace(_evidence()[0], body="长资料" * 5000)
    small = replace(huge, alias="c7", source_id=7, body="完整的小段资料。")
    baseline = _build([small], max_input_tokens=100000, context_window_tokens=100512)
    assert baseline is not None
    packed = _build([huge, small], max_input_tokens=100000,
                    context_window_tokens=baseline.estimated_tokens + 512)
    assert packed is not None and packed.evidence == [small]
    assert _build([huge, small], max_input_tokens=100000,
                  context_window_tokens=baseline.estimated_tokens + 511) is None
    assert _build([huge]) is None


def test_evidence_budget_keeps_order_when_everything_fits():
    a = _evidence()[0]
    b = replace(a, alias="c2", body="Another complete paragraph.")
    c = replace(a, alias="c3", source_id=2)
    history = [{"question": "previous question", "answer": "previous answer"}]
    result = _build([a, b, c], history=history)
    assert result is not None
    assert result.evidence == [a, b, c]
    assert result.history == history


def test_resume_budget_covers_later_page_before_more_from_first_page():
    first = replace(_evidence()[0], source_type="resume", heading_path="第 1 页",
                    body="Atlas 项目：完整的第一项项目说明。" * 50)
    skills = replace(first, alias="c2", body="第一页的技术能力说明。" * 100)
    second = replace(first, alias="c3", heading_path="第 2 页",
                     body="Beacon 项目：完整的第二项项目说明。" * 50)
    expected = _build([first, second], max_input_tokens=100000,
                      context_window_tokens=100512)
    assert expected is not None
    result = _build([first, skills, second], max_input_tokens=expected.estimated_tokens,
                    context_window_tokens=expected.estimated_tokens + 512)
    assert result is not None
    assert result.evidence == [first, second]
    assert result.estimated_tokens == expected.estimated_tokens
    assert "Atlas" in result.messages[1][1] and "Beacon" in result.messages[1][1]
    assert "include all distinct supported entries" in result.messages[0][1]
    assert "Never infer a document's total count" in result.messages[0][1]


@pytest.mark.parametrize("citation", ["c1", "c99"])
def test_packed_evidence_reaches_chat_and_rejects_omitted_citations(
    tmp_path, monkeypatch, citation,
):
    from app.assistant import graph

    original_retrieve = graph.hydrate_evidence
    original_hydrate = graph.hydrate_descriptors
    oversized = []

    def retrieve(*args, **kwargs):
        result = original_retrieve(*args, **kwargs)
        assert result.evidence
        oversized[:] = [replace(result.evidence[0], alias="c99", body="超长资料。" * 4000)]
        return replace(result, evidence=[*result.evidence, *oversized])

    def hydrate(db, descriptors):
        regular = original_hydrate(db, [d for d in descriptors if d["alias"] != "c99"])
        extra = [oversized[0]] if any(d["alias"] == "c99" for d in descriptors) else []
        return [*regular, *extra]

    monkeypatch.setattr(graph, "hydrate_evidence", retrieve)
    monkeypatch.setattr(graph, "hydrate_descriptors", hydrate)
    with _online_client(tmp_path, assistant_chat_max_input_tokens=8000) as client:
        _publish_and_index(client)
        def reply(request):
            passages = re.findall(r"<untrusted-evidence descriptor=(.*?)>\n(.*?)\n</untrusted-evidence>",
                                  request["messages"][-1]["content"], re.DOTALL)
            quotes = {json.loads(html.unescape(attrs))["id"]: html.unescape(body)
                      for attrs, body in passages}
            return json.dumps({"blocks": [{"text": "当前资料的相关内容。",
                "citation_ids": [citation], "supports": [{"citation_id": citation,
                "quote": quotes.get(citation, "omitted evidence")}]}]})
        chat, requests = _model(content=reply)
        client.app.state.assistant.chat = chat
        csrf = _create_session(client)
        status, body = _sse_body(client, csrf, "What Python notes are published?",
                                 idem=f"packed-evidence-{citation}")
        assert status == 200
        assert requests
        assert "input_budget_exceeded" not in body
        assert all("c99" not in str(request["messages"]) for request in requests)
        if citation == "c1":
            assert "event: answer" in body
            assert len(requests) == 1
        else:
            assert "event: answer" not in body
            assert '"code":"insufficient_evidence"' in body
