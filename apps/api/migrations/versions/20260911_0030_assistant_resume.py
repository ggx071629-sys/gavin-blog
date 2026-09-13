"""Add bounded resume content cache and independent binding/request identity."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260911_0030"
down_revision = "20260911_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_resume_source",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("binding_epoch", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("current_version_id", sa.String(32), nullable=True),
        sa.Column("current_request_id", sa.String(32), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("last_indexed_at", sa.DateTime(), nullable=True),
        sa.Column("last_refresh_at", sa.DateTime(), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.CheckConstraint("id = 1", name="ck_resume_source_singleton"),
    )
    op.create_table(
        "assistant_resume_versions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("binding_epoch", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("parser_version", sa.String(64), nullable=False),
        sa.Column("pdf_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("pages_json", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("length(pdf_bytes) <= 10485760", name="ck_resume_pdf_bytes"),
        sa.CheckConstraint("length(body) <= 200000", name="ck_resume_body_chars"),
    )
    op.create_table(
        "assistant_resume_requests",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("binding_epoch", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("lease_owner", sa.String(80), nullable=True),
        sa.Column("lease_token", sa.String(32), nullable=True),
        sa.Column("worker_fence", sa.Integer(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for table, name in (
        ("assistant_index_tasks", "ck_assistant_index_tasks_source_type"),
        ("assistant_chunks", "ck_assistant_chunks_source_type"),
    ):
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(name, type_="check")
            batch.create_check_constraint(
                name,
                "source_type IN ('article', 'project', 'book', 'profile', 'about', 'resume')",
            )


def downgrade() -> None:
    for table, name in (
        ("assistant_index_tasks", "ck_assistant_index_tasks_source_type"),
        ("assistant_chunks", "ck_assistant_chunks_source_type"),
    ):
        op.execute(sa.text(f"DELETE FROM {table} WHERE source_type = 'resume'"))
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(name, type_="check")
            batch.create_check_constraint(
                name,
                "source_type IN ('article', 'project', 'book', 'profile', 'about')",
            )
    for table in (
        "assistant_resume_requests",
        "assistant_resume_versions",
        "assistant_resume_source",
    ):
        op.drop_table(table)
