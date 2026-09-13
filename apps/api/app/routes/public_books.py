from __future__ import annotations

from typing import cast

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..dependencies import DbSession
from ..knowledge_links import serialize_backlinks, serialize_wikilinks
from ..models import BookNote
from ..pagination import PageLimit, PageOffset
from ..schemas import PublicBookNote, ReadingStatus

router = APIRouter(prefix="/books", tags=["public book notes"])


def public_response(note: BookNote, db: DbSession) -> PublicBookNote:
    revision = note.current_revision
    assert revision is not None
    path = (
        f"/books/{revision.first_published_at.year:04d}/"
        f"{revision.first_published_at.month:02d}/{revision.slug}"
    )
    return PublicBookNote(
        id=note.id,
        book_title=revision.book_title,
        author=revision.author,
        slug=revision.slug,
        cover_url=revision.cover_url,
        reading_status=cast(ReadingStatus, revision.reading_status),
        reading_date=revision.reading_date,
        rating=revision.rating,
        summary=revision.summary,
        content=revision.content,
        published_at=revision.first_published_at,
        updated_at=revision.published_at,
        public_path=path,
        backlinks=serialize_backlinks(db, "book", note.id),
        wikilinks=serialize_wikilinks(db, revision.content),
    )


@router.get("", response_model=list[PublicBookNote])
def list_public_notes(
    db: DbSession,
    limit: PageLimit = 20,
    offset: PageOffset = 0,
) -> list[PublicBookNote]:
    notes = db.scalars(
        select(BookNote)
        .options(selectinload(BookNote.current_revision))
        .where(
            BookNote.status == "published",
            BookNote.deleted_at.is_(None),
            BookNote.current_revision_id.is_not(None),
        )
        .order_by(BookNote.published_at.desc(), BookNote.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [public_response(note, db) for note in notes]


@router.get("/{year}/{month}/{slug}", response_model=PublicBookNote)
def get_public_note(year: int, month: int, slug: str, db: DbSession) -> PublicBookNote:
    note = db.scalar(
        select(BookNote)
        .options(selectinload(BookNote.current_revision))
        .where(
            BookNote.slug == slug,
            BookNote.status == "published",
            BookNote.deleted_at.is_(None),
            BookNote.current_revision_id.is_not(None),
        )
    )
    if (
        note is None
        or note.current_revision is None
        or note.current_revision.first_published_at.year != year
        or note.current_revision.first_published_at.month != month
    ):
        raise HTTPException(status_code=404, detail="book note not found")
    return public_response(note, db)
