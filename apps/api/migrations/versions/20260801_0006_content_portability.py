"""Add soft-delete timestamps to publishable content.

Revision ID: 20260801_0006
Revises: 20260801_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260801_0006"
down_revision: str | Sequence[str] | None = "20260801_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("articles", "projects", "book_notes"):
        op.add_column(table, sa.Column("deleted_at", sa.DateTime(), nullable=True))
        op.create_index(f"ix_{table}_deleted_at", table, ["deleted_at"], unique=False)


def downgrade() -> None:
    for table in ("book_notes", "projects", "articles"):
        op.drop_index(f"ix_{table}_deleted_at", table_name=table)
        op.drop_column(table, "deleted_at")
