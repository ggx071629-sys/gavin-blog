"""Add content-db assistant daily metrics and index-embedding ledger.

Revision ID: 20260828_0022
Revises: 20260828_0021

These objects contain no question/answer text, chunk bodies, vectors,
provider raw responses, or anonymous session identifiers. They belong to
the backed-up content fact database. Index attempts are owned by the
independent index Worker.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260828_0022"
down_revision: str | Sequence[str] | None = "20260828_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assistant_daily_metrics",
        sa.Column("beijing_date", sa.String(length=10), primary_key=True),
        sa.Column("chat_turns", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chat_reserved_micro_cny", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chat_settled_micro_cny", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("query_embedding_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("query_embedding_micro_cny", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("index_embedding_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("index_embedding_micro_cny", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("copied_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "assistant_index_embedding_budgets",
        sa.Column("beijing_date", sa.String(length=10), primary_key=True),
        sa.Column("reserved_micro_cny", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("settled_micro_cny", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("circuit_open", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "assistant_index_embedding_attempts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("generation_id", sa.Integer(), nullable=True),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("fencing_token", sa.String(length=64), nullable=False),
        sa.Column("price_snapshot_json", sa.Text(), nullable=False),
        sa.Column("beijing_date", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="prepared"),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("usage_json", sa.Text(), nullable=True),
        sa.Column("max_cost_micro_cny", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("settled_micro_cny", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('prepared', 'sending', 'succeeded', 'unknown', 'failed', 'deferred')",
            name="ck_assistant_index_embedding_attempts_status",
        ),
    )
    op.create_index(
        "ix_assistant_index_embedding_attempts_task_id",
        "assistant_index_embedding_attempts",
        ["task_id"],
    )
    op.create_index(
        "ix_assistant_index_embedding_attempts_generation_id",
        "assistant_index_embedding_attempts",
        ["generation_id"],
    )
    op.create_index(
        "ix_assistant_index_embedding_attempts_request_fingerprint",
        "assistant_index_embedding_attempts",
        ["request_fingerprint"],
    )
    op.create_index(
        "ix_assistant_index_embedding_attempts_beijing_date",
        "assistant_index_embedding_attempts",
        ["beijing_date"],
    )
    op.create_index(
        "ix_assistant_index_embedding_attempts_status",
        "assistant_index_embedding_attempts",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assistant_index_embedding_attempts_status",
        table_name="assistant_index_embedding_attempts",
    )
    op.drop_index(
        "ix_assistant_index_embedding_attempts_beijing_date",
        table_name="assistant_index_embedding_attempts",
    )
    op.drop_index(
        "ix_assistant_index_embedding_attempts_request_fingerprint",
        table_name="assistant_index_embedding_attempts",
    )
    op.drop_index(
        "ix_assistant_index_embedding_attempts_generation_id",
        table_name="assistant_index_embedding_attempts",
    )
    op.drop_index(
        "ix_assistant_index_embedding_attempts_task_id",
        table_name="assistant_index_embedding_attempts",
    )
    op.drop_table("assistant_index_embedding_attempts")
    op.drop_table("assistant_index_embedding_budgets")
    op.drop_table("assistant_daily_metrics")
