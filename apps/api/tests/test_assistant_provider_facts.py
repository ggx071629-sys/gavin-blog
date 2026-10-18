from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from langchain_core.embeddings import Embeddings

from app.assistant.graph import _settle_chat, _usage_from_raw
from app.assistant.providers import OpenAICompatibleMeteredEmbeddings
from app.assistant_index.index_ledger import (
    DeferredIndexEmbeddingError,
    LedgeredIndexEmbeddings,
)
from app.assistant_index.runtime import build_test_runtime
from app.models import AssistantIndexEmbeddingAttempt, AssistantIndexEmbeddingBudget


class _EmbeddingsApi:
    def __init__(self, response) -> None:
        self.response = response

    def create(self, **_kwargs):
        return self.response


class _Client:
    def __init__(self, response) -> None:
        self.embeddings = _EmbeddingsApi(response)


def _adapter(response) -> OpenAICompatibleMeteredEmbeddings:
    adapter = object.__new__(OpenAICompatibleMeteredEmbeddings)
    adapter.model = "operator-model"
    adapter.version = "operator-version"
    adapter.dimension = 2
    adapter.max_batch_items = 64
    adapter._client = _Client(response)
    return adapter


def test_embedding_missing_usage_and_identity_are_unknown_not_estimated() -> None:
    response = SimpleNamespace(
        data=[SimpleNamespace(embedding=[0.25, 0.75])],
        usage=None,
        model=None,
    )
    usage = _adapter(response).embed_documents_metered(["a long input still is not token usage"])

    assert usage.input_tokens is None
    assert usage.usage_source == "unknown"
    assert usage.model == "operator-model"
    assert usage.model_identity_source == "operator-declaration"
    assert usage.version == "operator-version"
    assert usage.version_identity_source == "operator-declaration"


def test_embedding_preserves_only_provider_reported_usage_and_model() -> None:
    response = SimpleNamespace(
        data=[SimpleNamespace(embedding=[0.25, 0.75])],
        usage=SimpleNamespace(prompt_tokens=17),
        model="provider-returned-model",
    )
    usage = _adapter(response).embed_documents_metered(["input"])

    assert usage.input_tokens == 17
    assert usage.usage_source == "provider-response"
    assert usage.model == "provider-returned-model"
    assert usage.model_identity_source == "provider-response"
    assert usage.version_identity_source == "operator-declaration"


def test_chat_missing_usage_is_nullable_and_conservatively_settled() -> None:
    raw = SimpleNamespace(
        response_metadata={"finish_reason": "stop", "model_name": "reported-model"},
        usage_metadata=None,
    )
    finish, usage = _usage_from_raw(raw)
    online = SimpleNamespace(
        settings=SimpleNamespace(
            assistant_chat_input_price_cny_per_million=Decimal("1"),
            assistant_chat_output_price_cny_per_million=Decimal("1"),
        )
    )

    assert finish == "stop"
    assert usage["input_tokens"] is None
    assert usage["output_tokens"] is None
    assert usage["usage_source"] == "unknown"
    assert usage["model"] == "reported-model"
    assert usage["model_identity_source"] == "provider-response"
    assert _settle_chat(online, usage, 900) == (900, True)


def test_chat_missing_finish_reason_is_not_silently_stop() -> None:
    finish, usage = _usage_from_raw(
        SimpleNamespace(
            response_metadata={
                "token_usage": {"prompt_tokens": 10, "completion_tokens": 5}
            },
            usage_metadata=None,
        )
    )
    assert finish == "unknown"
    assert usage["usage_source"] == "provider-response"


class _UnmeteredEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def test_index_unmetered_adapter_opens_circuit_and_records_nullable_usage(client) -> None:
    settings = client.app.state.settings.model_copy(
        update={
            "assistant_embedding_model": "operator-model",
            "assistant_embedding_model_version": "operator-version",
            "assistant_embedding_dimension": 8,
            "assistant_embedding_input_price_cny_per_million": Decimal("0.10"),
            "assistant_index_embedding_daily_budget_cny": Decimal("1.00"),
        }
    )
    runtime = build_test_runtime(settings, client.app.state.database)
    with client.app.state.database.session_factory() as db:
        usage = LedgeredIndexEmbeddings(
            _UnmeteredEmbeddings(), runtime, db, generation_id=9101
        ).embed_documents_metered(["provider returned a vector without usage"])
        attempt = db.query(AssistantIndexEmbeddingAttempt).filter_by(generation_id=9101).one()
        budget = db.query(AssistantIndexEmbeddingBudget).one()

        assert usage.input_tokens is None
        assert attempt.input_tokens is None
        assert json.loads(attempt.usage_json)["usage_source"] == "unknown"
        assert budget.circuit_open == 1
        assert attempt.settled_micro_cny == attempt.max_cost_micro_cny

        with pytest.raises(DeferredIndexEmbeddingError):
            LedgeredIndexEmbeddings(
                _UnmeteredEmbeddings(), runtime, db, generation_id=9102
            ).embed_documents_metered(["must not send after unknown usage"])
