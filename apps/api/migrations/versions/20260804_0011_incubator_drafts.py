"""Add incubator draft entities: plans, drafts, versions, anchors, attempts.

Revision ID: 20260804_0011
Revises: 20260804_0010
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260804_0011"
down_revision: str | Sequence[str] | None = "20260804_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _job_owner_check() -> str:
    return (
        "(event_id IS NOT NULL) + (revision_id IS NOT NULL) + "
        "(audit_plan_item_id IS NOT NULL) + (audit_version_id IS NOT NULL) + "
        "(connection_test_id IS NOT NULL) + (draft_plan_item_id IS NOT NULL) + "
        "(draft_version_id IS NOT NULL) = 1"
    )


def upgrade() -> None:
    op.create_table(
        "incubator_draft_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "audit_version_id",
            sa.Integer(),
            sa.ForeignKey("incubator_audit_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("prompt_version", sa.String(length=24), nullable=False),
        sa.Column("provider_service", sa.String(length=200), nullable=False),
        sa.Column("provider_model", sa.String(length=200), nullable=False),
        sa.Column("context_estimate_json", sa.Text(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("stale_reason", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        "ix_incubator_draft_plans_audit_version_id",
        "incubator_draft_plans",
        ["audit_version_id"],
    )
    op.create_index(
        "ix_incubator_draft_plans_status",
        "incubator_draft_plans",
        ["status"],
    )
    op.create_table(
        "incubator_draft_plan_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("incubator_draft_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "audit_version_id",
            sa.Integer(),
            sa.ForeignKey("incubator_audit_versions.id", ondelete="RESTRICT"),
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
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("from_conflict", sa.Boolean(), nullable=False),
        sa.Column("target_article_id", sa.Integer(), nullable=True),
        sa.Column("target_revision_id", sa.Integer(), nullable=True),
        sa.Column("target_snapshot_json", sa.Text(), nullable=False),
        sa.Column("taxonomy_candidates_json", sa.Text(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("base_draft_version_id", sa.Integer(), nullable=True),
        sa.Column("base_edit_version", sa.Integer(), nullable=False),
        sa.Column("context_estimate_json", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        "ix_incubator_draft_plan_items_plan_id",
        "incubator_draft_plan_items",
        ["plan_id"],
    )
    op.create_index(
        "ix_incubator_draft_plan_items_audit_version_id",
        "incubator_draft_plan_items",
        ["audit_version_id"],
    )
    op.create_index(
        "ix_incubator_draft_plan_items_source_id",
        "incubator_draft_plan_items",
        ["source_id"],
    )
    op.create_index(
        "ix_incubator_draft_plan_items_source_revision_id",
        "incubator_draft_plan_items",
        ["source_revision_id"],
    )
    op.create_table(
        "incubator_draft_anchors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_item_id",
            sa.Integer(),
            sa.ForeignKey("incubator_draft_plan_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("anchor_id", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("heading_level", sa.Integer(), nullable=False),
        sa.Column("heading_path", sa.String(length=500), nullable=False),
        sa.Column("heading_text", sa.String(length=180), nullable=False),
        sa.Column("occurrence", sa.Integer(), nullable=False),
        sa.Column("context_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("plan_item_id", "anchor_id"),
    )
    op.create_index(
        "ix_incubator_draft_anchors_plan_item_id",
        "incubator_draft_anchors",
        ["plan_item_id"],
    )
    op.create_table(
        "incubator_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "audit_version_id",
            sa.Integer(),
            sa.ForeignKey("incubator_audit_versions.id", ondelete="RESTRICT"),
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
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("target_article_id", sa.Integer(), nullable=True),
        sa.Column("target_revision_id", sa.Integer(), nullable=True),
        sa.Column("from_conflict", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("edit_version", sa.Integer(), nullable=False),
        sa.Column("active_version_id", sa.Integer(), nullable=True),
        sa.Column("working_copy_json", sa.Text(), nullable=False),
        sa.Column("last_saved_at", sa.DateTime(), nullable=True),
        sa.Column("stale_reason", sa.String(length=64), nullable=True),
        sa.Column("discard_reason", sa.String(length=500), nullable=True),
        sa.Column("discarded_by", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("audit_version_id"),
    )
    op.create_index(
        "ix_incubator_drafts_audit_version_id",
        "incubator_drafts",
        ["audit_version_id"],
    )
    op.create_index(
        "ix_incubator_drafts_source_id",
        "incubator_drafts",
        ["source_id"],
    )
    op.create_index(
        "ix_incubator_drafts_source_revision_id",
        "incubator_drafts",
        ["source_revision_id"],
    )
    op.create_index(
        "ix_incubator_drafts_status",
        "incubator_drafts",
        ["status"],
    )
    op.create_table(
        "incubator_draft_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "draft_id",
            sa.Integer(),
            sa.ForeignKey("incubator_drafts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("merged_markdown", sa.Text(), nullable=False),
        sa.Column("patch_json", sa.Text(), nullable=False),
        sa.Column("diff_preview_json", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.String(length=24), nullable=False),
        sa.Column("provider_service", sa.String(length=200), nullable=False),
        sa.Column("provider_model", sa.String(length=200), nullable=False),
        sa.Column("request_sha256", sa.String(length=64), nullable=False),
        sa.Column("response_sha256", sa.String(length=64), nullable=False),
        sa.Column("base_draft_version_id", sa.Integer(), nullable=True),
        sa.Column("base_edit_version", sa.Integer(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("attempt_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("draft_id", "version_number"),
    )
    op.create_index(
        "ix_incubator_draft_versions_draft_id",
        "incubator_draft_versions",
        ["draft_id"],
    )
    op.create_index(
        "ix_incubator_draft_versions_status",
        "incubator_draft_versions",
        ["status"],
    )
    op.create_table(
        "incubator_draft_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "draft_version_id",
            sa.Integer(),
            sa.ForeignKey("incubator_draft_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("incubator_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("retry_of_attempt_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_incubator_draft_attempts_draft_version_id",
        "incubator_draft_attempts",
        ["draft_version_id"],
    )
    op.create_index(
        "ix_incubator_draft_attempts_job_id",
        "incubator_draft_attempts",
        ["job_id"],
    )
    with op.batch_alter_table("incubator_draft_versions") as batch_op:
        batch_op.create_foreign_key(
            "fk_incubator_draft_versions_attempt_id",
            "incubator_draft_attempts",
            ["attempt_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_incubator_draft_versions_attempt_id",
            ["attempt_id"],
        )

    with op.batch_alter_table("incubator_jobs") as batch_op:
        batch_op.drop_constraint("ck_incubator_jobs_single_owner", type_="check")
        batch_op.add_column(
            sa.Column(
                "draft_plan_item_id",
                sa.Integer(),
                sa.ForeignKey(
                    "incubator_draft_plan_items.id",
                    ondelete="CASCADE",
                    name="fk_incubator_jobs_draft_plan_item_id",
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "draft_version_id",
                sa.Integer(),
                sa.ForeignKey(
                    "incubator_draft_versions.id",
                    ondelete="CASCADE",
                    name="fk_incubator_jobs_draft_version_id",
                ),
                nullable=True,
            )
        )
        batch_op.create_index("ix_incubator_jobs_draft_plan_item_id", ["draft_plan_item_id"])
        batch_op.create_index("ix_incubator_jobs_draft_version_id", ["draft_version_id"])
        batch_op.create_check_constraint(
            "ck_incubator_jobs_single_owner",
            _job_owner_check(),
        )

    with op.batch_alter_table("incubator_token_ledger") as batch_op:
        batch_op.add_column(
            sa.Column(
                "draft_attempt_id",
                sa.Integer(),
                sa.ForeignKey(
                    "incubator_draft_attempts.id",
                    ondelete="SET NULL",
                    name="fk_incubator_token_ledger_draft_attempt_id",
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "draft_version_id",
                sa.Integer(),
                sa.ForeignKey(
                    "incubator_draft_versions.id",
                    ondelete="SET NULL",
                    name="fk_incubator_token_ledger_draft_version_id",
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "draft_id",
                sa.Integer(),
                sa.ForeignKey(
                    "incubator_drafts.id",
                    ondelete="SET NULL",
                    name="fk_incubator_token_ledger_draft_id",
                ),
                nullable=True,
            )
        )
        batch_op.create_index(
            "ix_incubator_token_ledger_draft_attempt_id",
            ["draft_attempt_id"],
        )
        batch_op.create_index(
            "ix_incubator_token_ledger_draft_version_id",
            ["draft_version_id"],
        )
        batch_op.create_index(
            "ix_incubator_token_ledger_draft_id",
            ["draft_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("incubator_token_ledger") as batch_op:
        batch_op.drop_index("ix_incubator_token_ledger_draft_attempt_id")
        batch_op.drop_index("ix_incubator_token_ledger_draft_version_id")
        batch_op.drop_index("ix_incubator_token_ledger_draft_id")
        batch_op.drop_constraint(
            "fk_incubator_token_ledger_draft_attempt_id",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_incubator_token_ledger_draft_version_id",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_incubator_token_ledger_draft_id",
            type_="foreignkey",
        )
        batch_op.drop_column("draft_attempt_id")
        batch_op.drop_column("draft_version_id")
        batch_op.drop_column("draft_id")

    with op.batch_alter_table("incubator_jobs") as batch_op:
        batch_op.drop_constraint("ck_incubator_jobs_single_owner", type_="check")
        batch_op.drop_index("ix_incubator_jobs_draft_plan_item_id")
        batch_op.drop_index("ix_incubator_jobs_draft_version_id")
        batch_op.drop_constraint(
            "fk_incubator_jobs_draft_plan_item_id",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_incubator_jobs_draft_version_id",
            type_="foreignkey",
        )
        batch_op.drop_column("draft_plan_item_id")
        batch_op.drop_column("draft_version_id")
        batch_op.create_check_constraint(
            "ck_incubator_jobs_single_owner",
            "(event_id IS NOT NULL) + (revision_id IS NOT NULL) + "
            "(audit_plan_item_id IS NOT NULL) + (audit_version_id IS NOT NULL) + "
            "(connection_test_id IS NOT NULL) = 1",
        )

    with op.batch_alter_table("incubator_draft_versions") as batch_op:
        batch_op.drop_index("ix_incubator_draft_versions_attempt_id")
        batch_op.drop_constraint(
            "fk_incubator_draft_versions_attempt_id",
            type_="foreignkey",
        )

    op.drop_table("incubator_draft_attempts")
    op.drop_table("incubator_draft_versions")
    op.drop_table("incubator_drafts")
    op.drop_table("incubator_draft_anchors")
    op.drop_table("incubator_draft_plan_items")
    op.drop_table("incubator_draft_plans")
