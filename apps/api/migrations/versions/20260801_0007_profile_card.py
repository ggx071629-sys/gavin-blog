"""Add the singleton personal profile table.

Revision ID: 20260801_0007
Revises: 20260801_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "20260801_0007"
down_revision: str | Sequence[str] | None = "20260801_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("bio", sa.String(length=240), nullable=False),
        sa.Column("skills_json", sa.Text(), nullable=False),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("city", sa.String(length=80), nullable=True),
        sa.Column("city_visible", sa.Boolean(), nullable=False),
        sa.Column("github_url", sa.String(length=500), nullable=True),
        sa.Column("email", sa.String(length=160), nullable=True),
        sa.Column("email_visible", sa.Boolean(), nullable=False),
        sa.Column("resume_url", sa.String(length=500), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.execute(
        text(
            "INSERT INTO profiles "
            "(id, name, title, bio, skills_json, avatar_url, city, city_visible, "
            "github_url, email, email_visible, resume_url, version, created_at, updated_at) "
            "VALUES (1, :name, :title, :bio, '[]', NULL, NULL, 0, NULL, NULL, 0, NULL, 1, "
            "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ).bindparams(
            name="Gavin",
            title="后端工程师 / AI 应用开发者",
            bio="这里记录工程实践、问题排查与项目复盘，只留下持续校准过的技术笔记。",
        )
    )


def downgrade() -> None:
    op.drop_table("profiles")
