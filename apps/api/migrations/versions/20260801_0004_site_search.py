"""Add the published-content FTS5 index.

Revision ID: 20260801_0004
Revises: 20260801_0003
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260801_0004"
down_revision: str | Sequence[str] | None = "20260801_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE VIRTUAL TABLE search_index USING fts5(
            content_type UNINDEXED,
            content_id UNINDEXED,
            title,
            summary,
            body,
            taxonomy,
            public_path UNINDEXED,
            published_at UNINDEXED,
            tokenize = 'unicode61 remove_diacritics 2'
        )
        """
    )
    op.execute(
        """
        INSERT INTO search_index
            (content_type, content_id, title, summary, body, taxonomy, public_path, published_at)
        SELECT 'article', a.id, a.title, a.summary, a.content,
               trim(coalesce(c.name, '') || ' ' || coalesce(group_concat(t.name, ' '), '')),
               '/notes/' || strftime('%Y', a.published_at) || '/' ||
                   strftime('%m', a.published_at) || '/' || a.slug,
               a.published_at
        FROM articles a
        LEFT JOIN categories c ON c.id = a.category_id
        LEFT JOIN article_tags at ON at.article_id = a.id
        LEFT JOIN tags t ON t.id = at.tag_id
        WHERE a.status = 'published' AND a.published_at IS NOT NULL
        GROUP BY a.id
        """
    )
    op.execute(
        """
        INSERT INTO search_index
            (content_type, content_id, title, summary, body, taxonomy, public_path, published_at)
        SELECT 'project', id, title, summary, content, '', '/projects/' || slug, published_at
        FROM projects WHERE status = 'published' AND published_at IS NOT NULL
        """
    )
    op.execute(
        """
        INSERT INTO search_index
            (content_type, content_id, title, summary, body, taxonomy, public_path, published_at)
        SELECT 'book', id, book_title, summary, content, author,
               '/books/' || strftime('%Y', published_at) || '/' ||
                   strftime('%m', published_at) || '/' || slug,
               published_at
        FROM book_notes WHERE status = 'published' AND published_at IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE search_index")
