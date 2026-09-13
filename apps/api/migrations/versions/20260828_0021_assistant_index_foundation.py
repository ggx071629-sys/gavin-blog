"""Add rebuildable assistant hybrid-index schema.

Revision ID: 20260828_0021
Revises: 20260826_0020

Derived assistant chunks, FTS5, outbox tasks, generations, and the active
pointer. This migration does not connect to Qdrant, call an embedding
provider, start a worker, or rewrite existing content or search_index rows.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260828_0021"
down_revision: str | Sequence[str] | None = "20260826_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ASSISTANT_CHUNK_FTS_SQL = """
CREATE VIRTUAL TABLE assistant_chunk_fts USING fts5(
    chunk_id UNINDEXED,
    generation_id UNINDEXED,
    title,
    heading_path,
    body,
    tokenize = 'unicode61 remove_diacritics 2'
)
"""


def upgrade() -> None:
    op.create_table(
        "assistant_index_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("target_version", sa.String(length=64), nullable=False),
        sa.Column("pipeline_version", sa.String(length=64), nullable=False),
        sa.Column("operation", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lease_owner", sa.String(length=80), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("last_error_summary", sa.String(length=240), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "source_type IN ('article', 'project', 'book', 'profile')",
            name="ck_assistant_index_tasks_source_type",
        ),
        sa.CheckConstraint(
            "operation IN ('upsert', 'delete', 'purge')",
            name="ck_assistant_index_tasks_operation",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'leased', 'succeeded', 'failed')",
            name="ck_assistant_index_tasks_status",
        ),
    )
    op.create_index(
        "ix_assistant_index_tasks_source_type",
        "assistant_index_tasks",
        ["source_type"],
    )
    op.create_index(
        "ix_assistant_index_tasks_source_id",
        "assistant_index_tasks",
        ["source_id"],
    )
    op.create_index(
        "ix_assistant_index_tasks_status",
        "assistant_index_tasks",
        ["status"],
    )
    op.create_index(
        "ix_assistant_index_tasks_available_at",
        "assistant_index_tasks",
        ["available_at"],
    )
    op.create_index(
        "ix_assistant_index_tasks_poll",
        "assistant_index_tasks",
        ["status", "available_at", "id"],
    )

    op.create_table(
        "assistant_index_generations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("collection_name", sa.String(length=80), nullable=False),
        sa.Column("embedding_provider", sa.String(length=80), nullable=False),
        sa.Column("embedding_model", sa.String(length=160), nullable=False),
        sa.Column("embedding_model_version", sa.String(length=80), nullable=False),
        sa.Column("vector_dimension", sa.Integer(), nullable=False),
        sa.Column("distance_metric", sa.String(length=32), nullable=False),
        sa.Column("pipeline_version", sa.String(length=64), nullable=False),
        sa.Column("source_revision_set_digest", sa.String(length=64), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=True),
        sa.Column("vector_count", sa.Integer(), nullable=True),
        sa.Column("outbox_high_water", sa.Integer(), nullable=True),
        sa.Column("built_at", sa.DateTime(), nullable=True),
        sa.Column("manifest_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("collection_name", name="uq_assistant_index_generations_collection"),
        sa.CheckConstraint(
            "status IN ('staging', 'active', 'previous', 'failed', 'abandoned')",
            name="ck_assistant_index_generations_status",
        ),
    )
    op.create_index(
        "ix_assistant_index_generations_status",
        "assistant_index_generations",
        ["status"],
    )

    op.create_table(
        "assistant_index_pointers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("active_generation_id", sa.Integer(), nullable=True),
        sa.Column("previous_generation_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_assistant_index_pointers_singleton"),
        sa.ForeignKeyConstraint(
            ["active_generation_id"],
            ["assistant_index_generations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["previous_generation_id"],
            ["assistant_index_generations.id"],
            ondelete="SET NULL",
        ),
    )
    op.execute(
        sa.text(
            "INSERT INTO assistant_index_pointers "
            "(id, active_generation_id, previous_generation_id, updated_at) "
            "VALUES (1, NULL, NULL, CURRENT_TIMESTAMP)"
        )
    )

    op.create_table(
        "assistant_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chunk_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("source_version", sa.String(length=64), nullable=False),
        sa.Column("generation_id", sa.Integer(), nullable=False),
        sa.Column("pipeline_version", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("heading_path", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("page_content", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("public_path", sa.String(length=300), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["generation_id"],
            ["assistant_index_generations.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "generation_id",
            "chunk_id",
            name="uq_assistant_chunks_generation_chunk",
        ),
        sa.UniqueConstraint(
            "generation_id",
            "source_type",
            "source_id",
            "ordinal",
            name="uq_assistant_chunks_generation_source_ordinal",
        ),
        sa.CheckConstraint(
            "source_type IN ('article', 'project', 'book', 'profile')",
            name="ck_assistant_chunks_source_type",
        ),
    )
    op.create_index("ix_assistant_chunks_chunk_id", "assistant_chunks", ["chunk_id"])
    op.create_index("ix_assistant_chunks_source_type", "assistant_chunks", ["source_type"])
    op.create_index("ix_assistant_chunks_source_id", "assistant_chunks", ["source_id"])
    op.create_index("ix_assistant_chunks_generation_id", "assistant_chunks", ["generation_id"])
    op.create_index(
        "ix_assistant_chunks_source",
        "assistant_chunks",
        ["generation_id", "source_type", "source_id"],
    )

    op.execute(sa.text(ASSISTANT_CHUNK_FTS_SQL))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        bind.exec_driver_sql("DROP TABLE IF EXISTS assistant_chunk_fts")
    else:
        op.execute(sa.text("DROP TABLE IF EXISTS assistant_chunk_fts"))
    op.drop_index("ix_assistant_chunks_source", table_name="assistant_chunks")
    op.drop_index("ix_assistant_chunks_generation_id", table_name="assistant_chunks")
    op.drop_index("ix_assistant_chunks_source_id", table_name="assistant_chunks")
    op.drop_index("ix_assistant_chunks_source_type", table_name="assistant_chunks")
    op.drop_index("ix_assistant_chunks_chunk_id", table_name="assistant_chunks")
    op.drop_table("assistant_chunks")
    op.drop_table("assistant_index_pointers")
    op.drop_index("ix_assistant_index_generations_status", table_name="assistant_index_generations")
    op.drop_table("assistant_index_generations")
    op.drop_index("ix_assistant_index_tasks_poll", table_name="assistant_index_tasks")
    op.drop_index("ix_assistant_index_tasks_available_at", table_name="assistant_index_tasks")
    op.drop_index("ix_assistant_index_tasks_status", table_name="assistant_index_tasks")
    op.drop_index("ix_assistant_index_tasks_source_id", table_name="assistant_index_tasks")
    op.drop_index("ix_assistant_index_tasks_source_type", table_name="assistant_index_tasks")
    op.drop_table("assistant_index_tasks")
