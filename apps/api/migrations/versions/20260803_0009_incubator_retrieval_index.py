"""Add publish revisions, retrieval index entities, and article index jobs.

Revision ID: 20260803_0009
Revises: 20260803_0008
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260803_0009"
down_revision: str | Sequence[str] | None = "20260803_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Frozen pipeline constants; see apps/api/app/incubator/retrieval/config.py.
PIPELINE_VERSION = "retrieval-v1"
EMBEDDING_REVISION = "ccc66d3bcd826f577e26b9a4072cc5fe3a7ad6a3"
MANIFEST_UNPREPARED = "unprepared"


def _canonical_sha256(row: dict, tags: list[tuple]) -> str:
    payload = {
        "title": row["title"],
        "slug": row["slug"],
        "summary": row["summary"],
        "content": row["content"],
        "category_id": row["category_id"],
        "tags": [[tag[0], tag[1], tag[2]] for tag in tags],
    }
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _index_job_key(article_id: int, revision_number: int) -> str:
    return hashlib.sha256(
        f"{article_id}:{revision_number}:{PIPELINE_VERSION}:{EMBEDDING_REVISION}:"
        f"{MANIFEST_UNPREPARED}".encode()
    ).hexdigest()


def upgrade() -> None:
    op.create_table(
        "article_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "article_id",
            sa.Integer(),
            sa.ForeignKey("articles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.String(length=320), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("first_published_at", sa.DateTime(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("category_name", sa.String(length=80), nullable=False),
        sa.Column("category_slug", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("article_id", "revision_number"),
    )
    op.create_index(
        "ix_article_revisions_article_id",
        "article_revisions",
        ["article_id"],
    )
    op.create_table(
        "article_revision_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "revision_id",
            sa.Integer(),
            sa.ForeignKey("article_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_article_revision_tags_revision_id",
        "article_revision_tags",
        ["revision_id"],
    )

    op.add_column(
        "articles",
        sa.Column("current_revision_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_articles_current_revision_id",
        "articles",
        ["current_revision_id"],
    )

    with op.batch_alter_table("incubator_jobs") as batch_op:
        batch_op.alter_column(
            "event_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.add_column(sa.Column("revision_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_incubator_jobs_revision_id_article_revisions",
            "article_revisions",
            ["revision_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            "ix_incubator_jobs_revision_id",
            ["revision_id"],
        )
        batch_op.create_check_constraint(
            "ck_incubator_jobs_single_owner",
            "(event_id IS NULL) <> (revision_id IS NULL)",
        )

    op.create_table(
        "article_index_statuses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "revision_id",
            sa.Integer(),
            sa.ForeignKey("article_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "article_id",
            sa.Integer(),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("segment_count", sa.Integer(), nullable=False),
        sa.Column("pipeline_version", sa.String(length=24), nullable=False),
        sa.Column("embedding_model_revision", sa.String(length=64), nullable=False),
        sa.Column("manifest_checksum", sa.String(length=64), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("revision_id"),
    )
    op.create_index(
        "ix_article_index_statuses_revision_id",
        "article_index_statuses",
        ["revision_id"],
        unique=True,
    )
    op.create_index(
        "ix_article_index_statuses_article_id",
        "article_index_statuses",
        ["article_id"],
    )
    op.create_index(
        "ix_article_index_statuses_status",
        "article_index_statuses",
        ["status"],
    )
    op.create_table(
        "article_index_segments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "revision_id",
            sa.Integer(),
            sa.ForeignKey("article_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "article_id",
            sa.Integer(),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("segment_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("heading_path", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("pipeline_version", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("revision_id", "segment_number"),
    )
    op.create_index(
        "ix_article_index_segments_revision_id",
        "article_index_segments",
        ["revision_id"],
    )
    op.create_index(
        "ix_article_index_segments_article_id",
        "article_index_segments",
        ["article_id"],
    )
    op.create_table(
        "article_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "revision_id",
            sa.Integer(),
            sa.ForeignKey("article_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "segment_id",
            sa.Integer(),
            sa.ForeignKey("article_index_segments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("embedding_model_revision", sa.String(length=64), nullable=False),
        sa.Column("manifest_checksum", sa.String(length=64), nullable=False),
        sa.Column("pipeline_version", sa.String(length=24), nullable=False),
        sa.Column("vector", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "segment_id",
            "embedding_model_revision",
            "pipeline_version",
        ),
    )
    op.create_index(
        "ix_article_embeddings_revision_id",
        "article_embeddings",
        ["revision_id"],
    )
    op.create_index(
        "ix_article_embeddings_segment_id",
        "article_embeddings",
        ["segment_id"],
    )
    op.create_table(
        "article_index_pointers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "article_id",
            sa.Integer(),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "revision_id",
            sa.Integer(),
            sa.ForeignKey("article_revisions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("manifest_checksum", sa.String(length=64), nullable=False),
        sa.Column("embedding_model_revision", sa.String(length=64), nullable=False),
        sa.Column("pipeline_version", sa.String(length=24), nullable=False),
        sa.Column("activated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_article_index_pointers_article_id",
        "article_index_pointers",
        ["article_id"],
        unique=True,
    )
    op.create_index(
        "ix_article_index_pointers_revision_id",
        "article_index_pointers",
        ["revision_id"],
    )

    op.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS incubator_fts USING fts5(
            segment_id UNINDEXED,
            article_id UNINDEXED,
            revision_id UNINDEXED,
            title,
            heading_path,
            body,
            pipeline_version UNINDEXED,
            tokenize = 'unicode61 remove_diacritics 2'
        )
        """
    )

    _backfill_baseline_revisions()


def _backfill_baseline_revisions() -> None:
    """Create immutable revision 1 for every existing published article."""
    bind = op.get_bind()
    articles = bind.execute(
        sa.text(
            "SELECT id, title, slug, summary, content, published_at, category_id "
            "FROM articles WHERE status = 'published' AND published_at IS NOT NULL "
            "ORDER BY id"
        )
    ).mappings().all()
    for row in articles:
        category = None
        if row["category_id"] is not None:
            category = bind.execute(
                sa.text("SELECT name, slug FROM categories WHERE id = :cid"),
                {"cid": row["category_id"]},
            ).first()
        tags = bind.execute(
            sa.text(
                "SELECT tags.id, tags.name, tags.slug FROM article_tags "
                "JOIN tags ON tags.id = article_tags.tag_id "
                "WHERE article_tags.article_id = :aid ORDER BY tags.name, tags.id"
            ),
            {"aid": row["id"]},
        ).all()
        content_sha256 = _canonical_sha256(dict(row), tags)
        bind.execute(
            sa.text(
                """
                INSERT INTO article_revisions(
                    article_id, revision_number, title, slug, summary, content,
                    first_published_at, published_at, category_id, category_name,
                    category_slug, source, content_sha256, created_at
                ) VALUES (
                    :article_id, 1, :title, :slug, :summary, :content,
                    :published_at, :published_at, :category_id, :category_name,
                    :category_slug, 'editor', :content_sha256, :published_at
                )
                """
            ),
            {
                "article_id": row["id"],
                "title": row["title"],
                "slug": row["slug"],
                "summary": row["summary"],
                "content": row["content"],
                "published_at": row["published_at"],
                "category_id": row["category_id"],
                "category_name": category[0] if category else "",
                "category_slug": category[1] if category else "",
                "content_sha256": content_sha256,
            },
        )
        revision_id = bind.execute(
            sa.text(
                "SELECT id FROM article_revisions "
                "WHERE article_id = :aid AND revision_number = 1"
            ),
            {"aid": row["id"]},
        ).scalar_one()
        bind.execute(
            sa.text(
                "UPDATE articles SET current_revision_id = :rid WHERE id = :aid"
            ),
            {"rid": revision_id, "aid": row["id"]},
        )
        for position, tag in enumerate(tags):
            bind.execute(
                sa.text(
                    """
                    INSERT INTO article_revision_tags(
                        revision_id, tag_id, name, slug, position
                    ) VALUES (:revision_id, :tag_id, :name, :slug, :position)
                    """
                ),
                {
                    "revision_id": revision_id,
                    "tag_id": tag[0],
                    "name": tag[1],
                    "slug": tag[2],
                    "position": position,
                },
            )
        now = row["published_at"]
        bind.execute(
            sa.text(
                """
                INSERT INTO article_index_statuses(
                    revision_id, article_id, status, progress, segment_count,
                    pipeline_version, embedding_model_revision, manifest_checksum,
                    created_at, updated_at
                ) VALUES (
                    :revision_id, :article_id, 'pending', 0, 0,
                    :pipeline_version, :embedding_revision, :manifest,
                    :now, :now
                )
                """
            ),
            {
                "revision_id": revision_id,
                "article_id": row["id"],
                "pipeline_version": PIPELINE_VERSION,
                "embedding_revision": EMBEDDING_REVISION,
                "manifest": MANIFEST_UNPREPARED,
                "now": now,
            },
        )
        bind.execute(
            sa.text(
                """
                INSERT INTO incubator_jobs(
                    event_id, revision_id, job_type, status, progress, attempts,
                    idempotency_key, cancellation_requested, created_at, updated_at
                ) VALUES (
                    NULL, :revision_id, 'article_index', 'queued', 0, 0,
                    :idempotency_key, 0, :now, :now
                )
                """
            ),
            {
                "revision_id": revision_id,
                "idempotency_key": _index_job_key(row["id"], 1),
                "now": now,
            },
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS incubator_fts")
    op.drop_table("article_index_pointers")
    op.drop_table("article_embeddings")
    op.drop_table("article_index_segments")
    op.drop_table("article_index_statuses")

    with op.batch_alter_table("incubator_jobs") as batch_op:
        batch_op.drop_constraint("ck_incubator_jobs_single_owner", type_="check")
        batch_op.drop_constraint(
            "fk_incubator_jobs_revision_id_article_revisions",
            type_="foreignkey",
        )
        batch_op.drop_index("ix_incubator_jobs_revision_id")
        batch_op.drop_column("revision_id")
        batch_op.alter_column(
            "event_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

    op.drop_index("ix_articles_current_revision_id", table_name="articles")
    op.drop_column("articles", "current_revision_id")
    op.drop_table("article_revision_tags")
    op.drop_table("article_revisions")
