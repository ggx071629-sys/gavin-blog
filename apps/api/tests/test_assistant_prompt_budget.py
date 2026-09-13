from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import replace
from pathlib import Path

import pytest

from app.assistant.prompt import build_prompt
from app.assistant.prompt_budget import input_accounting, output_accounting

from .test_assistant_deepseek import _model
from .test_assistant_runtime_integrity_remediation import _evidence


def test_budget_accounting_preserves_units_and_omitted_evidence():
    chat, _ = _model()
    question = "预算 <秘密字段> & SQL"
    small = replace(_evidence()[0], body="完整资料。", title="预算资料")
    huge = replace(small, alias="c9", source_id=9, body="长资料" * 10000)
    history = [{"question": "旧问题", "answer": "旧答案" * 10000}]
    built = build_prompt(question=question, evidence=[huge, small], history=history,
                         provider=chat, max_input_tokens=8000, max_output_tokens=512,
                         context_window_tokens=8512)
    assert built is not None and built.evidence == [small] and built.history == []
    # Character count is a deliberately different unit from UTF-8 byte count.
    result = input_accounting(question=question, candidates=[huge, small], built=built,
                              provider=chat, count_text=len)
    assert sum(result["component_utf8_bytes"].values()) == result["serialized_utf8_bytes"]
    assert result["byte_fallback_tokens"] == result["serialized_utf8_bytes"] + 28
    assert result["admission_estimated_tokens"] >= result["byte_fallback_tokens"]
    assert result["component_utf8_bytes"]["question"] > (
        result["component_text_tokens_nonadditive"]["question"])
    assert result["candidate_evidence_utf8_bytes"] > (
        result["component_utf8_bytes"]["selected_evidence"])
    assert result["candidate_evidence_count"] == 2 and result["selected_evidence_count"] == 1
    assert result["selected_history_pairs"] == 0
    assert "秘密字段" not in json.dumps(result, ensure_ascii=False)


def test_output_budget_distinguishes_supports_json_and_empty_or_invalid():
    payload = {"blocks": [{"text": '原文有“引用”与\\路径。', "citation_ids": ["c1"],
                           "supports": [{"citation_id": "c1", "quote": "原文" * 500}]}]}
    raw = json.dumps(payload, ensure_ascii=False)
    result = output_accounting(raw, count_text=len)
    assert result["valid_structure"] and result["nonempty"]
    assert result["supports_utf8_bytes"] > result["answer_utf8_bytes"]
    assert sum(result[k] for k in ["answer_utf8_bytes", "supports_utf8_bytes",
                                  "json_and_citations_utf8_bytes"]) == (
        result["canonical_json_utf8_bytes"])
    assert not output_accounting('{"blocks":[]}', count_text=len)["nonempty"]
    for invalid in [raw[:-1], '{"blocks":[],"extra":"data"}',
                    raw.replace("原文" * 500, "原文" * 601)]:
        assert not output_accounting(invalid, count_text=len)["valid_structure"]
    assert "原文" not in json.dumps(result, ensure_ascii=False)


def test_minimum_input_and_context_boundaries_keep_original_limits():
    chat, _ = _model()
    item = replace(_evidence()[0], body="本教程调用 SMTP 服务完成邮件通知。")
    for question in ["文章如何介绍邮件通知？",
                     "How does the article describe email notifications?"]:
        for availability in [None, False]:
            args = dict(question=question, evidence=[item], history=[], provider=chat,
                        max_output_tokens=512, resume_available=availability)
            full = build_prompt(**args, max_input_tokens=100000, context_window_tokens=100512)
            threshold = full.estimated_tokens
            assert threshold <= 8000
            exact = build_prompt(**args, max_input_tokens=threshold,
                                 context_window_tokens=threshold + 512)
            assert exact.evidence == [item]
            assert build_prompt(**args, max_input_tokens=threshold - 1,
                                context_window_tokens=threshold + 512) is None
            assert build_prompt(**args, max_input_tokens=threshold,
                                context_window_tokens=threshold + 511) is None


def test_calibration_rejects_changed_data_and_unsupported_message_shapes(tmp_path, monkeypatch):
    import socket

    def blocked(*args, **kwargs):
        raise AssertionError("calibration must remain offline")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    path = Path(__file__).resolve().parents[3] / (
        "plan-build/assistant-gap-closure/evaluation/audit_prompt_budget.py")
    spec = importlib.util.spec_from_file_location("g12_audit", path)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    local = tmp_path / "data.json"
    data = b'{"fixture":true}'
    local.write_bytes(data)
    sha = hashlib.sha256(data).hexdigest()
    assert audit.read_verified(local, sha) == data
    local.write_bytes(data + b" ")
    with pytest.raises(ValueError, match="digest"):
        audit.read_verified(local, sha)
    messages = [{"role": "system", "content": "policy"},
                {"role": "system", "content": "schema"},
                {"role": "user", "content": "question"}]
    config = {"bos_token": {"content": "BOS"}}
    rendered = audit.official_text_template(messages, config)
    assert rendered.index("policy") < rendered.index("schema") < rendered.index("question")
    for invalid in [messages[1:], [*messages, {"role": "assistant", "content": "answer"}],
                    [messages[0], messages[2], messages[1]]]:
        with pytest.raises(ValueError, match="shape"):
            audit.official_text_template(invalid, config)


def test_current_chinese_clauses_fit_without_truncation_or_history_facts():
    chat, _ = _model()
    # A complete ~500-character Chinese source chunk used to be displaced by
    # repeated policy text under the byte-conservative 8000 input ceiling.
    body = "资料自述项目采用异步任务处理完整业务流程，并保留来源版本和审查记录。" * 15
    body += "自动续期测试命令是 sudo certbot renew --dry-run。"
    item = replace(_evidence()[0], body=body, title="运维笔记", heading_path="自动续期")
    built = build_prompt(question="文章提到什么自动续期测试命令？", evidence=[item],
                         history=[], provider=chat, max_input_tokens=8000,
                         max_output_tokens=512, context_window_tokens=8512)
    assert built is not None and built.evidence == [item]
    assert body in built.messages[-1][1] and built.history == []
    assert built.estimated_tokens <= 8000
    assert build_prompt(question="续期命令？", evidence=[item], history=[], provider=chat,
                        max_input_tokens=1000, max_output_tokens=512,
                        context_window_tokens=1512) is None
