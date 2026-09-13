"""Capture execution identity and observable cleanup retry facts.

Revision ID: 20260829_rt0002
Revises: 20260828_rt0001

The migration only extends application-owned control tables. LangGraph's
``checkpoints`` and ``writes`` tables remain pinned and untouched.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260829_rt0002"
down_revision: str | Sequence[str] | None = "20260828_rt0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assistant_turns",
        sa.Column("execution_epoch", sa.Integer(), nullable=True),
    )
    op.add_column(
        "assistant_turns",
        sa.Column("execution_token", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "assistant_turns",
        sa.Column("ip_hmac", sa.String(length=64), nullable=True),
    )
    op.create_table(
        "assistant_cleanup_retries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("target_id", sa.String(length=80), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_error", sa.String(length=240), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("kind", "target_id", name="uq_assistant_cleanup_retry"),
    )


def downgrade() -> None:
    op.drop_table("assistant_cleanup_retries")
    with op.batch_alter_table("assistant_turns") as batch:
        batch.drop_column("ip_hmac")
        batch.drop_column("execution_token")
        batch.drop_column("execution_epoch")
