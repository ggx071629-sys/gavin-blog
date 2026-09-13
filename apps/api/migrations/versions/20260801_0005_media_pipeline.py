"""Add media assets.

Revision ID: 20260801_0005
Revises: 20260801_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260801_0005"
down_revision: str | Sequence[str] | None = "20260801_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("alt_text", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=True),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("storage_key", sa.String(length=64), nullable=True, unique=True),
        sa.Column("variants_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_media_assets_source", "media_assets", ["source"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_media_assets_source", table_name="media_assets")
    op.drop_table("media_assets")
