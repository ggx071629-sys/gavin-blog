"""Add singleton About page working copy and immutable publish revisions.

Revision ID: 20260907_0024
Revises: 20260829_0023
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "20260907_0024"
down_revision: str | Sequence[str] | None = "20260829_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_BIO = "这里记录工程实践、问题排查与项目复盘，只留下持续校准过的技术笔记。"


def _content_json(statement: str) -> str:
    payload = {
        "statement": statement,
        "capabilities": [
            {
                "title": "后端工程",
                "description": "从 API、数据库到服务架构，构建能够真正运行和持续维护的后端系统。",
                "tags": ["Python", "FastAPI", "SQL"],
            },
            {
                "title": "AI 应用",
                "description": (
                    "把 LLM 接入实际业务，而不止停留在 Demo。包括 "
                    "RAG、Agent、工具调用与应用后端。"
                ),
                "tags": ["LLM", "RAG", "Agent"],
            },
            {
                "title": "产品构建",
                "description": (
                    "从一个想法开始，完成技术方案、前后端实现，"
                    "直到部署成一个真正可以使用的产品。"
                ),
                "tags": ["Nuxt", "API", "Deployment"],
            },
            {
                "title": "问题排查",
                "description": "定位那些“不应该出问题，但就是出问题了”的问题。",
                "tags": ["Debugging", "Performance", "Infrastructure"],
            },
        ],
        "now": [
            {"label": "重构这个网站", "status": "in_progress", "target": "projects"},
            {"label": "一个 AI 应用", "status": "building", "target": "projects"},
            {
                "label": "最近正在研究的技术",
                "status": "exploring",
                "target": "articles",
            },
        ],
        "editorial_topics": ["工程实践", "问题排查", "AI 应用", "项目复盘"],
        "site": {
            "description": "这里记录做过的事情、踩过的坑，以及随着实践不断改变的认识。",
            "stack": [
                {"label": "WRITING", "value": "Markdown"},
                {"label": "FRONTEND", "value": "Nuxt 4 SSR"},
                {"label": "BACKEND", "value": "FastAPI"},
                {"label": "DATABASE", "value": "SQLite WAL"},
            ],
        },
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def upgrade() -> None:
    op.create_table(
        "about_pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("current_revision_id", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_about_pages_status", "about_pages", ["status"])
    op.create_index(
        "ix_about_pages_current_revision_id",
        "about_pages",
        ["current_revision_id"],
    )
    op.create_table(
        "about_page_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "about_page_id",
            sa.Integer(),
            sa.ForeignKey("about_pages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("first_published_at", sa.DateTime(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("rollback_from_revision_id", sa.Integer(), nullable=True),
        sa.UniqueConstraint("about_page_id", "revision_number"),
        sa.CheckConstraint(
            "source IN ('editor', 'rollback')",
            name="ck_about_page_revisions_source",
        ),
    )
    op.create_index(
        "ix_about_page_revisions_about_page_id",
        "about_page_revisions",
        ["about_page_id"],
    )
    op.create_index(
        "ix_about_page_revisions_rollback_from_revision_id",
        "about_page_revisions",
        ["rollback_from_revision_id"],
    )

    bind = op.get_bind()
    profile = bind.execute(text("SELECT bio FROM profiles WHERE id = 1")).first()
    statement = profile[0] if profile is not None else DEFAULT_BIO
    content = _content_json(statement)
    digest = _sha256(content)
    bind.execute(
        text(
            "INSERT INTO about_pages("
            "id, content_json, status, version, current_revision_id, published_at, "
            "created_at, updated_at) VALUES ("
            "1, :content, 'published', 1, NULL, CURRENT_TIMESTAMP, "
            "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"content": content},
    )
    result = bind.execute(
        text(
            "INSERT INTO about_page_revisions("
            "about_page_id, revision_number, content_json, content_sha256, source, "
            "first_published_at, published_at, created_at) VALUES ("
            "1, 1, :content, :digest, 'editor', CURRENT_TIMESTAMP, "
            "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"content": content, "digest": digest},
    )
    revision_id = result.lastrowid
    bind.execute(
        text(
            "UPDATE about_pages SET current_revision_id = :revision_id WHERE id = 1"
        ),
        {"revision_id": revision_id},
    )


def downgrade() -> None:
    op.drop_table("about_page_revisions")
    op.drop_table("about_pages")
