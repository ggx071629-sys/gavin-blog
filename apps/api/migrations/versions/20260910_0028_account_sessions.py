"""Expose independent session identifiers and observed activity."""

import sqlalchemy as sa
from alembic import op

revision = "20260910_0028"
down_revision = "20260910_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM admin_sessions")
    with op.batch_alter_table("admin_sessions") as batch:
        batch.add_column(sa.Column("public_id", sa.String(64), nullable=False))
        batch.add_column(sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False))
        batch.create_unique_constraint("uq_admin_sessions_public_id", ["public_id"])


def downgrade() -> None:
    op.execute("DELETE FROM admin_sessions")
    with op.batch_alter_table("admin_sessions") as batch:
        batch.drop_constraint("uq_admin_sessions_public_id", type_="unique")
        batch.drop_column("last_seen_at")
        batch.drop_column("public_id")
