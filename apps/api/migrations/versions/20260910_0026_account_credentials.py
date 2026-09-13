"""Persist the singleton credential without loading deployment secrets."""

import sqlalchemy as sa
from alembic import op

revision = "20260910_0026"
down_revision = "20260910_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("id = 1"),
    )
    op.execute("DELETE FROM admin_sessions")


def downgrade() -> None:
    # Downgrade intentionally returns to configuration credentials, invalidating sessions.
    op.execute("DELETE FROM admin_sessions")
    op.drop_table("admin_credentials")
