from __future__ import annotations

import re
from datetime import datetime
from html import unescape
from typing import cast

from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from .models import (
    Article,
    ArticleRevision,
    BookNote,
    BookNoteRevision,
    Category,
    Project,
    ProjectRevision,
    Tag,
)
from .schemas import SearchResult
from .time_utils import as_utc

SEARCH_TABLE_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
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


def ensure_search_table(db: Session) -> None:
    db.execute(text(SEARCH_TABLE_SQL))


def _kind(content: Article | Project | BookNote) -> str:
    if isinstance(content, Article):
        return "article"
    if isinstance(content, Project):
        return "project"
    return "book"


def _document(
    db: Session,
    content: Article | Project | BookNote,
) -> tuple[str, str, str, str, str]:
    if isinstance(content, Article):
        assert content.published_at is not None
        return _article_document(db, content)
    if isinstance(content, Project):
        project_revision = content.current_revision
        if project_revision is None and content.current_revision_id is not None:
            project_revision = db.get(ProjectRevision, content.current_revision_id)
        assert project_revision is not None
        return (
            project_revision.title,
            project_revision.summary,
            project_revision.content,
            "",
            f"/projects/{project_revision.slug}",
        )
    book_revision = content.current_revision
    if book_revision is None and content.current_revision_id is not None:
        book_revision = db.get(BookNoteRevision, content.current_revision_id)
    assert book_revision is not None
    path = (
        f"/books/{book_revision.first_published_at.year:04d}/"
        f"{book_revision.first_published_at.month:02d}/{book_revision.slug}"
    )
    return (
        book_revision.book_title,
        book_revision.summary,
        book_revision.content,
        book_revision.author,
        path,
    )


def _article_document(
    db: Session,
    article: Article,
) -> tuple[str, str, str, str, str]:
    """Public search values come from the current publish revision.

    Title/summary/body are immutable snapshot values; taxonomy names resolve
    against the live category/tag rows so admin renames stay effective.
    """
    assert article.published_at is not None
    revision = article.current_revision
    if revision is None and article.current_revision_id is not None:
        revision = db.scalar(
            select(ArticleRevision)
            .options(selectinload(ArticleRevision.tags))
            .where(ArticleRevision.id == article.current_revision_id)
        )
    if revision is not None and article.status == "published":
        title = revision.title
        summary = revision.summary
        body = revision.content
        slug = revision.slug
        live_category = (
            db.get(Category, revision.category_id)
            if revision.category_id is not None
            else None
        )
        category_name = live_category.name if live_category else revision.category_name
        revision_tags = list(revision.tags)
        tag_ids = [tag.tag_id for tag in revision_tags]
        tag_rows = (
            list(db.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all())
            if tag_ids
            else []
        )
        tag_names_by_id = {tag.id: tag.name for tag in tag_rows}
        tag_names = [tag_names_by_id.get(tag.tag_id, tag.name) for tag in revision_tags]
    else:
        title = article.title
        summary = article.summary
        body = article.content
        slug = article.slug
        category = article.category
        if category is None and article.category_id is not None:
            category = db.get(Category, article.category_id)
        category_name = category.name if category else ""
        tag_names = [tag.name for tag in article.tags]
    taxonomy = " ".join([category_name] + list(tag_names))
    path = (
        f"/notes/{article.published_at.year:04d}/{article.published_at.month:02d}/"
        f"{slug}"
    )
    return title, summary, body, taxonomy, path


def sync_search_document(db: Session, content: Article | Project | BookNote) -> None:
    ensure_search_table(db)
    content_type = _kind(content)
    db.execute(
        text("DELETE FROM search_index WHERE content_type = :type AND content_id = :id"),
        {"type": content_type, "id": content.id},
    )
    if (
        content.status != "published"
        or content.deleted_at is not None
        or content.published_at is None
    ):
        return
    title, summary, body, taxonomy, path = _document(db, content)
    db.execute(
        text(
            """
            INSERT INTO search_index(
                content_type, content_id, title, summary, body, taxonomy, public_path, published_at
            ) VALUES (:type, :id, :title, :summary, :body, :taxonomy, :path, :published_at)
            """
        ),
        {
            "type": content_type,
            "id": content.id,
            "title": title,
            "summary": summary,
            "body": body,
            "taxonomy": taxonomy,
            "path": path,
            "published_at": content.published_at.isoformat(),
        },
    )


def rebuild_search_index(db: Session) -> None:
    ensure_search_table(db)
    db.execute(text("DELETE FROM search_index"))
    for model in (Article, Project, BookNote):
        query = select(model).where(model.status == "published", model.deleted_at.is_(None))
        for content in db.scalars(query).unique().all():
            sync_search_document(db, cast(Article | Project | BookNote, content))


def safe_match_query(query: str) -> str:
    terms = re.findall(r"[\w-]+", query, flags=re.UNICODE)
    return " ".join(f'"{term}"*' for term in terms[:12])


def markdown_to_plain_text(value: str) -> str:
    text_value = unescape(value or "")
    text_value = re.sub(r"```[^\n]*\n[\s\S]*?```|~~~[^\n]*\n[\s\S]*?~~~", " ", text_value)
    text_value = re.sub(r"```[^\n]*\n?|~~~[^\n]*\n?", " ", text_value)
    text_value = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text_value)
    text_value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text_value)
    text_value = re.sub(r"<[^>]+>", " ", text_value)
    text_value = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text_value)
    text_value = re.sub(r"(?m)^\s{0,3}(?:>|[-+*]\s+|\d+[.)]\s+)", "", text_value)
    text_value = re.sub(r"`([^`]+)`", r"\1", text_value)
    text_value = re.sub(r"(?:\*\*|__)(.+?)(?:\*\*|__)", r"\1", text_value)
    text_value = re.sub(r"~~(.+?)~~", r"\1", text_value)
    return re.sub(r"\s+", " ", text_value).strip()


def search(db: Session, query: str, limit: int, offset: int = 0) -> list[SearchResult]:
    ensure_search_table(db)
    match = safe_match_query(query)
    if not match:
        return []
    rows = db.execute(
        text(
            """
            SELECT content_type, CAST(content_id AS INTEGER) AS content_id, title, summary,
                   COALESCE(NULLIF(snippet(search_index, 4, '', '', ' … ', 20), ''), summary)
                       AS snippet,
                   public_path, published_at,
                   bm25(search_index, 0.0, 0.0, 7.0, 4.0, 1.5, 5.0, 0.0, 0.0) AS score
            FROM search_index
            WHERE search_index MATCH :query
            ORDER BY score, published_at DESC, CAST(content_id AS INTEGER) DESC
            LIMIT :limit
            OFFSET :offset
            """
        ),
        {"query": match, "limit": limit, "offset": offset},
    ).mappings()
    results = []
    for row in rows:
        data = dict(row)
        data["summary"] = markdown_to_plain_text(data["summary"])
        data["snippet"] = markdown_to_plain_text(data["snippet"]) or data["summary"]
        data["published_at"] = as_utc(datetime.fromisoformat(data["published_at"]))
        results.append(SearchResult(**data))
    return results
