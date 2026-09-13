"""Shared assistant budget authority; runtime history is imported by the API owner."""

import sqlalchemy as sa
from alembic import op

revision = "20260910_0025"
down_revision = "20260907_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_budget_policy",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cap_micro_cny", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("blocked_beijing_date", sa.String(10), nullable=True),
        sa.Column("runtime_accounted_date", sa.String(10), nullable=True),
    )
    op.create_table(
        "assistant_budget_reservations",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("beijing_date", sa.String(10), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("reserved_micro_cny", sa.Integer(), nullable=False),
        sa.Column("settled_micro_cny", sa.Integer(), nullable=False),
        sa.Column("terminal", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_assistant_budget_reservations_beijing_date",
        "assistant_budget_reservations",
        ["beijing_date"],
    )
    op.execute(
        sa.text("""
        INSERT INTO assistant_budget_reservations
        SELECT 'index:' || id, beijing_date, 'index_embedding', 'index',
          CASE WHEN status IN ('prepared','sending') THEN max_cost_micro_cny ELSE 0 END,
          COALESCE(settled_micro_cny,0),
          CASE WHEN status IN ('prepared','sending') THEN 0 ELSE 1 END
        FROM assistant_index_embedding_attempts WHERE status != 'deferred'
    """)
    )


def downgrade() -> None:
    if (
        op.get_bind()
        .execute(sa.text("SELECT COUNT(*) FROM assistant_budget_reservations"))
        .scalar()
    ):
        raise RuntimeError("preserve budget authority; cannot downgrade nonempty accounting")
    op.drop_table("assistant_budget_reservations")
    op.drop_table("assistant_budget_policy")
