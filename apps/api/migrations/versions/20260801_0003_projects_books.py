"""Add projects and book notes.

Revision ID: 20260801_0003
Revises: 20260801_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260801_0003"
down_revision: str | Sequence[str] | None = "20260801_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.String(length=320), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("repository_url", sa.String(length=500), nullable=True),
        sa.Column("website_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_projects_slug", "projects", ["slug"], unique=True)
    op.create_index("ix_projects_status", "projects", ["status"], unique=False)
    op.create_table(
        "project_articles",
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "article_id",
            sa.Integer(),
            sa.ForeignKey("articles.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )
    op.create_table(
        "book_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("book_title", sa.String(length=180), nullable=False),
        sa.Column("author", sa.String(length=180), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("cover_url", sa.String(length=500), nullable=True),
        sa.Column("reading_status", sa.String(length=16), nullable=False, server_default="planned"),
        sa.Column("reading_date", sa.Date(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("summary", sa.String(length=320), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 5)",
            name="ck_book_rating",
        ),
    )
    op.create_index("ix_book_notes_slug", "book_notes", ["slug"], unique=True)
    op.create_index("ix_book_notes_status", "book_notes", ["status"], unique=False)
    op.create_index(
        "ix_book_notes_reading_status",
        "book_notes",
        ["reading_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_book_notes_reading_status", table_name="book_notes")
    op.drop_index("ix_book_notes_status", table_name="book_notes")
    op.drop_index("ix_book_notes_slug", table_name="book_notes")
    op.drop_table("book_notes")
    op.drop_table("project_articles")
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_index("ix_projects_slug", table_name="projects")
    op.drop_table("projects")
