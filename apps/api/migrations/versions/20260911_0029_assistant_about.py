"""Add explicit About assistant eligibility and index source constraints."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260911_0029"
down_revision = "20260910_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "about_page_revisions",
        sa.Column("assistant_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(sa.text(
        "UPDATE about_page_revisions SET assistant_eligible = 1 "
        "WHERE revision_number > 1 OR source = 'rollback'"
    ))
    for table, name in (
        ("assistant_index_tasks", "ck_assistant_index_tasks_source_type"),
        ("assistant_chunks", "ck_assistant_chunks_source_type"),
    ):
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(name, type_="check")
            batch.create_check_constraint(
                name, "source_type IN ('article', 'project', 'book', 'profile', 'about')",
            )


def downgrade() -> None:
    # New derived rows have no meaning under the preceding four-source schema.
    for table, name in (
        ("assistant_index_tasks", "ck_assistant_index_tasks_source_type"),
        ("assistant_chunks", "ck_assistant_chunks_source_type"),
    ):
        op.execute(sa.text(f"DELETE FROM {table} WHERE source_type = 'about'"))
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(name, type_="check")
            batch.create_check_constraint(
                name, "source_type IN ('article', 'project', 'book', 'profile')",
            )
    op.drop_column("about_page_revisions", "assistant_eligible")
