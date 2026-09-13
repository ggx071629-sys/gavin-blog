"""Add Zvec generation request owners for rebuild and switch jobs.

Revision ID: 20260814_0018
Revises: 20260811_0017
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_0018"
down_revision: str | Sequence[str] | None = "20260811_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _previous_owner_check() -> str:
    return (
        "(event_id IS NOT NULL) + (revision_id IS NOT NULL) + "
        "(audit_plan_item_id IS NOT NULL) + (audit_version_id IS NOT NULL) + "
        "(connection_test_id IS NOT NULL) + (draft_plan_item_id IS NOT NULL) + "
        "(draft_version_id IS NOT NULL) + (publish_plan_item_id IS NOT NULL) = 1"
    )


def _owner_check() -> str:
    return (
        "(event_id IS NOT NULL) + (revision_id IS NOT NULL) + "
        "(audit_plan_item_id IS NOT NULL) + (audit_version_id IS NOT NULL) + "
        "(connection_test_id IS NOT NULL) + (draft_plan_item_id IS NOT NULL) + "
        "(draft_version_id IS NOT NULL) + (publish_plan_item_id IS NOT NULL) + "
        "(generation_request_id IS NOT NULL) = 1"
    )


def upgrade() -> None:
    op.create_table(
        "zvec_generation_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("generation_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("pipeline_version", sa.String(length=32), nullable=False),
        sa.Column("embedding_revision", sa.String(length=64), nullable=False),
        sa.Column("manifest_checksum", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_zvec_generation_requests_action",
        "zvec_generation_requests",
        ["action"],
    )
    with op.batch_alter_table("incubator_jobs") as batch_op:
        batch_op.drop_constraint("ck_incubator_jobs_single_owner", type_="check")
        batch_op.add_column(
            sa.Column(
                "generation_request_id",
                sa.Integer(),
                sa.ForeignKey(
                    "zvec_generation_requests.id",
                    ondelete="CASCADE",
                    name="fk_incubator_jobs_generation_request_id",
                ),
                nullable=True,
            )
        )
        batch_op.create_index(
            "ix_incubator_jobs_generation_request_id",
            ["generation_request_id"],
        )
        batch_op.create_check_constraint(
            "ck_incubator_jobs_single_owner",
            _owner_check(),
        )


def downgrade() -> None:
    with op.batch_alter_table("incubator_jobs") as batch_op:
        batch_op.drop_constraint("ck_incubator_jobs_single_owner", type_="check")
        batch_op.drop_index("ix_incubator_jobs_generation_request_id")
        batch_op.drop_constraint(
            "fk_incubator_jobs_generation_request_id",
            type_="foreignkey",
        )
        batch_op.drop_column("generation_request_id")
        batch_op.create_check_constraint(
            "ck_incubator_jobs_single_owner",
            _previous_owner_check(),
        )
    op.drop_index("ix_zvec_generation_requests_action", table_name="zvec_generation_requests")
    op.drop_table("zvec_generation_requests")
