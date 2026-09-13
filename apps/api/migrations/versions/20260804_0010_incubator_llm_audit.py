"""Add LLM audit entities: plans, versions, attempts, evidence, token ledger.

Revision ID: 20260804_0010
Revises: 20260803_0009
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260804_0010"
down_revision: str | Sequence[str] | None = "20260803_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _job_owner_check() -> str:
    return (
        "(event_id IS NOT NULL) + (revision_id IS NOT NULL) + "
        "(audit_plan_item_id IS NOT NULL) + (audit_version_id IS NOT NULL) + "
        "(connection_test_id IS NOT NULL) = 1"
    )


def upgrade() -> None:
    op.create_table(
        "incubator_audit_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("mode", sa.String(length=8), nullable=False),
        sa.Column("degraded", sa.Boolean(), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_incubator_audit_plans_status",
        "incubator_audit_plans",
        ["status"],
    )
    op.create_table(
        "incubator_audit_plan_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("incubator_audit_plans.id", ondelete="CASCADE"),
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
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("source_title", sa.String(length=180), nullable=False),
        sa.Column("source_token_estimate", sa.Integer(), nullable=False),
        sa.Column("evidence_chunks_json", sa.Text(), nullable=False),
        sa.Column("retrieval_snapshot_json", sa.Text(), nullable=False),
        sa.Column("manifest_json", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.String(length=24), nullable=False),
        sa.Column("context_estimate_json", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("previous_audit_id", sa.Integer(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        "ix_incubator_audit_plan_items_plan_id",
        "incubator_audit_plan_items",
        ["plan_id"],
    )
    op.create_index(
        "ix_incubator_audit_plan_items_source_id",
        "incubator_audit_plan_items",
        ["source_id"],
    )
    op.create_index(
        "ix_incubator_audit_plan_items_source_revision_id",
        "incubator_audit_plan_items",
        ["source_revision_id"],
    )
    op.create_index(
        "ix_incubator_audit_plan_items_status",
        "incubator_audit_plan_items",
        ["status"],
    )
    op.create_table(
        "incubator_audit_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_item_id",
            sa.Integer(),
            sa.ForeignKey("incubator_audit_plan_items.id", ondelete="RESTRICT"),
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
        sa.Column("audit_number", sa.Integer(), nullable=False),
        sa.Column("previous_audit_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("ai_role", sa.String(length=16), nullable=True),
        sa.Column("ai_target_article_id", sa.Integer(), nullable=True),
        sa.Column("ai_target_revision_id", sa.Integer(), nullable=True),
        sa.Column("effective_role", sa.String(length=16), nullable=True),
        sa.Column("effective_target_article_id", sa.Integer(), nullable=True),
        sa.Column("effective_target_revision_id", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("confidence_level", sa.String(length=8), nullable=True),
        sa.Column("degraded", sa.Boolean(), nullable=False),
        sa.Column("requires_split", sa.Boolean(), nullable=False),
        sa.Column("split_reason", sa.Text(), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("expected_output_type", sa.String(length=60), nullable=True),
        sa.Column("expected_output_scope", sa.Text(), nullable=True),
        sa.Column("risks_json", sa.Text(), nullable=False),
        sa.Column("uncertainties_json", sa.Text(), nullable=False),
        sa.Column("target_article_id", sa.Integer(), nullable=True),
        sa.Column("target_revision_id", sa.Integer(), nullable=True),
        sa.Column("other_article_ids_json", sa.Text(), nullable=False),
        sa.Column(
            "human_selected_outside_candidates",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column("reference_warnings_json", sa.Text(), nullable=False),
        sa.Column("retrieval_model", sa.String(length=64), nullable=False),
        sa.Column("retrieval_manifest", sa.String(length=64), nullable=False),
        sa.Column("retrieval_pipeline", sa.String(length=24), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("prompt_version", sa.String(length=24), nullable=False),
        sa.Column("provider_service", sa.String(length=200), nullable=False),
        sa.Column("provider_model", sa.String(length=200), nullable=False),
        sa.Column("response_sha256", sa.String(length=64), nullable=True),
        sa.Column("validation_error", sa.String(length=500), nullable=True),
        sa.Column("validation_error_code", sa.String(length=64), nullable=True),
        sa.Column("stale_reason", sa.String(length=64), nullable=True),
        sa.Column("human_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("source_id", "audit_number"),
    )
    op.create_index(
        "ix_incubator_audit_versions_plan_item_id",
        "incubator_audit_versions",
        ["plan_item_id"],
    )
    op.create_index(
        "ix_incubator_audit_versions_source_id",
        "incubator_audit_versions",
        ["source_id"],
    )
    op.create_index(
        "ix_incubator_audit_versions_source_revision_id",
        "incubator_audit_versions",
        ["source_revision_id"],
    )
    op.create_index(
        "ix_incubator_audit_versions_status",
        "incubator_audit_versions",
        ["status"],
    )
    op.create_table(
        "incubator_audit_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_item_id",
            sa.Integer(),
            sa.ForeignKey("incubator_audit_plan_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("revision_id", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.String(length=320), nullable=False),
        sa.Column("fragment_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_incubator_audit_candidates_plan_item_id",
        "incubator_audit_candidates",
        ["plan_item_id"],
    )
    op.create_table(
        "incubator_audit_evidence_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_item_id",
            sa.Integer(),
            sa.ForeignKey("incubator_audit_plan_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_id", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("source_revision_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("plan_item_id", "chunk_id"),
    )
    op.create_index(
        "ix_incubator_audit_evidence_chunks_plan_item_id",
        "incubator_audit_evidence_chunks",
        ["plan_item_id"],
    )
    op.create_table(
        "incubator_audit_judgments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "audit_version_id",
            sa.Integer(),
            sa.ForeignKey("incubator_audit_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("evidence_chunk_ids_json", sa.Text(), nullable=False),
        sa.Column("target_article_id", sa.Integer(), nullable=True),
        sa.Column("target_revision_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("audit_version_id", "position"),
    )
    op.create_index(
        "ix_incubator_audit_judgments_audit_version_id",
        "incubator_audit_judgments",
        ["audit_version_id"],
    )
    op.create_table(
        "incubator_audit_human_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "audit_version_id",
            sa.Integer(),
            sa.ForeignKey("incubator_audit_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("previous_role", sa.String(length=16), nullable=True),
        sa.Column("new_role", sa.String(length=16), nullable=True),
        sa.Column("previous_target_article_id", sa.Integer(), nullable=True),
        sa.Column("new_target_article_id", sa.Integer(), nullable=True),
        sa.Column("target_revision_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_incubator_audit_human_decisions_audit_version_id",
        "incubator_audit_human_decisions",
        ["audit_version_id"],
    )
    op.create_table(
        "incubator_audit_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "audit_version_id",
            sa.Integer(),
            sa.ForeignKey("incubator_audit_versions.id", ondelete="CASCADE"),
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
        "ix_incubator_audit_attempts_audit_version_id",
        "incubator_audit_attempts",
        ["audit_version_id"],
    )
    op.create_index(
        "ix_incubator_audit_attempts_job_id",
        "incubator_audit_attempts",
        ["job_id"],
    )
    op.create_table(
        "incubator_token_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_type", sa.String(length=24), nullable=False),
        sa.Column(
            "attempt_id",
            sa.Integer(),
            sa.ForeignKey("incubator_audit_attempts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "audit_version_id",
            sa.Integer(),
            sa.ForeignKey("incubator_audit_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "plan_item_id",
            sa.Integer(),
            sa.ForeignKey("incubator_audit_plan_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("precision", sa.String(length=24), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_incubator_token_ledger_task_type",
        "incubator_token_ledger",
        ["task_type"],
    )
    op.create_index(
        "ix_incubator_token_ledger_attempt_id",
        "incubator_token_ledger",
        ["attempt_id"],
    )
    op.create_index(
        "ix_incubator_token_ledger_audit_version_id",
        "incubator_token_ledger",
        ["audit_version_id"],
    )
    op.create_table(
        "incubator_llm_connection_tests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("token_precision", sa.String(length=24), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_incubator_llm_connection_tests_status",
        "incubator_llm_connection_tests",
        ["status"],
    )

    # The source pointer intentionally has no FK, matching current_revision_id.
    op.add_column(
        "incubator_sources",
        sa.Column("current_audit_version_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_incubator_sources_current_audit_version_id",
        "incubator_sources",
        ["current_audit_version_id"],
    )

    with op.batch_alter_table("incubator_jobs") as batch_op:
        batch_op.drop_constraint("ck_incubator_jobs_single_owner", type_="check")
        batch_op.add_column(
            sa.Column(
                "audit_plan_item_id",
                sa.Integer(),
                sa.ForeignKey(
                    "incubator_audit_plan_items.id",
                    ondelete="CASCADE",
                    name="fk_incubator_jobs_audit_plan_item_id",
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "audit_version_id",
                sa.Integer(),
                sa.ForeignKey(
                    "incubator_audit_versions.id",
                    ondelete="CASCADE",
                    name="fk_incubator_jobs_audit_version_id",
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "connection_test_id",
                sa.Integer(),
                sa.ForeignKey(
                    "incubator_llm_connection_tests.id",
                    ondelete="CASCADE",
                    name="fk_incubator_jobs_connection_test_id",
                ),
                nullable=True,
            )
        )
        batch_op.create_index("ix_incubator_jobs_audit_plan_item_id", ["audit_plan_item_id"])
        batch_op.create_index("ix_incubator_jobs_audit_version_id", ["audit_version_id"])
        batch_op.create_index("ix_incubator_jobs_connection_test_id", ["connection_test_id"])
        batch_op.create_check_constraint(
            "ck_incubator_jobs_single_owner",
            _job_owner_check(),
        )


def downgrade() -> None:
    with op.batch_alter_table("incubator_jobs") as batch_op:
        batch_op.drop_constraint("ck_incubator_jobs_single_owner", type_="check")
        batch_op.drop_index("ix_incubator_jobs_audit_plan_item_id")
        batch_op.drop_index("ix_incubator_jobs_audit_version_id")
        batch_op.drop_index("ix_incubator_jobs_connection_test_id")
        batch_op.drop_constraint(
            "fk_incubator_jobs_audit_plan_item_id",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_incubator_jobs_audit_version_id",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_incubator_jobs_connection_test_id",
            type_="foreignkey",
        )
        batch_op.drop_column("audit_plan_item_id")
        batch_op.drop_column("audit_version_id")
        batch_op.drop_column("connection_test_id")
        batch_op.create_check_constraint(
            "ck_incubator_jobs_single_owner",
            "(event_id IS NULL) <> (revision_id IS NULL)",
        )

    op.drop_index(
        "ix_incubator_sources_current_audit_version_id",
        table_name="incubator_sources",
    )
    op.drop_column("incubator_sources", "current_audit_version_id")

    op.drop_table("incubator_llm_connection_tests")
    op.drop_table("incubator_token_ledger")
    op.drop_table("incubator_audit_attempts")
    op.drop_table("incubator_audit_human_decisions")
    op.drop_table("incubator_audit_judgments")
    op.drop_table("incubator_audit_evidence_chunks")
    op.drop_table("incubator_audit_candidates")
    op.drop_table("incubator_audit_versions")
    op.drop_table("incubator_audit_plan_items")
    op.drop_table("incubator_audit_plans")
