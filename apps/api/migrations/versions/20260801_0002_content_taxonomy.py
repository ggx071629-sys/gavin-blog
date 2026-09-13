"""Add categories and tags to articles.

Revision ID: 20260801_0002
Revises: 20260731_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260801_0002"
down_revision: str | Sequence[str] | None = "20260731_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False, unique=True),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=True)
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False, unique=True),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_tags_slug", "tags", ["slug"], unique=True)
    with op.batch_alter_table("articles") as batch_op:
        batch_op.add_column(sa.Column("category_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_articles_category_id", ["category_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_articles_category_id_categories",
            "categories",
            ["category_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_table(
        "article_tags",
        sa.Column(
            "article_id",
            sa.Integer(),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.Integer(),
            sa.ForeignKey("tags.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("article_tags")
    with op.batch_alter_table("articles") as batch_op:
        batch_op.drop_constraint("fk_articles_category_id_categories", type_="foreignkey")
        batch_op.drop_index("ix_articles_category_id")
        batch_op.drop_column("category_id")
    op.drop_index("ix_tags_slug", table_name="tags")
    op.drop_table("tags")
    op.drop_index("ix_categories_slug", table_name="categories")
    op.drop_table("categories")
