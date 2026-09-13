"""Add publish plans, operations, source links, references, and rollback markers.

Revision ID: 20260804_0012
Revises: 20260804_0011
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260804_0012"
down_revision: str | Sequence[str] | None = "20260804_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _job_owner_check() -> str:
    return (
        "(event_id IS NOT NULL) + (revision_id IS NOT NULL) + "
        "(audit_plan_item_id IS NOT NULL) + (audit_version_id IS NOT NULL) + "
        "(connection_test_id IS NOT NULL) + (draft_plan_item_id IS NOT NULL) + "
        "(draft_version_id IS NOT NULL) + (publish_plan_item_id IS NOT NULL) = 1"
    )


def upgrade() -> None:
    op.create_table(
        "incubator_publish_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("operator", sa.String(length=80), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("stale_reason", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        "ix_incubator_publish_plans_status",
        "incubator_publish_plans",
        ["status"],
    )
    op.create_table(
        "incubator_publish_plan_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("incubator_publish_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "draft_id",
            sa.Integer(),
            sa.ForeignKey("incubator_drafts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("frozen_json", sa.Text(), nullable=False),
        sa.Column("preview_json", sa.Text(), nullable=False),
        sa.Column("batch_eligible", sa.Boolean(), nullable=False),
        sa.Column("block_code", sa.String(length=64), nullable=True),
        sa.Column("block_message", sa.String(length=500), nullable=True),
        sa.Column("warnings_json", sa.Text(), nullable=False),
        sa.Column("local_recheck_json", sa.Text(), nullable=False),
        sa.Column("publication_operation_id", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        "ix_incubator_publish_plan_items_plan_id",
        "incubator_publish_plan_items",
        ["plan_id"],
    )
    op.create_index(
        "ix_incubator_publish_plan_items_draft_id",
        "incubator_publish_plan_items",
        ["draft_id"],
    )
    op.create_index(
        "ix_incubator_publish_plan_items_status",
        "incubator_publish_plan_items",
        ["status"],
    )
    op.create_table(
        "incubator_publish_operations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_item_id",
            sa.Integer(),
            sa.ForeignKey("incubator_publish_plan_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "draft_id",
            sa.Integer(),
            sa.ForeignKey("incubator_drafts.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=True),
        sa.Column("revision_id", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        "ix_incubator_publish_operations_plan_item_id",
        "incubator_publish_operations",
        ["plan_item_id"],
    )
    op.create_index(
        "ix_incubator_publish_operations_draft_id",
        "incubator_publish_operations",
        ["draft_id"],
    )
    op.create_index(
        "ix_incubator_publish_operations_status",
        "incubator_publish_operations",
        ["status"],
    )
    op.create_index(
        "ix_incubator_publish_operations_article_id",
        "incubator_publish_operations",
        ["article_id"],
    )
    op.create_index(
        "ix_incubator_publish_operations_revision_id",
        "incubator_publish_operations",
        ["revision_id"],
    )
    op.create_table(
        "incubator_publish_source_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "revision_id",
            sa.Integer(),
            sa.ForeignKey("article_revisions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("incubator_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "source_revision_id",
            sa.Integer(),
            sa.ForeignKey("incubator_revisions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "audit_version_id",
            sa.Integer(),
            sa.ForeignKey("incubator_audit_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "draft_id",
            sa.Integer(),
            sa.ForeignKey("incubator_drafts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("draft_edit_version", sa.Integer(), nullable=False),
        sa.Column(
            "generation_version_id",
            sa.Integer(),
            sa.ForeignKey("incubator_draft_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("operator", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("revision_id"),
    )
    op.create_index(
        "ix_incubator_publish_source_links_source_id",
        "incubator_publish_source_links",
        ["source_id"],
    )
    op.create_index(
        "ix_incubator_publish_source_links_source_revision_id",
        "incubator_publish_source_links",
        ["source_revision_id"],
    )
    op.create_index(
        "ix_incubator_publish_source_links_audit_version_id",
        "incubator_publish_source_links",
        ["audit_version_id"],
    )
    op.create_index(
        "ix_incubator_publish_source_links_draft_id",
        "incubator_publish_source_links",
        ["draft_id"],
    )
    op.create_index(
        "ix_incubator_publish_source_links_generation_version_id",
        "incubator_publish_source_links",
        ["generation_version_id"],
    )
    op.create_table(
        "article_revision_public_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "revision_id",
            sa.Integer(),
            sa.ForeignKey("article_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("display_title", sa.String(length=180), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_article_revision_public_references_revision_id",
        "article_revision_public_references",
        ["revision_id"],
    )

    with op.batch_alter_table("incubator_drafts") as batch_op:
        batch_op.add_column(
            sa.Column("published_article_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("published_revision_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("publish_error_code", sa.String(length=64), nullable=True)
        )
        batch_op.add_column(
            sa.Column("publish_error_message", sa.String(length=500), nullable=True)
        )
        batch_op.add_column(
            sa.Column("last_publish_operation_id", sa.Integer(), nullable=True)
        )

    with op.batch_alter_table("article_revisions") as batch_op:
        batch_op.add_column(
            sa.Column("rollback_from_revision_id", sa.Integer(), nullable=True)
        )
        batch_op.create_index(
            "ix_article_revisions_rollback_from_revision_id",
            ["rollback_from_revision_id"],
        )
        batch_op.create_check_constraint(
            "ck_article_revisions_source",
            "source IN ('editor', 'incubator', 'rollback')",
        )

    with op.batch_alter_table("incubator_jobs") as batch_op:
        batch_op.drop_constraint("ck_incubator_jobs_single_owner", type_="check")
        batch_op.add_column(
            sa.Column(
                "publish_plan_item_id",
                sa.Integer(),
                sa.ForeignKey(
                    "incubator_publish_plan_items.id",
                    ondelete="CASCADE",
                    name="fk_incubator_jobs_publish_plan_item_id",
                ),
                nullable=True,
            )
        )
        batch_op.create_index(
            "ix_incubator_jobs_publish_plan_item_id",
            ["publish_plan_item_id"],
        )
        batch_op.create_check_constraint(
            "ck_incubator_jobs_single_owner",
            _job_owner_check(),
        )


def downgrade() -> None:
    with op.batch_alter_table("incubator_jobs") as batch_op:
        batch_op.drop_constraint("ck_incubator_jobs_single_owner", type_="check")
        batch_op.drop_index("ix_incubator_jobs_publish_plan_item_id")
        batch_op.drop_constraint(
            "fk_incubator_jobs_publish_plan_item_id",
            type_="foreignkey",
        )
        batch_op.drop_column("publish_plan_item_id")
        batch_op.create_check_constraint(
            "ck_incubator_jobs_single_owner",
            "(event_id IS NOT NULL) + (revision_id IS NOT NULL) + "
            "(audit_plan_item_id IS NOT NULL) + (audit_version_id IS NOT NULL) + "
            "(connection_test_id IS NOT NULL) + (draft_plan_item_id IS NOT NULL) + "
            "(draft_version_id IS NOT NULL) = 1",
        )

    with op.batch_alter_table("article_revisions") as batch_op:
        batch_op.drop_index("ix_article_revisions_rollback_from_revision_id")
        batch_op.drop_constraint(
            "ck_article_revisions_source",
            type_="check",
        )
        batch_op.drop_column("rollback_from_revision_id")

    with op.batch_alter_table("incubator_drafts") as batch_op:
        batch_op.drop_column("published_article_id")
        batch_op.drop_column("published_revision_id")
        batch_op.drop_column("publish_error_code")
        batch_op.drop_column("publish_error_message")
        batch_op.drop_column("last_publish_operation_id")

    op.drop_table("article_revision_public_references")
    op.drop_table("incubator_publish_source_links")
    op.drop_table("incubator_publish_operations")
    op.drop_table("incubator_publish_plan_items")
    op.drop_table("incubator_publish_plans")
