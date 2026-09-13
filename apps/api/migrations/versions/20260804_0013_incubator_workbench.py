"""Add composite indexes for the high-growth incubator job list.

Revision ID: 20260804_0013
Revises: 20260804_0012
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20260804_0013"
down_revision: str | Sequence[str] | None = "20260804_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_incubator_jobs_status_created_at_id",
        "incubator_jobs",
        ["status", "created_at", "id"],
    )
    op.create_index(
        "ix_incubator_jobs_job_type_created_at_id",
        "incubator_jobs",
        ["job_type", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_incubator_jobs_job_type_created_at_id", table_name="incubator_jobs")
    op.drop_index("ix_incubator_jobs_status_created_at_id", table_name="incubator_jobs")
