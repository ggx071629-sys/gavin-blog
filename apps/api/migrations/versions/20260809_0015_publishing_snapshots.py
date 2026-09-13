"""Add immutable project and book-note publish snapshots.

Revision ID: 20260809_0015
Revises: 20260809_0014
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0015"
down_revision: str | Sequence[str] | None = "20260809_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _sha256(payload: dict) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _iso(value: object) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table: str, column: str) -> bool:
    return column in {
        item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)
    }


def _index_names(table: str) -> set[str]:
    return {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_indexes(table)
        if item["name"]
    }


def _create_tables() -> None:
    if not _has_table("project_revisions"):
        op.create_table(
            "project_revisions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "project_id",
                sa.Integer(),
                sa.ForeignKey("projects.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("revision_number", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=180), nullable=False),
            sa.Column("slug", sa.String(length=160), nullable=False),
            sa.Column("summary", sa.String(length=320), nullable=False, server_default=""),
            sa.Column("content", sa.Text(), nullable=False, server_default=""),
            sa.Column("repository_url", sa.String(length=500), nullable=True),
            sa.Column("website_url", sa.String(length=500), nullable=True),
            sa.Column("first_published_at", sa.DateTime(), nullable=False),
            sa.Column("published_at", sa.DateTime(), nullable=False),
            sa.Column("content_sha256", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("project_id", "revision_number"),
        )
    if "ix_project_revisions_project_id" not in _index_names("project_revisions"):
        op.create_index(
            "ix_project_revisions_project_id",
            "project_revisions",
            ["project_id"],
        )

    if not _has_table("project_revision_articles"):
        op.create_table(
            "project_revision_articles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "revision_id",
                sa.Integer(),
                sa.ForeignKey("project_revisions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("article_id", sa.Integer(), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.UniqueConstraint("revision_id", "article_id"),
        )
    for name, columns in (
        ("ix_project_revision_articles_revision_id", ["revision_id"]),
        ("ix_project_revision_articles_article_id", ["article_id"]),
    ):
        if name not in _index_names("project_revision_articles"):
            op.create_index(name, "project_revision_articles", columns)

    if not _has_table("book_note_revisions"):
        op.create_table(
            "book_note_revisions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "book_note_id",
                sa.Integer(),
                sa.ForeignKey("book_notes.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("revision_number", sa.Integer(), nullable=False),
            sa.Column("book_title", sa.String(length=180), nullable=False),
            sa.Column("author", sa.String(length=180), nullable=False),
            sa.Column("slug", sa.String(length=160), nullable=False),
            sa.Column("cover_url", sa.String(length=500), nullable=True),
            sa.Column("reading_status", sa.String(length=16), nullable=False),
            sa.Column("reading_date", sa.Date(), nullable=True),
            sa.Column("rating", sa.Integer(), nullable=True),
            sa.Column("summary", sa.String(length=320), nullable=False, server_default=""),
            sa.Column("content", sa.Text(), nullable=False, server_default=""),
            sa.Column("first_published_at", sa.DateTime(), nullable=False),
            sa.Column("published_at", sa.DateTime(), nullable=False),
            sa.Column("content_sha256", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("book_note_id", "revision_number"),
        )
    if "ix_book_note_revisions_book_note_id" not in _index_names("book_note_revisions"):
        op.create_index(
            "ix_book_note_revisions_book_note_id",
            "book_note_revisions",
            ["book_note_id"],
        )


def _add_current_revision_columns() -> None:
    if not _has_column("projects", "current_revision_id"):
        op.add_column(
            "projects",
            sa.Column("current_revision_id", sa.Integer(), nullable=True),
        )
    if "ix_projects_current_revision_id" not in _index_names("projects"):
        op.create_index(
            "ix_projects_current_revision_id",
            "projects",
            ["current_revision_id"],
        )
    if not _has_column("book_notes", "current_revision_id"):
        op.add_column(
            "book_notes",
            sa.Column("current_revision_id", sa.Integer(), nullable=True),
        )
    if "ix_book_notes_current_revision_id" not in _index_names("book_notes"):
        op.create_index(
            "ix_book_notes_current_revision_id",
            "book_notes",
            ["current_revision_id"],
        )


def _restore_backups() -> bool:
    bind = op.get_bind()
    backups = {
        "project_revisions": "_backup_project_revisions",
        "project_revision_articles": "_backup_project_revision_articles",
        "book_note_revisions": "_backup_book_note_revisions",
    }
    if not all(_has_table(name) for name in backups.values()):
        return False
    for target, backup in backups.items():
        bind.execute(sa.text(f"INSERT INTO {target} SELECT * FROM {backup}"))
    bind.execute(
        sa.text(
            "UPDATE projects SET current_revision_id = ("
            "SELECT id FROM project_revisions r WHERE r.project_id = projects.id "
            "ORDER BY r.revision_number DESC LIMIT 1)"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE book_notes SET current_revision_id = ("
            "SELECT id FROM book_note_revisions r WHERE r.book_note_id = book_notes.id "
            "ORDER BY r.revision_number DESC LIMIT 1)"
        )
    )
    for backup in backups.values():
        op.drop_table(backup)
    return True


def _backfill_published_content() -> None:
    bind = op.get_bind()
    projects = bind.execute(
        sa.text("SELECT * FROM projects WHERE status = 'published' AND published_at IS NOT NULL")
    ).mappings()
    for project in projects:
        article_ids = [
            row[0]
            for row in bind.execute(
                sa.text(
                    "SELECT article_id FROM project_articles "
                    "WHERE project_id = :project_id ORDER BY article_id"
                ),
                {"project_id": project["id"]},
            ).all()
        ]
        digest = _sha256(
            {
                "title": project["title"],
                "slug": project["slug"],
                "summary": project["summary"],
                "content": project["content"],
                "repository_url": project["repository_url"],
                "website_url": project["website_url"],
                "article_ids": article_ids,
            }
        )
        result = bind.execute(
            sa.text(
                "INSERT INTO project_revisions("
                "project_id, revision_number, title, slug, summary, content, "
                "repository_url, website_url, first_published_at, published_at, "
                "content_sha256, created_at) VALUES ("
                ":id, 1, :title, :slug, :summary, :content, :repository_url, "
                ":website_url, :published_at, :published_at, :digest, :created_at)"
            ),
            {
                **dict(project),
                "digest": digest,
                "created_at": project["published_at"] or project["updated_at"],
            },
        )
        revision_id = result.lastrowid
        for position, article_id in enumerate(article_ids):
            bind.execute(
                sa.text(
                    "INSERT INTO project_revision_articles("
                    "revision_id, article_id, position) VALUES "
                    "(:revision_id, :article_id, :position)"
                ),
                {
                    "revision_id": revision_id,
                    "article_id": article_id,
                    "position": position,
                },
            )
        bind.execute(
            sa.text("UPDATE projects SET current_revision_id = :revision_id WHERE id = :id"),
            {"revision_id": revision_id, "id": project["id"]},
        )

    notes = bind.execute(
        sa.text("SELECT * FROM book_notes WHERE status = 'published' AND published_at IS NOT NULL")
    ).mappings()
    for note in notes:
        digest = _sha256(
            {
                "book_title": note["book_title"],
                "author": note["author"],
                "slug": note["slug"],
                "cover_url": note["cover_url"],
                "reading_status": note["reading_status"],
                "reading_date": _iso(note["reading_date"]),
                "rating": note["rating"],
                "summary": note["summary"],
                "content": note["content"],
            }
        )
        result = bind.execute(
            sa.text(
                "INSERT INTO book_note_revisions("
                "book_note_id, revision_number, book_title, author, slug, cover_url, "
                "reading_status, reading_date, rating, summary, content, "
                "first_published_at, published_at, content_sha256, created_at) VALUES ("
                ":id, 1, :book_title, :author, :slug, :cover_url, :reading_status, "
                ":reading_date, :rating, :summary, :content, :published_at, :published_at, "
                ":digest, :created_at)"
            ),
            {
                **dict(note),
                "digest": digest,
                "created_at": note["published_at"] or note["updated_at"],
            },
        )
        bind.execute(
            sa.text("UPDATE book_notes SET current_revision_id = :revision_id WHERE id = :id"),
            {"revision_id": result.lastrowid, "id": note["id"]},
        )


def upgrade() -> None:
    _create_tables()
    _add_current_revision_columns()
    if not _restore_backups():
        _backfill_published_content()


def downgrade() -> None:
    bind = op.get_bind()
    for source, backup in (
        ("project_revisions", "_backup_project_revisions"),
        ("project_revision_articles", "_backup_project_revision_articles"),
        ("book_note_revisions", "_backup_book_note_revisions"),
    ):
        bind.execute(sa.text(f"CREATE TABLE {backup} AS SELECT * FROM {source}"))

    op.drop_index("ix_projects_current_revision_id", table_name="projects")
    op.drop_column("projects", "current_revision_id")
    op.drop_index("ix_book_notes_current_revision_id", table_name="book_notes")
    op.drop_column("book_notes", "current_revision_id")
    op.drop_table("project_revision_articles")
    op.drop_table("project_revisions")
    op.drop_table("book_note_revisions")
