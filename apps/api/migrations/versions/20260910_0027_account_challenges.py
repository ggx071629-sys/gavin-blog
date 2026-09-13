"""Durable bounded account challenges and rate reservations."""

import sqlalchemy as sa
from alembic import op

revision = "20260910_0027"
down_revision = "20260910_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_challenges",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("credential_version", sa.Integer(), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_account_challenges_purpose", "account_challenges", ["purpose"])
    op.create_table(
        "account_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("ip_hash", sa.String(64), nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_account_attempts_kind", "account_attempts", ["kind"])
    op.create_index("ix_account_attempts_created_at", "account_attempts", ["created_at"])


def downgrade() -> None:
    op.drop_table("account_attempts")
    op.drop_table("account_challenges")
