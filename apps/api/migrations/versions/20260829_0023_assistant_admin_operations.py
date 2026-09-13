"""Add durable assistant index operations and worker fencing.

Revision ID: 20260829_0023
Revises: 20260828_0022
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260829_0023"
down_revision: str | Sequence[str] | None = "20260828_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("assistant_index_tasks") as batch:
        batch.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("safe_error_code", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("intent_key", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("parent_task_id", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("operator_authorized", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("worker_fence", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("lease_token", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("provider_state", sa.String(length=16), nullable=True))
    op.create_index(
        "uq_assistant_index_tasks_intent_key",
        "assistant_index_tasks",
        ["intent_key"],
        unique=True,
    )
    op.create_table(
        "assistant_index_worker_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.String(length=80), nullable=True),
        sa.Column("fencing_token", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_assistant_index_worker_singleton"),
    )
    op.execute(
        "INSERT INTO assistant_index_worker_state "
        "(id, owner_id, fencing_token, heartbeat_at, lease_expires_at, updated_at) "
        "VALUES (1, NULL, 0, NULL, NULL, CURRENT_TIMESTAMP)"
    )
    op.create_table(
        "assistant_index_commands",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("idempotency_key_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("generation_id", sa.Integer(), nullable=True),
        sa.Column("previous_generation_id", sa.Integer(), nullable=True),
        sa.Column("worker_fence", sa.Integer(), nullable=True),
        sa.Column("source_cursor", sa.String(length=80), nullable=True),
        sa.Column("outbox_high_water", sa.Integer(), nullable=True),
        sa.Column("source_revision_set_digest", sa.String(length=64), nullable=True),
        sa.Column("manifest_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("finalize_token", sa.String(length=64), nullable=True),
        sa.Column("finalize_idempotency_hash", sa.String(length=64), nullable=True),
        sa.Column("safe_error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("terminal_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("idempotency_key_hash", name="uq_assistant_index_commands_idem"),
        sa.CheckConstraint("kind IN ('rebuild')", name="ck_assistant_index_commands_kind"),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'waiting', 'catch_up', 'ready_to_switch', "
            "'switch_pending', 'switched', 'failed', 'abandoned')",
            name="ck_assistant_index_commands_status",
        ),
    )
    op.create_index(
        "ix_assistant_index_commands_status",
        "assistant_index_commands",
        ["status", "created_at"],
    )
    op.create_table(
        "assistant_index_rebuild_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("command_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("source_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["command_id"], ["assistant_index_commands.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "command_id", "source_type", "source_id", name="uq_assistant_rebuild_source"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'waiting', 'dirty', 'failed')",
            name="ck_assistant_rebuild_progress_status",
        ),
    )
    op.create_index(
        "ix_assistant_rebuild_progress_command",
        "assistant_index_rebuild_progress",
        ["command_id", "status", "id"],
    )
    op.create_table(
        "assistant_index_repair_intents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("target_version", sa.String(length=64), nullable=False),
        sa.Column("generation_id", sa.Integer(), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "source_type", "source_id", "target_version", "generation_id",
            name="uq_assistant_index_repair_intent",
        ),
    )
    op.create_table(
        "assistant_index_provider_facts",
        sa.Column("kind", sa.String(length=32), primary_key=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("assistant_index_provider_facts")
    op.drop_table("assistant_index_repair_intents")
    op.drop_index(
        "ix_assistant_rebuild_progress_command", table_name="assistant_index_rebuild_progress"
    )
    op.drop_table("assistant_index_rebuild_progress")
    op.drop_index("ix_assistant_index_commands_status", table_name="assistant_index_commands")
    op.drop_table("assistant_index_commands")
    op.drop_table("assistant_index_worker_state")
    op.drop_index("uq_assistant_index_tasks_intent_key", table_name="assistant_index_tasks")
    with op.batch_alter_table("assistant_index_tasks") as batch:
        batch.drop_column("provider_state")
        batch.drop_column("lease_token")
        batch.drop_column("worker_fence")
        batch.drop_column("operator_authorized")
        batch.drop_column("parent_task_id")
        batch.drop_column("intent_key")
        batch.drop_column("safe_error_code")
        batch.drop_column("version")
