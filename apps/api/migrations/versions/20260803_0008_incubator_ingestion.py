"""Add knowledge incubator ingestion entities.

Revision ID: 20260803_0008
Revises: 20260801_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260803_0008"
down_revision: str | Sequence[str] | None = "20260801_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "incubator_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("url_count", sa.Integer(), nullable=False),
        sa.Column("total_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "incubator_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "batch_id",
            sa.Integer(),
            sa.ForeignKey("incubator_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=8), nullable=False),
        sa.Column("input_name", sa.String(length=2000), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("staged_blob", sa.LargeBinary(), nullable=True),
        sa.Column("staged_sha256", sa.String(length=64), nullable=True),
        sa.Column("staged_mime", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_incubator_events_batch_id", "incubator_events", ["batch_id"])
    op.create_index("ix_incubator_events_source_id", "incubator_events", ["source_id"])
    op.create_index("ix_incubator_events_source_type", "incubator_events", ["source_type"])
    op.create_index("ix_incubator_events_status", "incubator_events", ["status"])
    op.create_table(
        "incubator_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Integer(),
            sa.ForeignKey("incubator_events.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("source_type", sa.String(length=8), nullable=False),
        sa.Column("source_name", sa.String(length=2000), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("body_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("token_estimate", sa.Integer(), nullable=False),
        sa.Column("cleaner_version", sa.String(length=24), nullable=False),
        sa.Column("current_revision_id", sa.Integer(), nullable=True),
        sa.Column("raw_payload_id", sa.Integer(), nullable=True),
        sa.Column("discarded_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_incubator_sources_status", "incubator_sources", ["status"])
    op.create_index("ix_incubator_sources_source_type", "incubator_sources", ["source_type"])
    op.create_index(
        "ix_incubator_sources_body_fingerprint",
        "incubator_sources",
        ["body_fingerprint"],
        unique=True,
    )
    op.create_table(
        "incubator_raw_payloads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("incubator_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("compression_format", sa.String(length=16), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("original_encoding", sa.String(length=40), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
    )
    op.create_index(
        "ix_incubator_raw_payloads_source_id",
        "incubator_raw_payloads",
        ["source_id"],
        unique=True,
    )
    op.create_table(
        "incubator_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("incubator_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("body_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("token_estimate", sa.Integer(), nullable=False),
        sa.Column("cleaner_version", sa.String(length=24), nullable=False),
        sa.Column("base_revision", sa.Integer(), nullable=True),
        sa.Column("is_manual", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("source_id", "revision_number"),
    )
    op.create_index(
        "ix_incubator_revisions_source_id",
        "incubator_revisions",
        ["source_id"],
    )
    op.create_table(
        "incubator_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Integer(),
            sa.ForeignKey("incubator_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("job_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("cancellation_requested", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_incubator_jobs_event_id", "incubator_jobs", ["event_id"])
    op.create_index("ix_incubator_jobs_status", "incubator_jobs", ["status"])
    op.create_index(
        "ix_incubator_jobs_idempotency_key",
        "incubator_jobs",
        ["idempotency_key"],
        unique=True,
    )
    op.create_table(
        "incubator_worker_heartbeats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("worker_id", sa.String(length=64), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_incubator_worker_heartbeats_worker_id",
        "incubator_worker_heartbeats",
        ["worker_id"],
    )


def downgrade() -> None:
    op.drop_table("incubator_worker_heartbeats")
    op.drop_table("incubator_jobs")
    op.drop_table("incubator_revisions")
    op.drop_table("incubator_raw_payloads")
    op.drop_table("incubator_sources")
    op.drop_table("incubator_events")
    op.drop_table("incubator_batches")
