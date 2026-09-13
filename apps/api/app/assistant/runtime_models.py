from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class RuntimeBase(DeclarativeBase):
    pass


class RuntimeMeta(RuntimeBase):
    __tablename__ = "assistant_runtime_meta"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class AssistantSession(RuntimeBase):
    __tablename__ = "assistant_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_hmac: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_hmac: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime)
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime)
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime)
    tombstoned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fencing_epoch: Mapped[int] = mapped_column(Integer, default=0)
    persisted_bytes: Mapped[int] = mapped_column(Integer, default=0)
    cleanup_breaker: Mapped[int] = mapped_column(Integer, default=0)


class AssistantTurn(RuntimeBase):
    __tablename__ = "assistant_turns"
    __table_args__ = (
        UniqueConstraint("session_id", "idempotency_hmac", name="uq_assistant_turns_idempotency"),
        CheckConstraint(
            "status IN ('accepted', 'running', 'terminal', 'revoking')",
            name="ck_assistant_turns_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("assistant_sessions.id"),
        index=True,
    )
    idempotency_hmac: Mapped[str] = mapped_column(String(64), index=True)
    payload_hmac: Mapped[str] = mapped_column(String(64))
    thread_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="accepted")
    question: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    dense_skipped: Mapped[int] = mapped_column(Integer, default=0)
    generation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    terminal_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    terminal_event: Mapped[str | None] = mapped_column(String(16), nullable=True)
    terminal_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    terminal_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    citations_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    sources_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_purged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    checkpoint_deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    runner_quiescent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    preflight_blocked: Mapped[int] = mapped_column(Integer, default=0)
    execution_epoch: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_hmac: Mapped[str | None] = mapped_column(String(64), nullable=True)
    operational_epoch: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AssistantHistory(RuntimeBase):
    __tablename__ = "assistant_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("assistant_sessions.id"), index=True)
    turn_id: Mapped[str] = mapped_column(ForeignKey("assistant_turns.id"), unique=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    purged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AssistantAttempt(RuntimeBase):
    __tablename__ = "assistant_attempts"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('chat', 'query_embedding')",
            name="ck_assistant_attempts_kind",
        ),
        CheckConstraint(
            "status IN ('prepared', 'sending', 'succeeded', 'unknown', 'failed')",
            name="ck_assistant_attempts_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    turn_id: Mapped[str] = mapped_column(ForeignKey("assistant_turns.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="prepared")
    fencing_token: Mapped[str] = mapped_column(String(64))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    price_snapshot_json: Mapped[str] = mapped_column(Text)
    beijing_date: Mapped[str] = mapped_column(String(10), index=True)
    max_cost_micro: Mapped[int] = mapped_column(Integer)
    settled_micro: Mapped[int] = mapped_column(Integer, default=0)
    usage_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    finish_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    parsed_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    vector_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class AssistantChatBudget(RuntimeBase):
    __tablename__ = "assistant_chat_budgets"

    beijing_date: Mapped[str] = mapped_column(String(10), primary_key=True)
    reserved_micro: Mapped[int] = mapped_column(Integer, default=0)
    settled_micro: Mapped[int] = mapped_column(Integer, default=0)
    circuit_open: Mapped[int] = mapped_column(Integer, default=0)


class AssistantQueryEmbeddingBudget(RuntimeBase):
    __tablename__ = "assistant_query_embedding_budgets"

    beijing_date: Mapped[str] = mapped_column(String(10), primary_key=True)
    reserved_micro: Mapped[int] = mapped_column(Integer, default=0)
    settled_micro: Mapped[int] = mapped_column(Integer, default=0)
    circuit_open: Mapped[int] = mapped_column(Integer, default=0)


class AssistantRateEvent(RuntimeBase):
    __tablename__ = "assistant_rate_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip_hmac: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    beijing_date: Mapped[str] = mapped_column(String(10), index=True)


class AssistantLease(RuntimeBase):
    __tablename__ = "assistant_leases"
    __table_args__ = (
        UniqueConstraint("scope", "scope_key", "owner_turn_id", name="uq_assistant_leases_owner"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(16))
    scope_key: Mapped[str] = mapped_column(String(80))
    fencing_token: Mapped[str] = mapped_column(String(64))
    owner_turn_id: Mapped[str] = mapped_column(String(64), index=True)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    beijing_date: Mapped[str] = mapped_column(String(10))


class AssistantEvent(RuntimeBase):
    __tablename__ = "assistant_event_journal"
    __table_args__ = (UniqueConstraint("turn_id", "seq", name="uq_assistant_events_turn_seq"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    turn_id: Mapped[str] = mapped_column(ForeignKey("assistant_turns.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    event_name: Mapped[str] = mapped_column(String(32))
    data_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class AssistantReadinessReceipt(RuntimeBase):
    __tablename__ = "assistant_readiness_receipts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    receipt_json: Mapped[str] = mapped_column(Text)
    receipt_hmac: Mapped[str] = mapped_column(String(64))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class AssistantCleanupState(RuntimeBase):
    __tablename__ = "assistant_cleanup_state"
    __table_args__ = (CheckConstraint("id = 1", name="ck_assistant_cleanup_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    breaker_open: Mapped[int] = mapped_column(Integer, default=0)
    last_sweep_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(240), nullable=True)


class AssistantCleanupRetry(RuntimeBase):
    __tablename__ = "assistant_cleanup_retries"
    __table_args__ = (UniqueConstraint("kind", "target_id", name="uq_assistant_cleanup_retry"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(40))
    target_id: Mapped[str] = mapped_column(String(80))
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    last_error: Mapped[str] = mapped_column(String(240))
    last_attempt_at: Mapped[datetime] = mapped_column(DateTime)


class AssistantOperationalGate(RuntimeBase):
    __tablename__ = "assistant_operational_gate"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_assistant_operational_gate_singleton"),
        CheckConstraint(
            "requested_state IN ('disabled', 'enabled')",
            name="ck_assistant_operational_gate_requested",
        ),
        CheckConstraint(
            "effective_state IN ('disabled', 'enabled', 'blocked')",
            name="ck_assistant_operational_gate_effective",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requested_state: Mapped[str] = mapped_column(String(16))
    effective_state: Mapped[str] = mapped_column(String(16))
    version: Mapped[int] = mapped_column(Integer, default=1)
    operational_epoch: Mapped[int] = mapped_column(Integer, default=1)
    readiness_receipt_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    config_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    active_generation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    switch_pending_operation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    switch_target_generation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    switch_finalize_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    blocked_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class AssistantMeteredEvent(RuntimeBase):
    __tablename__ = "assistant_metered_events"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('chat', 'query_embedding')",
            name="ck_assistant_metered_events_kind",
        ),
    )

    event_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    beijing_date: Mapped[str] = mapped_column(String(10), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    outcome: Mapped[str] = mapped_column(String(32))
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_micro: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class AssistantProviderFact(RuntimeBase):
    __tablename__ = "assistant_provider_facts"

    kind: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(16))
    reason_code: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(16))
    observed_at: Mapped[datetime] = mapped_column(DateTime)


class AssistantActivityEvent(RuntimeBase):
    __tablename__ = "assistant_activity_events"

    event_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    beijing_date: Mapped[str] = mapped_column(String(10), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    outcome: Mapped[str] = mapped_column(String(32))
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
