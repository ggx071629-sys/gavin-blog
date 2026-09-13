"""Remove the retired knowledge-incubator persistence surface.

Revision ID: 20260826_0020
Revises: 20260814_0019

The deleted rows are preserved in the encrypted final archive.  Core article
revision, reference, taxonomy, search, and content-link tables remain intact.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20260826_0020"
down_revision: str | Sequence[str] | None = "20260814_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


RETIRED_TABLES = (
    "incubator_publish_source_links",
    "incubator_publish_operations",
    "incubator_token_ledger",
    "incubator_draft_attempts",
    "incubator_audit_attempts",
    "incubator_jobs",
    "incubator_publish_plan_items",
    "incubator_publish_plans",
    "incubator_draft_versions",
    "incubator_draft_anchors",
    "incubator_drafts",
    "incubator_draft_plan_items",
    "incubator_draft_plans",
    "incubator_audit_human_decisions",
    "incubator_audit_judgments",
    "incubator_audit_candidates",
    "incubator_audit_evidence_chunks",
    "incubator_audit_versions",
    "incubator_audit_plan_items",
    "incubator_audit_plans",
    "incubator_llm_connection_tests",
    "zvec_generation_requests",
    "incubator_worker_heartbeats",
    "incubator_raw_payloads",
    "incubator_revisions",
    "incubator_sources",
    "incubator_events",
    "incubator_batches",
    "article_embeddings",
    "article_index_segments",
    "article_index_pointers",
    "article_index_statuses",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
        bind.exec_driver_sql("DROP TABLE IF EXISTS incubator_fts")
    for table_name in RETIRED_TABLES:
        op.execute(f'DROP TABLE IF EXISTS "{table_name}"')
    if bind.dialect.name == "sqlite":
        bind.exec_driver_sql("PRAGMA foreign_keys=ON")


def downgrade() -> None:
    raise RuntimeError(
        "20260826_0020 is intentionally irreversible; restore the encrypted "
        "incubator-final archive before running the retired application"
    )
