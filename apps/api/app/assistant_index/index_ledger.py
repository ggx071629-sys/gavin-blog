from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal
from typing import cast

from langchain_core.embeddings import Embeddings
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..assistant.constants import (
    ATTEMPT_DEFERRED,
    ATTEMPT_PREPARED,
    ATTEMPT_SENDING,
    ATTEMPT_SUCCEEDED,
    ATTEMPT_UNKNOWN,
)
from ..assistant.crypto import random_id
from ..assistant.money import cny_to_micro, snapshot_json, tokens_cost_micro
from ..assistant.providers import EmbeddingUsage, MeteredEmbeddings
from ..assistant.time_beijing import beijing_date
from ..models import AssistantIndexEmbeddingAttempt, AssistantIndexEmbeddingBudget
from .runtime import AssistantIndexRuntime
from .worker_control import (
    FenceHeartbeat,
    WorkerFenceLost,
    record_provider_fact,
    require_worker_fence,
)


class UnknownIndexEmbeddingError(RuntimeError):
    """Raised when an index embedding attempt is already sending or unknown."""


class DeferredIndexEmbeddingError(RuntimeError):
    """Raised when the index embedding budget is exhausted until the next Beijing day."""


class UnavailableIndexVectorsError(UnknownIndexEmbeddingError):
    """A previous call succeeded, but its vectors are not available for reuse."""


class LedgeredIndexEmbeddings(MeteredEmbeddings):
    def __init__(
        self,
        inner: Embeddings,
        runtime: AssistantIndexRuntime,
        db: Session,
        *,
        task_id: int | None = None,
        generation_id: int | None = None,
        worker_fence: int | None = None,
        lease_token: str | None = None,
    ) -> None:
        self.inner = inner
        self.runtime = runtime
        self.db = db
        self.task_id = task_id
        self.generation_id = generation_id
        self.worker_fence = worker_fence
        self.lease_token = lease_token

    def embed_documents_metered(self, texts: list[str]) -> EmbeddingUsage:
        return _metered_call(
            self.runtime,
            self.db,
            self.inner,
            texts,
            task_id=self.task_id,
            generation_id=self.generation_id,
            worker_fence=self.worker_fence,
            lease_token=self.lease_token,
        )

    def embed_query(self, text: str) -> list[float]:
        return self.embed_query_metered(text).vector

    def embed_query_metered(self, text: str) -> EmbeddingUsage:
        return self.embed_documents_metered([text])


def _metered_call(
    runtime: AssistantIndexRuntime,
    db: Session,
    inner: Embeddings,
    texts: list[str],
    *,
    task_id: int | None,
    generation_id: int | None,
    worker_fence: int | None,
    lease_token: str | None,
) -> EmbeddingUsage:
    settings = runtime.settings
    from ..assistant.total_budget import question_headroom, reserve, settle

    # Take the shared authority write lock before reading its remaining balance.
    db.execute(text("UPDATE assistant_budget_policy SET version=version WHERE id=1"))
    if worker_fence is not None:
        require_worker_fence(
            runtime,
            worker_fence,
            task_id=task_id,
            token=lease_token,
        )
    price = settings.assistant_embedding_input_price_cny_per_million or Decimal("0")
    cap = cny_to_micro(settings.assistant_index_embedding_daily_budget_cny or Decimal("0"))
    tokenizer = getattr(inner, "tokenizer", None)
    estimate = tokens_cost_micro(
        sum(
            tokenizer.count("passage: " + text)
            if tokenizer is not None
            else max(1, math.ceil(len(text) / 4))
            for text in texts
        ),
        price,
    )
    fingerprint = hashlib.sha256("\n".join(texts).encode()).hexdigest()
    now = runtime.now()
    day = beijing_date(now).isoformat()
    existing = (
        db.query(AssistantIndexEmbeddingAttempt)
        .filter_by(request_fingerprint=fingerprint, generation_id=generation_id)
        .order_by(AssistantIndexEmbeddingAttempt.created_at.desc())
        .first()
    )
    if existing is not None:
        if existing.status == ATTEMPT_SUCCEEDED:
            raise UnavailableIndexVectorsError(
                "index embedding result cannot be reused without stored vectors"
            )
        if existing.status in {ATTEMPT_SENDING, ATTEMPT_UNKNOWN}:
            raise UnknownIndexEmbeddingError(
                "index embedding attempt is unknown and must not be resent"
            )
    budget = db.get(AssistantIndexEmbeddingBudget, day)
    if budget is None:
        budget = AssistantIndexEmbeddingBudget(beijing_date=day)
        db.add(budget)
        db.flush()
    if budget.circuit_open or budget.settled_micro_cny + budget.reserved_micro_cny + estimate > cap:
        attempt = AssistantIndexEmbeddingAttempt(
            id=random_id(),
            task_id=task_id,
            generation_id=generation_id,
            request_fingerprint=fingerprint,
            fencing_token=str(worker_fence) if worker_fence is not None else random_id(),
            price_snapshot_json=snapshot_json(
                input_cny_per_million=price, output_cny_per_million=price
            ),
            beijing_date=day,
            status=ATTEMPT_DEFERRED,
            max_cost_micro_cny=estimate,
            created_at=now,
            updated_at=now,
        )
        db.add(attempt)
        db.flush()
        raise DeferredIndexEmbeddingError("index embedding budget exhausted")
    common_id = random_id()
    if not reserve(
        db,
        settings,
        day=day,
        entries=[
            {
                "id": f"index:{common_id}",
                "kind": "index_embedding",
                "scope": "index",
                "reserved_micro_cny": estimate,
            }
        ],
        headroom=question_headroom(settings),
    ):
        raise DeferredIndexEmbeddingError("shared budget preserves question headroom")
    attempt = AssistantIndexEmbeddingAttempt(
        id=common_id,
        task_id=task_id,
        generation_id=generation_id,
        request_fingerprint=fingerprint,
        fencing_token=str(worker_fence) if worker_fence is not None else random_id(),
        price_snapshot_json=snapshot_json(
            input_cny_per_million=price, output_cny_per_million=price
        ),
        beijing_date=day,
        status=ATTEMPT_PREPARED,
        max_cost_micro_cny=estimate,
        created_at=now,
        updated_at=now,
    )
    db.add(attempt)
    budget.reserved_micro_cny += estimate
    db.flush()
    attempt.status = ATTEMPT_SENDING
    attempt.updated_at = now
    db.commit()
    try:
        heartbeat = (
            FenceHeartbeat(
                runtime,
                worker_fence,
                task_id=task_id,
                token=lease_token,
            )
            if worker_fence is not None
            else None
        )
        if heartbeat is None:
            if isinstance(inner, MeteredEmbeddings):
                usage = inner.embed_documents_metered(texts)
            else:
                vectors = inner.embed_documents(texts)
                usage = EmbeddingUsage(
                    vectors=vectors,
                    input_tokens=None,
                    usage_source="unknown",
                    model=str(runtime.settings.assistant_embedding_model or "unknown"),
                    model_identity_source="operator-declaration",
                    version=str(runtime.settings.assistant_embedding_model_version or "unknown"),
                    version_identity_source="operator-declaration",
                )
        else:
            with heartbeat:
                if isinstance(inner, MeteredEmbeddings):
                    usage = inner.embed_documents_metered(texts)
                else:
                    vectors = inner.embed_documents(texts)
                    usage = EmbeddingUsage(
                        vectors=vectors,
                        input_tokens=None,
                        usage_source="unknown",
                        model=str(runtime.settings.assistant_embedding_model or "unknown"),
                        model_identity_source="operator-declaration",
                        version=str(
                            runtime.settings.assistant_embedding_model_version or "unknown"
                        ),
                        version_identity_source="operator-declaration",
                    )
            require_worker_fence(
                runtime,
                cast(int, worker_fence),
                task_id=task_id,
                token=lease_token,
            )
    except Exception as exc:
        attempt.status = ATTEMPT_UNKNOWN
        attempt.settled_micro_cny = estimate
        attempt.updated_at = runtime.now()
        budget.settled_micro_cny += estimate
        budget.reserved_micro_cny -= estimate
        budget.circuit_open = 1
        settle(db, f"index:{attempt.id}", estimate)
        db.commit()
        record_provider_fact(
            runtime,
            kind="index_embedding",
            status="unknown",
            reason="provider_result_unknown"
            if not isinstance(exc, WorkerFenceLost)
            else "worker_fence_lost",
            outcome="unknown",
        )
        raise UnknownIndexEmbeddingError("index embedding result unknown") from exc
    input_tokens = usage.input_tokens
    usage_known = input_tokens is not None and input_tokens > 0
    settled = tokens_cost_micro(input_tokens, price) if input_tokens else estimate
    circuit = settled > estimate or (bool(texts) and not usage_known)
    attempt.status = ATTEMPT_SUCCEEDED
    attempt.input_tokens = usage.input_tokens
    attempt.usage_json = json.dumps(
        {
            "input_tokens": usage.input_tokens,
            "usage_source": usage.usage_source,
            "model": usage.model,
            "model_identity_source": usage.model_identity_source,
            "version": usage.version,
            "version_identity_source": usage.version_identity_source,
        },
        sort_keys=True,
    )
    attempt.settled_micro_cny = max(settled, estimate if circuit else settled)
    attempt.updated_at = runtime.now()
    budget.reserved_micro_cny -= estimate
    budget.settled_micro_cny += attempt.settled_micro_cny
    if circuit:
        budget.circuit_open = 1
    settle(db, f"index:{attempt.id}", attempt.settled_micro_cny)
    db.commit()
    record_provider_fact(
        runtime,
        kind="index_embedding",
        status="healthy" if usage_known else "unknown",
        reason="provider_call_succeeded" if usage_known else "provider_usage_unknown",
        outcome="success" if usage_known else "unknown",
    )
    return usage


def has_blocking_index_attempts(db: Session, generation_id: int | None = None) -> bool:
    query = db.query(AssistantIndexEmbeddingAttempt).filter(
        AssistantIndexEmbeddingAttempt.status.in_((ATTEMPT_SENDING, ATTEMPT_UNKNOWN))
    )
    if generation_id is not None:
        query = query.filter(AssistantIndexEmbeddingAttempt.generation_id == generation_id)
    return query.first() is not None
