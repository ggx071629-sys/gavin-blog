"""Create assistant runtime control tables.

Revision ID: 20260828_rt0001
Revises:

Control-plane only. This migration must never create, drop, rename, or
alter LangGraph saver tables (checkpoints, writes).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260828_rt0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assistant_runtime_meta",
        sa.Column("key", sa.String(length=80), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
    )
    op.create_table(
        "assistant_sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("session_hmac", sa.String(length=64), nullable=False),
        sa.Column("csrf_hmac", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(), nullable=False),
        sa.Column("tombstoned_at", sa.DateTime(), nullable=True),
        sa.Column("fencing_epoch", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("persisted_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cleanup_breaker", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("session_hmac", name="uq_assistant_sessions_hmac"),
    )
    op.create_table(
        "assistant_turns",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("idempotency_hmac", sa.String(length=64), nullable=False),
        sa.Column("payload_hmac", sa.String(length=64), nullable=False),
        sa.Column("thread_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="accepted"),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("current_path", sa.String(length=300), nullable=True),
        sa.Column("dense_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("generation_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("terminal_at", sa.DateTime(), nullable=True),
        sa.Column("terminal_event", sa.String(length=16), nullable=True),
        sa.Column("terminal_code", sa.String(length=64), nullable=True),
        sa.Column("terminal_message", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("citations_json", sa.Text(), nullable=True),
        sa.Column("sources_json", sa.Text(), nullable=True),
        sa.Column("body_purged_at", sa.DateTime(), nullable=True),
        sa.Column("checkpoint_deleted_at", sa.DateTime(), nullable=True),
        sa.Column("runner_quiescent_at", sa.DateTime(), nullable=True),
        sa.Column("preflight_blocked", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["session_id"], ["assistant_sessions.id"]),
        sa.UniqueConstraint(
            "session_id",
            "idempotency_hmac",
            name="uq_assistant_turns_idempotency",
        ),
        sa.CheckConstraint(
            "status IN ('accepted', 'running', 'terminal', 'revoking')",
            name="ck_assistant_turns_status",
        ),
    )
    op.create_index("ix_assistant_turns_session_id", "assistant_turns", ["session_id"])
    op.create_index("ix_assistant_turns_idempotency_hmac", "assistant_turns", ["idempotency_hmac"])
    op.create_table(
        "assistant_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("turn_id", sa.String(length=64), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("purged_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["assistant_sessions.id"]),
        sa.ForeignKeyConstraint(["turn_id"], ["assistant_turns.id"]),
        sa.UniqueConstraint("turn_id", name="uq_assistant_history_turn"),
    )
    op.create_index("ix_assistant_history_session_id", "assistant_history", ["session_id"])
    op.create_table(
        "assistant_attempts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("turn_id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="prepared"),
        sa.Column("fencing_token", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("price_snapshot_json", sa.Text(), nullable=False),
        sa.Column("beijing_date", sa.String(length=10), nullable=False),
        sa.Column("max_cost_micro", sa.Integer(), nullable=False),
        sa.Column("settled_micro", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("usage_json", sa.Text(), nullable=True),
        sa.Column("finish_reason", sa.String(length=32), nullable=True),
        sa.Column("parsed_json", sa.Text(), nullable=True),
        sa.Column("vector_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["turn_id"], ["assistant_turns.id"]),
        sa.CheckConstraint(
            "kind IN ('chat', 'query_embedding')",
            name="ck_assistant_attempts_kind",
        ),
        sa.CheckConstraint(
            "status IN ('prepared', 'sending', 'succeeded', 'unknown', 'failed')",
            name="ck_assistant_attempts_status",
        ),
    )
    op.create_index("ix_assistant_attempts_turn_id", "assistant_attempts", ["turn_id"])
    op.create_index("ix_assistant_attempts_beijing_date", "assistant_attempts", ["beijing_date"])
    op.create_table(
        "assistant_chat_budgets",
        sa.Column("beijing_date", sa.String(length=10), primary_key=True),
        sa.Column("reserved_micro", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("settled_micro", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("circuit_open", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "assistant_query_embedding_budgets",
        sa.Column("beijing_date", sa.String(length=10), primary_key=True),
        sa.Column("reserved_micro", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("settled_micro", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("circuit_open", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "assistant_rate_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ip_hmac", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("beijing_date", sa.String(length=10), nullable=False),
    )
    op.create_index("ix_assistant_rate_events_ip_hmac", "assistant_rate_events", ["ip_hmac"])
    op.create_index("ix_assistant_rate_events_kind", "assistant_rate_events", ["kind"])
    op.create_index("ix_assistant_rate_events_created_at", "assistant_rate_events", ["created_at"])
    op.create_index(
        "ix_assistant_rate_events_beijing_date",
        "assistant_rate_events",
        ["beijing_date"],
    )
    op.create_table(
        "assistant_leases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("scope_key", sa.String(length=80), nullable=False),
        sa.Column("fencing_token", sa.String(length=64), nullable=False),
        sa.Column("owner_turn_id", sa.String(length=64), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("beijing_date", sa.String(length=10), nullable=False),
        sa.UniqueConstraint("scope", "scope_key", name="uq_assistant_leases_scope_key"),
    )
    op.create_index("ix_assistant_leases_owner_turn_id", "assistant_leases", ["owner_turn_id"])
    op.create_index("ix_assistant_leases_expires_at", "assistant_leases", ["expires_at"])
    op.create_table(
        "assistant_event_journal",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("turn_id", sa.String(length=64), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("event_name", sa.String(length=32), nullable=False),
        sa.Column("data_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["turn_id"], ["assistant_turns.id"]),
        sa.UniqueConstraint("turn_id", "seq", name="uq_assistant_events_turn_seq"),
    )
    op.create_index("ix_assistant_event_journal_turn_id", "assistant_event_journal", ["turn_id"])
    op.create_table(
        "assistant_readiness_receipts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("receipt_json", sa.Text(), nullable=False),
        sa.Column("receipt_hmac", sa.String(length=64), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "assistant_cleanup_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("breaker_open", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_sweep_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(length=240), nullable=True),
        sa.CheckConstraint("id = 1", name="ck_assistant_cleanup_singleton"),
    )
    op.execute("INSERT INTO assistant_cleanup_state (id, breaker_open) VALUES (1, 0)")


def downgrade() -> None:
    op.drop_table("assistant_cleanup_state")
    op.drop_table("assistant_readiness_receipts")
    op.drop_table("assistant_event_journal")
    op.drop_table("assistant_leases")
    op.drop_table("assistant_rate_events")
    op.drop_table("assistant_query_embedding_budgets")
    op.drop_table("assistant_chat_budgets")
    op.drop_table("assistant_attempts")
    op.drop_table("assistant_history")
    op.drop_table("assistant_turns")
    op.drop_table("assistant_sessions")
    op.drop_table("assistant_runtime_meta")
