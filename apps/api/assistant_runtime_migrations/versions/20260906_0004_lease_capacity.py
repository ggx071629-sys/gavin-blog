"""Permit the existing per-IP and global concurrency budgets without losing leases."""

import sqlalchemy as sa
from alembic import op

revision = "20260906_rt0004"
down_revision = "20260829_rt0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("assistant_leases") as batch:
        batch.drop_constraint("uq_assistant_leases_scope_key", type_="unique")
        batch.create_unique_constraint(
            "uq_assistant_leases_owner", ["scope", "scope_key", "owner_turn_id"]
        )


def downgrade() -> None:
    if op.get_bind().execute(sa.text("SELECT COUNT(*) FROM assistant_leases")).scalar():
        raise RuntimeError("stop and drain active leases before downgrade")
    with op.batch_alter_table("assistant_leases") as batch:
        batch.drop_constraint("uq_assistant_leases_owner", type_="unique")
        batch.create_unique_constraint("uq_assistant_leases_scope_key", ["scope", "scope_key"])
