"""Add the fail-closed assistant operations control plane.

Revision ID: 20260829_rt0003
Revises: 20260829_rt0002

Only application-owned runtime tables are changed. The pinned LangGraph
``checkpoints`` and ``writes`` schemas are deliberately not inspected or
modified by this migration.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260829_rt0003"
down_revision: str | Sequence[str] | None = "20260829_rt0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assistant_operational_gate",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("requested_state", sa.String(length=16), nullable=False),
        sa.Column("effective_state", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("operational_epoch", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("readiness_receipt_id", sa.String(length=64), nullable=True),
        sa.Column("config_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("active_generation_id", sa.Integer(), nullable=True),
        sa.Column("switch_pending_operation_id", sa.String(length=64), nullable=True),
        sa.Column("switch_target_generation_id", sa.Integer(), nullable=True),
        sa.Column("switch_finalize_token", sa.String(length=64), nullable=True),
        sa.Column("blocked_reason", sa.String(length=64), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_assistant_operational_gate_singleton"),
        sa.CheckConstraint(
            "requested_state IN ('disabled', 'enabled')",
            name="ck_assistant_operational_gate_requested",
        ),
        sa.CheckConstraint(
            "effective_state IN ('disabled', 'enabled', 'blocked')",
            name="ck_assistant_operational_gate_effective",
        ),
    )
    op.execute(
        "INSERT INTO assistant_operational_gate "
        "(id, requested_state, effective_state, version, operational_epoch, updated_at) "
        "VALUES (1, 'disabled', 'disabled', 1, 1, CURRENT_TIMESTAMP)"
    )
    op.add_column("assistant_turns", sa.Column("operational_epoch", sa.Integer(), nullable=True))
    op.create_table(
        "assistant_metered_events",
        sa.Column("event_id", sa.String(length=80), primary_key=True),
        sa.Column("beijing_date", sa.String(length=10), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_micro", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('chat', 'query_embedding')",
            name="ck_assistant_metered_events_kind",
        ),
    )
    op.create_index(
        "ix_assistant_metered_events_day_kind",
        "assistant_metered_events",
        ["beijing_date", "kind"],
    )
    op.create_table(
        "assistant_provider_facts",
        sa.Column("kind", sa.String(length=32), primary_key=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('chat', 'query_embedding')",
            name="ck_assistant_provider_facts_kind",
        ),
        sa.CheckConstraint(
            "status IN ('healthy', 'degraded', 'unknown')",
            name="ck_assistant_provider_facts_status",
        ),
        sa.CheckConstraint(
            "outcome IN ('success', 'failure', 'unknown')",
            name="ck_assistant_provider_facts_outcome",
        ),
    )
    op.create_table(
        "assistant_activity_events",
        sa.Column("event_id", sa.String(length=80), primary_key=True),
        sa.Column("beijing_date", sa.String(length=10), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_assistant_activity_events_day_kind",
        "assistant_activity_events",
        ["beijing_date", "kind"],
    )


def downgrade() -> None:
    op.drop_index("ix_assistant_activity_events_day_kind", table_name="assistant_activity_events")
    op.drop_table("assistant_activity_events")
    op.drop_table("assistant_provider_facts")
    op.drop_index("ix_assistant_metered_events_day_kind", table_name="assistant_metered_events")
    op.drop_table("assistant_metered_events")
    with op.batch_alter_table("assistant_turns") as batch:
        batch.drop_column("operational_epoch")
    op.drop_table("assistant_operational_gate")
