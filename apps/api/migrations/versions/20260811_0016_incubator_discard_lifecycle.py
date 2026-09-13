"""Add recoverable incubator discard metadata.

Revision ID: 20260811_0016
Revises: 20260809_0015
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0016"
down_revision: str | Sequence[str] | None = "20260809_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("incubator_sources") as batch:
        batch.add_column(sa.Column("discard_reason", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("discarded_by", sa.String(length=80), nullable=True))
    with op.batch_alter_table("incubator_audit_versions") as batch:
        batch.add_column(sa.Column("discard_reason", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("discarded_by", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("discarded_from_status", sa.String(length=16), nullable=True))
    with op.batch_alter_table("incubator_drafts") as batch:
        batch.add_column(sa.Column("discarded_from_status", sa.String(length=16), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("incubator_drafts") as batch:
        batch.drop_column("discarded_from_status")
    with op.batch_alter_table("incubator_audit_versions") as batch:
        batch.drop_column("discarded_from_status")
        batch.drop_column("discarded_by")
        batch.drop_column("discard_reason")
    with op.batch_alter_table("incubator_sources") as batch:
        batch.drop_column("discarded_by")
        batch.drop_column("discard_reason")
