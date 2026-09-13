from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


def runner():
    path = (
        Path(__file__).resolve().parents[3]
        / "plan-build/assistant-gap-closure/evaluation/run_current_quality.py"
    )
    spec = importlib.util.spec_from_file_location("current_quality", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_dataset_is_versioned_split_and_rejects_drift():
    r = runner()
    corpus, cases = r.read_json(r.BASE / "Q5-corpus.json"), r.read_json(r.BASE / "Q5-cases.json")
    r.validate_dataset(corpus, cases)
    assert len(corpus["sources"]) == 5
    assert {s["key"].split(":")[0] for s in corpus["sources"]} == {"article", "profile", "resume"}
    assert sum(row["split"] == "debug" for row in cases["rows"]) == 3
    assert sum(row["split"] == "evaluation" for row in cases["rows"]) == 15
    assert "independent_human_review_unverified" in cases["annotation_review"]
    with pytest.raises(ValueError, match="corpus changed"):
        r.validate_dataset(corpus, cases, [])
    cases["rows"][0]["expected_support"][0]["source"] = "about:missing"
    with pytest.raises(ValueError, match="unknown/empty"):
        r.validate_dataset(corpus, cases)


def test_current_quality_budget_precedes_dispatch_and_unknown_stops(monkeypatch, tmp_path):
    r = runner()
    assert (r.MAX_CALLS, r.MAX_MICRO_CNY) == (250, 4_000_000)
    contract = SimpleNamespace(
        max_input_tokens=8000,
        max_output_tokens=512,
        input_price_micro_cny_per_million=3_000_000,
        output_price_micro_cny_per_million=9_000_000,
        model="deepseek-flash",
    )
    calls, settlements = [], []
    bound = SimpleNamespace(invoke=lambda messages: calls.append(messages))
    status = dict(
        authorization_id=r.AUTHORIZATION,
        unresolved=[],
        calls_remaining=22,
        micro_cny_remaining=1664624,
    )
    r.check_envelope(status, 15, r.max_cost(contract))
    for change in [
        dict(calls_remaining=14),
        dict(micro_cny_remaining=1),
        dict(unresolved=[{}]),
        dict(authorization_id="assistant-gap-closure-g07-100-20260912"),
    ]:
        with pytest.raises(ValueError):
            r.check_envelope({**status, **change}, 15, r.max_cost(contract))

    def exhausted(*args, **kwargs):
        raise ValueError("cumulative envelope exhausted")

    monkeypatch.setattr(r.probe, "_reserve", exhausted)
    with pytest.raises(ValueError, match="exhausted"):
        r.paid_call(None, contract, tmp_path / "unused", bound, [], 8000)
    assert calls == []
    monkeypatch.setattr(r.probe, "_reserve", lambda *a, **k: "attempt")
    monkeypatch.setattr(r.probe, "_settle", lambda *a, **k: settlements.append(k))

    def unknown(messages):
        calls.append(messages)
        raise TimeoutError()

    bound.invoke = unknown
    result, parsed = r.paid_call(None, contract, tmp_path / "unused", bound, ["question"], 8000)
    assert parsed is None and not result["transport_ok"] and len(calls) == 1
    assert settlements[-1]["status"] == "unknown"
    assert settlements[-1]["settled_micro_cny"] == 28608


def test_current_quality_identity_and_usage_settle_without_retry(monkeypatch, tmp_path):
    r = runner()
    contract = SimpleNamespace(
        max_input_tokens=8000,
        max_output_tokens=512,
        input_price_micro_cny_per_million=3_000_000,
        output_price_micro_cny_per_million=9_000_000,
        model="deepseek-flash",
    )
    settlements, reserves = [], []
    monkeypatch.setattr(r.probe, "_reserve", lambda *a, **k: reserves.append(k) or "attempt")
    monkeypatch.setattr(r.probe, "_settle", lambda *a, **k: settlements.append(k))
    for model, accepted in [("deepseek-flash", True), ("unexpected-model", False)]:
        raw = SimpleNamespace(
            content="{}",
            usage_metadata=dict(input_tokens=100, output_tokens=10),
            response_metadata=dict(model_name=model, finish_reason="stop"),
        )
        bound = SimpleNamespace(invoke=lambda _, raw=raw: dict(raw=raw, parsed=None))
        result, _ = r.paid_call(None, contract, tmp_path / "unused", bound, [], 100)
        assert reserves[-1]["reserved_micro_cny"] == 4908
        assert result["transport_ok"] is accepted
        assert result["cost_micro_cny"] == 390
        assert settlements[-1]["status"] == ("succeeded" if accepted else "measured_fail")


def test_current_quality_default_prepare_never_dispatches_or_reserves(monkeypatch, tmp_path):
    from contextlib import nullcontext

    r = runner()
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(r, "API_ROOT", tmp_path)
    monkeypatch.setattr(r.sys, "argv", ["run_current_quality.py"])
    settings = SimpleNamespace(assistant_online_enabled=False, database_url="unused")
    monkeypatch.setattr(r, "Settings", lambda **k: settings)
    monkeypatch.setattr(r, "evaluation_settings", lambda: settings)
    contract = SimpleNamespace(
        max_input_tokens=8000,
        max_output_tokens=512,
        input_price_micro_cny_per_million=3_000_000,
        output_price_micro_cny_per_million=9_000_000,
    )
    monkeypatch.setattr(r, "contract_for", lambda _: contract)
    database = SimpleNamespace(
        session_factory=lambda: nullcontext(SimpleNamespace(info={})),
        engine=SimpleNamespace(dispose=lambda: None),
    )
    monkeypatch.setattr(r, "Database", lambda _: database)
    monkeypatch.setattr(
        r,
        "build_runtime",
        lambda *a: SimpleNamespace(
            store=SimpleNamespace(client=SimpleNamespace(close=lambda: None))
        ),
    )
    monkeypatch.setattr(r, "build_chat_model", lambda _: object())
    # Source validation is exercised separately. This isolates the orchestration
    # branch with a prepared, callable prompt to prove default mode never pays.
    monkeypatch.setattr(r, "iter_public_sources", lambda _: None)
    monkeypatch.setattr(r, "prepare_case", lambda *a: (dict(chat_called=False), object()))
    monkeypatch.setattr(r.local_ledger, "run_lock", lambda _: nullcontext())
    monkeypatch.setattr(
        r.local_ledger,
        "status",
        lambda **k: dict(
            authorization_id=r.AUTHORIZATION,
            unresolved=[],
            calls_remaining=22,
            micro_cny_remaining=1664624,
        ),
    )

    def forbidden(*a, **k):
        raise AssertionError("prepare cannot reserve or dispatch")

    monkeypatch.setattr(r, "paid_call", forbidden)
    monkeypatch.setattr(r.probe, "_reserve", forbidden)
    monkeypatch.setattr(r, "bind_answer_model", forbidden)
    r.main()
    report = r.read_json(next((tmp_path / "data").glob("qa-current-*.json")))
    assert report["mode"] == "prepare"
    assert all(not row["chat_called"] for row in report["rows"])
    assert report["budget_before"] == report["budget_after"]


def test_evaluation_uses_reviewed_input_cap_and_reserves_actual_prompt(monkeypatch):
    r = runner()
    from app.config import Settings

    settings = Settings(
        _env_file=None,
        assistant_chat_max_input_tokens=32000,
        assistant_chat_context_window_tokens=131072,
        assistant_chat_max_output_tokens=512,
    )
    monkeypatch.setattr(r, "Settings", lambda **k: settings)
    effective = r.evaluation_settings()
    assert effective.assistant_chat_max_input_tokens == 32000
    assert settings.assistant_chat_max_input_tokens == 32000
    assert (
        r.max_cost(
            SimpleNamespace(
                max_input_tokens=8000,
                max_output_tokens=512,
                input_price_micro_cny_per_million=3_000_000,
                output_price_micro_cny_per_million=9_000_000,
            ),
            7000,
        )
        == 25608
    )
    assert r.AUTHORIZATION == "assistant-gap-closure-q5-250-4-20260913"


def test_expanded_input_keeps_complete_multi_source_evidence():
    from dataclasses import replace

    from app.assistant.prompt import build_prompt

    from .test_assistant_deepseek import _model
    from .test_assistant_runtime_integrity_remediation import _evidence

    chat, _ = _model()
    evidence = [
        replace(
            _evidence()[0],
            alias=f"c{i}",
            source_id=i,
            title=f"资料{i}",
            body=(f"资料{i}保留来源条件和原文说明，不能将相关内容改写为无条件事实。" * 25),
        )
        for i in range(1, 4)
    ]
    common = dict(
        question="这些资料如何保留条件？",
        evidence=evidence,
        history=[],
        provider=chat,
        max_output_tokens=512,
        context_window_tokens=131072,
    )
    full = build_prompt(**common, max_input_tokens=32000)
    small = build_prompt(**common, max_input_tokens=8000)
    assert full is not None and full.evidence == evidence
    assert all(item.body in full.messages[-1][1] for item in evidence)
    assert full.estimated_tokens <= 32000
    assert small is None or len(small.evidence) < len(evidence)
