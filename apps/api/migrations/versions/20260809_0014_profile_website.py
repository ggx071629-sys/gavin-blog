"""Add a personal website URL to the singleton profile.

Revision ID: 20260809_0014
Revises: 20260804_0013
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0014"
down_revision: str | Sequence[str] | None = "20260804_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("website_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "website_url")
