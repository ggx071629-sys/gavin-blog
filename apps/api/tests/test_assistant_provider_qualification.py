from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.assistant.providers import (
    EmbeddingUsage,
    ModelAnswer,
    OpenAICompatibleMeteredEmbeddings,
)
from app.assistant_qualification.profile import QualificationProfile, profile_digest
from app.assistant_qualification.provider_probe import (
    ProviderQualificationError,
    provider_probe_digest,
    run_local_chat_probe,
    run_provider_probe,
    validate_provider_probe_artifact,
)
from app.config import Settings
from tests.test_assistant_qualification_profile import valid_profile_data


def _profile(tmp_path: Path) -> QualificationProfile:
    data = valid_profile_data()
    data["storage"]["paths"]["qualification_root"] = str(tmp_path.resolve())
    return QualificationProfile.model_validate(data)


def _cny(micro: int) -> Decimal:
    return Decimal(micro) / Decimal(1_000_000)


def _settings(profile: QualificationProfile) -> Settings:
    chat = profile.providers.chat
    embedding = profile.providers.embedding
    budgets = profile.providers.budgets
    return Settings(
        environment="production",
        assistant_online_enabled=False,
        assistant_index_worker_enabled=False,
        assistant_chat_provider=chat.protocol,
        assistant_chat_model=chat.model,
        assistant_chat_model_version=chat.model_version,
        assistant_chat_endpoint="https://provider.invalid/v1",
        assistant_chat_api_key="test-secret-not-written",
        assistant_chat_max_input_tokens=chat.max_input_tokens,
        assistant_chat_max_output_tokens=chat.max_output_tokens,
        assistant_chat_context_window_tokens=chat.context_window_tokens,
        assistant_chat_input_price_cny_per_million=_cny(chat.input_price_micro_cny_per_million),
        assistant_chat_output_price_cny_per_million=_cny(chat.output_price_micro_cny_per_million),
        assistant_chat_daily_budget_cny=_cny(budgets.chat_daily_micro_cny),
        assistant_query_embedding_daily_budget_cny=_cny(budgets.query_embedding_daily_micro_cny),
        assistant_index_embedding_daily_budget_cny=_cny(budgets.index_embedding_daily_micro_cny),
        assistant_embedding_provider=embedding.protocol,
        assistant_embedding_model=embedding.model,
        assistant_embedding_model_version=embedding.model_version,
        assistant_embedding_dimension=embedding.dimension,
        assistant_embedding_max_batch_items=embedding.max_batch_items,
        assistant_embedding_endpoint="https://provider.invalid/v1",
        assistant_embedding_api_key="test-secret-not-written",
        assistant_embedding_input_price_cny_per_million=_cny(
            embedding.input_price_micro_cny_per_million
        ),
        assistant_provider_timeout_seconds=chat.timeout_seconds,
        assistant_readiness_hmac_secret="qualification-ready-secret-value-32bytes",
    )


class _BoundChat:
    def __init__(self, *, usage: bool = True) -> None:
        self.usage = usage
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        token_usage = (
            {"prompt_tokens": 9, "completion_tokens": 4, "total_tokens": 13} if self.usage else {}
        )
        raw = SimpleNamespace(
            response_metadata={
                "finish_reason": "stop",
                "model_name": "chat-final",
                "model_version": "2026-08-01",
                "token_usage": token_usage,
            },
            usage_metadata={},
        )
        return {
            "raw": raw,
            "parsed": ModelAnswer.model_validate(
                {"blocks": [{"text": "qualification-ok", "citation_ids": []}]}
            ),
            "parsing_error": None,
        }


class _Chat:
    def __init__(self, bound: _BoundChat) -> None:
        self.bound = bound

    def with_structured_output(self, schema, **kwargs):
        assert schema is ModelAnswer
        assert kwargs == {"method": "json_schema", "strict": True, "include_raw": True}
        return self.bound


class _Embeddings:
    def __init__(self, profile: QualificationProfile, *, usage: bool = True) -> None:
        self.profile = profile
        self.usage = usage
        self.calls = 0

    def embed_documents_metered(self, texts: list[str]) -> EmbeddingUsage:
        self.calls += 1
        dimension = self.profile.providers.embedding.dimension
        return EmbeddingUsage(
            vectors=[[0.0] * dimension for _ in texts],
            input_tokens=7 if self.usage else None,
            usage_source="provider-response" if self.usage else "unknown",
            model=self.profile.providers.embedding.model,
            model_identity_source="provider-response",
            version=self.profile.providers.embedding.model_version,
            version_identity_source="versioned-provider-contract",
        )


class _BatchEndpoint:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def create(self, *, model: str, input: list[str], dimensions: int, encoding_format: str):
        assert encoding_format == "float"
        self.calls.append(input)
        return SimpleNamespace(
            model=model,
            data=[SimpleNamespace(embedding=[0.0] * dimensions) for _ in input],
            usage=SimpleNamespace(prompt_tokens=len(input)),
        )


def _clock() -> Callable[[], datetime]:
    current = datetime(2026, 8, 30, 10, 0, tzinfo=UTC)

    def now() -> datetime:
        nonlocal current
        value = current
        current += timedelta(seconds=1)
        return value

    return now


def test_probe_requires_explicit_selection_and_exact_profile_digest(tmp_path: Path) -> None:
    profile = _profile(tmp_path)
    calls = 0

    def chat_factory(_settings):
        nonlocal calls
        calls += 1
        return _Chat(_BoundChat())

    with pytest.raises(ProviderQualificationError, match="select at least one"):
        run_provider_probe(
            settings=_settings(profile),
            profile=profile,
            approved_profile_digest=profile_digest(profile),
            ledger_path=tmp_path / "ledger.json",
            output_path=tmp_path / "probe.json",
            probe_chat=False,
            probe_embedding=False,
            chat_factory=chat_factory,
        )
    with pytest.raises(ProviderQualificationError, match="digest approval"):
        run_provider_probe(
            settings=_settings(profile),
            profile=profile,
            approved_profile_digest="sha256:" + "0" * 64,
            ledger_path=tmp_path / "ledger.json",
            output_path=tmp_path / "probe.json",
            probe_chat=True,
            probe_embedding=False,
            chat_factory=chat_factory,
        )
    assert calls == 0
    assert not (tmp_path / "ledger.json").exists()


def test_real_embedding_adapter_enforces_approved_batch_cap() -> None:
    endpoint = _BatchEndpoint()
    embeddings = OpenAICompatibleMeteredEmbeddings(
        model="embedding-final",
        version="2026-08-01",
        api_key="not-used-by-fake-endpoint",
        base_url="https://provider.invalid/v1",
        dimension=8,
        timeout=30,
        max_batch_items=2,
    )
    embeddings._client = SimpleNamespace(embeddings=endpoint)

    result = embeddings.embed_documents_metered(["a", "b", "c", "d", "e"])

    assert [len(batch) for batch in endpoint.calls] == [2, 2, 1]
    assert len(result.vectors) == 5
    assert result.input_tokens == 5
    assert result.usage_source == "provider-response"


def test_probe_records_allowlisted_real_provider_facts_and_bounded_cost(
    tmp_path: Path,
) -> None:
    profile = _profile(tmp_path)
    chat = _BoundChat()
    embedding = _Embeddings(profile)
    output = tmp_path / "probe.json"
    result = run_provider_probe(
        settings=_settings(profile),
        profile=profile,
        approved_profile_digest=profile_digest(profile),
        ledger_path=tmp_path / "ledger.json",
        output_path=output,
        probe_chat=True,
        probe_embedding=True,
        now=_clock(),
        chat_factory=lambda _settings: _Chat(chat),
        embedding_factory=lambda _settings: embedding,
    )
    assert result["chat"]["status"] == "pass"
    assert result["embedding"]["status"] == "pass"
    assert result["ledger"]["calls_used"] == 2
    assert result["ledger"]["within_envelope"] is True
    assert chat.calls == embedding.calls == 1
    assert validate_provider_probe_artifact(output, profile, _settings(profile)) == result
    assert provider_probe_digest(output).startswith("sha256:")
    serialized = output.read_text(encoding="utf-8")
    assert "qualification-ok" not in serialized
    assert "provider.invalid" not in serialized
    assert "test-secret" not in serialized
    drifted_settings = _settings(profile).model_copy(
        update={"assistant_chat_endpoint": "https://different-provider.invalid/v1"}
    )
    with pytest.raises(ProviderQualificationError, match="endpoint binding has drifted"):
        validate_provider_probe_artifact(output, profile, drifted_settings)
    ledger = json.loads((tmp_path / "ledger.json").read_text(encoding="utf-8"))
    assert [item["status"] for item in ledger["attempts"]] == [
        "succeeded",
        "succeeded",
    ]

    tampered = json.loads(serialized)
    tampered["chat"]["status"] = "measured_fail"
    output.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ProviderQualificationError, match="measured failure"):
        validate_provider_probe_artifact(output, profile, _settings(profile))


def test_missing_usage_is_measured_fail_and_conservatively_settled(tmp_path: Path) -> None:
    profile = _profile(tmp_path)
    chat = _BoundChat(usage=False)
    result = run_provider_probe(
        settings=_settings(profile),
        profile=profile,
        approved_profile_digest=profile_digest(profile),
        ledger_path=tmp_path / "ledger.json",
        output_path=tmp_path / "probe.json",
        probe_chat=True,
        probe_embedding=False,
        now=_clock(),
        chat_factory=lambda _settings: _Chat(chat),
    )
    assert result["chat"]["status"] == "measured_fail"
    assert result["chat"]["usage_proven"] is False
    assert result["chat"]["settled_micro_cny"] == result["chat"]["reserved_micro_cny"]
    assert result["chat"]["input_tokens"] is None


def test_cost_envelope_blocks_before_network_call(tmp_path: Path) -> None:
    data = valid_profile_data()
    data["storage"]["paths"]["qualification_root"] = str(tmp_path.resolve())
    data["providers"]["budgets"]["qualification_max_micro_cny"] = 1
    profile = QualificationProfile.model_validate(data)
    calls = 0

    def factory(_settings):
        nonlocal calls
        calls += 1
        return _Chat(_BoundChat())

    with pytest.raises(ProviderQualificationError, match="cost envelope"):
        run_provider_probe(
            settings=_settings(profile),
            profile=profile,
            approved_profile_digest=profile_digest(profile),
            ledger_path=tmp_path / "ledger.json",
            output_path=tmp_path / "probe.json",
            probe_chat=True,
            probe_embedding=False,
            chat_factory=factory,
        )
    assert calls == 0


def test_embedding_probe_counts_provider_batches_in_call_envelope(tmp_path: Path) -> None:
    data = valid_profile_data()
    data["storage"]["paths"]["qualification_root"] = str(tmp_path.resolve())
    data["providers"]["embedding"]["max_batch_items"] = 1
    profile = QualificationProfile.model_validate(data)

    result = run_provider_probe(
        settings=_settings(profile),
        profile=profile,
        approved_profile_digest=profile_digest(profile),
        ledger_path=tmp_path / "ledger.json",
        output_path=tmp_path / "probe.json",
        probe_chat=False,
        probe_embedding=True,
        now=_clock(),
        embedding_factory=lambda _settings: _Embeddings(profile),
    )

    assert result["embedding"]["call_count"] == 2
    assert result["ledger"]["calls_used"] == 2


def _local_probe_inputs(tmp_path, monkeypatch, **model_options):
    from app.assistant_qualification import provider_probe as module

    from .test_assistant_deepseek import _model

    monkeypatch.setattr(module, "__file__", str(tmp_path / "app/assistant_qualification/probe.py"))
    settings = Settings(
        _env_file=None,
        environment="development",
        assistant_online_enabled=False,
        assistant_chat_provider="openai-compatible",
        assistant_chat_endpoint="https://api.deepseek.com",
        assistant_chat_model="deepseek-v4-flash",
        assistant_chat_model_version="DeepSeek-V4-Flash-0731",
        assistant_chat_api_key="synthetic-private-key",
        assistant_chat_max_input_tokens=8000,
        assistant_chat_max_output_tokens=512,
        assistant_chat_context_window_tokens=1_000_000,
        assistant_chat_input_price_cny_per_million=Decimal("3"),
        assistant_chat_output_price_cny_per_million=Decimal("9"),
        assistant_chat_daily_budget_cny=Decimal("2"),
        assistant_provider_timeout_seconds=45,
        assistant_readiness_hmac_secret="synthetic-private-control-secret-0001",
    )
    chat, requests = _model(
        content=model_options.pop(
            "content", '{"blocks":[{"text":"qualification-ok","citation_ids":[],"supports":[]}]}'
        ),
        **model_options,
    )
    args = dict(
        settings=settings,
        ledger_path=tmp_path / "data/ledger.json",
        output_path=tmp_path / "data/probe.json",
        approved_max_micro_cny=1_000_000,
        max_calls=1,
        chat_factory=lambda _: chat,
    )
    return args, requests


def test_local_chat_probe_preconditions_and_allowlisted_result(tmp_path, monkeypatch):
    args, requests = _local_probe_inputs(tmp_path, monkeypatch)
    for change in (
        {"environment": "production"},
        {"assistant_online_enabled": True},
        {"assistant_chat_max_output_tokens": None},
        {"assistant_chat_model_version": "unknown"},
        {"assistant_chat_max_input_tokens": 1},
    ):
        with pytest.raises(ProviderQualificationError):
            run_local_chat_probe(**{**args, "settings": args["settings"].model_copy(update=change)})
    assert not requests and not args["ledger_path"].exists()
    result = run_local_chat_probe(**args)
    assert result["scope"] == "local-development-chat" and not result["production_qualified"]
    assert result["chat"]["status"] == "pass"
    assert result["chat"]["application_schema"] is True and not result["chat"]["strict_schema"]
    assert result["chat"]["model_identity_source"] == "provider-response"
    assert result["chat"]["version_identity_source"] == "versioned-provider-contract"
    assert result["ledger"]["calls_used"] == 1
    text = args["output_path"].read_text()
    assert "synthetic-private" not in text and "qualification-ok" not in text
    assert "messages" not in text and "blocks" not in text
    assert len(requests) == 1


def test_local_chat_probe_reuses_budget_and_rejects_drift(tmp_path, monkeypatch):
    args, requests = _local_probe_inputs(tmp_path, monkeypatch)
    with pytest.raises(ProviderQualificationError, match="cost envelope"):
        run_local_chat_probe(**{**args, "approved_max_micro_cny": 1})
    assert not requests
    result = run_local_chat_probe(**args)
    assert result["chat"]["settled_micro_cny"] == 540
    with pytest.raises(ProviderQualificationError, match="call envelope"):
        run_local_chat_probe(**args)
    with pytest.raises(ProviderQualificationError, match="another profile"):
        run_local_chat_probe(**{**args, "max_calls": 2})
    assert len(requests) == 1
    args, requests = _local_probe_inputs(tmp_path / "unknown", monkeypatch, usage=False)
    result = run_local_chat_probe(**args)
    assert result["chat"]["status"] == "measured_fail"
    assert result["chat"]["settled_micro_cny"] == result["chat"]["reserved_micro_cny"]
    with pytest.raises(ProviderQualificationError, match="unresolved or failed"):
        run_local_chat_probe(**args)
    assert len(requests) == 1


def test_local_chat_probe_cannot_be_production_qualification(tmp_path, monkeypatch):
    args, _ = _local_probe_inputs(tmp_path, monkeypatch)
    run_local_chat_probe(**args)
    profile = _profile(tmp_path)
    with pytest.raises(ProviderQualificationError):
        validate_provider_probe_artifact(args["output_path"], profile, _settings(profile))
    args, requests = _local_probe_inputs(tmp_path / "invalid", monkeypatch, content='{"blocks":[]}')
    result = run_local_chat_probe(**args)
    assert result["chat"]["status"] == "measured_fail" and len(requests) == 1
    assert result["chat"]["strict_schema"] is False
