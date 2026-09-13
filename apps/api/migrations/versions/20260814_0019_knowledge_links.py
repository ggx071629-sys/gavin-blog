"""Add article working references and published content links.

Revision ID: 20260814_0019
Revises: 20260814_0018
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_0019"
down_revision: str | Sequence[str] | None = "20260814_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "article_working_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="external"),
        sa.Column("display_title", sa.String(length=180), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("target_type", sa.String(length=16), nullable=True),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('external', 'internal')",
            name="ck_article_working_references_kind",
        ),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_article_working_references_article_id",
        "article_working_references",
        ["article_id"],
    )
    op.create_table(
        "content_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("source_revision_id", sa.Integer(), nullable=True),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="wikilink"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('article', 'project', 'book')",
            name="ck_content_links_source_type",
        ),
        sa.CheckConstraint(
            "target_type IN ('article', 'project', 'book')",
            name="ck_content_links_target_type",
        ),
        sa.CheckConstraint(
            "kind IN ('wikilink', 'reference')",
            name="ck_content_links_kind",
        ),
        sa.UniqueConstraint(
            "source_type",
            "source_id",
            "target_type",
            "target_id",
            name="uq_content_links_source_target",
        ),
    )
    op.create_index("ix_content_links_source_type", "content_links", ["source_type"])
    op.create_index("ix_content_links_source_id", "content_links", ["source_id"])
    op.create_index("ix_content_links_target_type", "content_links", ["target_type"])
    op.create_index("ix_content_links_target_id", "content_links", ["target_id"])


def downgrade() -> None:
    op.drop_index("ix_content_links_target_id", table_name="content_links")
    op.drop_index("ix_content_links_target_type", table_name="content_links")
    op.drop_index("ix_content_links_source_id", table_name="content_links")
    op.drop_index("ix_content_links_source_type", table_name="content_links")
    op.drop_table("content_links")
    op.drop_index(
        "ix_article_working_references_article_id",
        table_name="article_working_references",
    )
    op.drop_table("article_working_references")
