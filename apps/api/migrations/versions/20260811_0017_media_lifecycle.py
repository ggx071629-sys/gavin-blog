"""Add media deduplication and soft-delete lifecycle.

Revision ID: 20260811_0017
Revises: 20260811_0016
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0017"
down_revision: str | Sequence[str] | None = "20260811_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("media_assets") as batch:
        batch.add_column(sa.Column("content_sha256", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        batch.create_unique_constraint("uq_media_assets_content_sha256", ["content_sha256"])
        batch.create_index("ix_media_assets_deleted_at", ["deleted_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("media_assets") as batch:
        batch.drop_index("ix_media_assets_deleted_at")
        batch.drop_constraint("uq_media_assets_content_sha256", type_="unique")
        batch.drop_column("deleted_at")
        batch.drop_column("content_sha256")
