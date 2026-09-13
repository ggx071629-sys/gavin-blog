from __future__ import annotations

import hashlib
import json
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    BookNote,
    BookNoteRevision,
    Project,
    ProjectRevision,
    ProjectRevisionArticle,
)
from .time_utils import utc_now


def _sha256(payload: dict) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def canonical_project_sha256(
    *,
    title: str,
    slug: str,
    summary: str,
    content: str,
    repository_url: str | None,
    website_url: str | None,
    article_ids: list[int],
) -> str:
    return _sha256(
        {
            "title": title,
            "slug": slug,
            "summary": summary,
            "content": content,
            "repository_url": repository_url,
            "website_url": website_url,
            "article_ids": sorted(article_ids),
        }
    )


def canonical_book_note_sha256(
    *,
    book_title: str,
    author: str,
    slug: str,
    cover_url: str | None,
    reading_status: str,
    reading_date: date | None,
    rating: int | None,
    summary: str,
    content: str,
) -> str:
    return _sha256(
        {
            "book_title": book_title,
            "author": author,
            "slug": slug,
            "cover_url": cover_url,
            "reading_status": reading_status,
            "reading_date": reading_date.isoformat() if reading_date else None,
            "rating": rating,
            "summary": summary,
            "content": content,
        }
    )


def current_project_content_hash(project: Project) -> str:
    return canonical_project_sha256(
        title=project.title,
        slug=project.slug,
        summary=project.summary,
        content=project.content,
        repository_url=project.repository_url,
        website_url=project.website_url,
        article_ids=[article.id for article in project.articles],
    )


def current_book_note_content_hash(note: BookNote) -> str:
    return canonical_book_note_sha256(
        book_title=note.book_title,
        author=note.author,
        slug=note.slug,
        cover_url=note.cover_url,
        reading_status=note.reading_status,
        reading_date=note.reading_date,
        rating=note.rating,
        summary=note.summary,
        content=note.content,
    )


def create_project_publish_revision(
    db: Session,
    project: Project,
    *,
    published_at: datetime | None = None,
) -> ProjectRevision:
    now = published_at or utc_now()
    if project.published_at is None:
        project.published_at = now
    latest = db.scalar(
        select(ProjectRevision.revision_number)
        .where(ProjectRevision.project_id == project.id)
        .order_by(ProjectRevision.revision_number.desc())
        .limit(1)
    )
    article_ids = sorted(article.id for article in project.articles)
    revision = ProjectRevision(
        project_id=project.id,
        revision_number=(latest or 0) + 1,
        title=project.title,
        slug=project.slug,
        summary=project.summary,
        content=project.content,
        repository_url=project.repository_url,
        website_url=project.website_url,
        first_published_at=project.published_at,
        published_at=now,
        content_sha256=current_project_content_hash(project),
    )
    db.add(revision)
    db.flush()
    for position, article_id in enumerate(article_ids):
        db.add(
            ProjectRevisionArticle(
                revision_id=revision.id,
                article_id=article_id,
                position=position,
            )
        )
    project.current_revision_id = revision.id
    db.expire(project, ["current_revision"])
    return revision


def create_book_note_publish_revision(
    db: Session,
    note: BookNote,
    *,
    published_at: datetime | None = None,
) -> BookNoteRevision:
    now = published_at or utc_now()
    if note.published_at is None:
        note.published_at = now
    latest = db.scalar(
        select(BookNoteRevision.revision_number)
        .where(BookNoteRevision.book_note_id == note.id)
        .order_by(BookNoteRevision.revision_number.desc())
        .limit(1)
    )
    revision = BookNoteRevision(
        book_note_id=note.id,
        revision_number=(latest or 0) + 1,
        book_title=note.book_title,
        author=note.author,
        slug=note.slug,
        cover_url=note.cover_url,
        reading_status=note.reading_status,
        reading_date=note.reading_date,
        rating=note.rating,
        summary=note.summary,
        content=note.content,
        first_published_at=note.published_at,
        published_at=now,
        content_sha256=current_book_note_content_hash(note),
    )
    db.add(revision)
    db.flush()
    note.current_revision_id = revision.id
    db.expire(note, ["current_revision"])
    return revision


def project_has_unpublished_changes(project: Project) -> bool:
    revision = project.current_revision
    if revision is None:
        return project.status == "published"
    return current_project_content_hash(project) != revision.content_sha256


def book_note_has_unpublished_changes(note: BookNote) -> bool:
    revision = note.current_revision
    if revision is None:
        return note.status == "published"
    return current_book_note_content_hash(note) != revision.content_sha256
