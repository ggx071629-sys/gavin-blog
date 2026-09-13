from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from ..admin_list_query import ListSearch, ListStatus, query_content
from ..assistant_index.outbox import enqueue_for_content
from ..content_revisions import (
    book_note_has_unpublished_changes,
    create_book_note_publish_revision,
)
from ..dependencies import DbSession, require_admin, require_session_csrf
from ..markdown_media import missing_image_alt_location
from ..models import AdminSession, BookNote
from ..pagination import PageLimit, PageOffset
from ..schemas import (
    BookListQueryResponse,
    BookNoteCreate,
    BookNoteResponse,
    BookNoteUpdate,
    PublishRequest,
)
from ..search import sync_search_document
from ..time_utils import utc_now

router = APIRouter(prefix="/admin/books", tags=["admin book notes"])


def book_response(note: BookNote) -> BookNoteResponse:
    revision = note.current_revision
    public_path = None
    if revision is not None and note.deleted_at is None:
        public_path = (
            f"/books/{revision.first_published_at.year:04d}/"
            f"{revision.first_published_at.month:02d}/{revision.slug}"
        )
    return BookNoteResponse.model_validate(note).model_copy(
        update={
            "public_path": public_path,
            "current_revision_id": note.current_revision_id,
            "current_publish_revision": (
                revision.revision_number if revision is not None else None
            ),
            "has_unpublished_changes": book_note_has_unpublished_changes(note),
        }
    )


def get_note_or_404(note_id: int, db: DbSession) -> BookNote:
    note = db.get(BookNote, note_id)
    if note is None or note.deleted_at is not None:
        raise HTTPException(status_code=404, detail="book note not found")
    return note


def book_data(payload: BookNoteCreate | BookNoteUpdate, exclude: set[str]) -> dict:
    data = payload.model_dump(exclude=exclude, exclude_none=True)
    if "cover_url" in data:
        data["cover_url"] = str(data["cover_url"])
    return data


@router.get("/query", response_model=BookListQueryResponse)
def query_books(
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
    q: ListSearch = "",
    status: ListStatus | None = None,
    limit: PageLimit = 20,
    offset: PageOffset = 0,
) -> dict:
    return query_content(
        db,
        BookNote,
        (
            BookNote.book_title,
            BookNote.author,
        ),
        q,
        status,
        limit,
        offset,
        book_response,
        tuple(selectinload(field) for field in (BookNote.current_revision,)),
    )


@router.get("", response_model=list[BookNoteResponse])
def list_notes(
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
    limit: PageLimit = 20,
    offset: PageOffset = 0,
) -> list[BookNoteResponse]:
    notes = db.scalars(
        select(BookNote)
        .options(selectinload(BookNote.current_revision))
        .where(BookNote.deleted_at.is_(None))
        .order_by(BookNote.updated_at.desc(), BookNote.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [book_response(note) for note in notes]


@router.post("", response_model=BookNoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    payload: BookNoteCreate,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> BookNoteResponse:
    note = BookNote(**book_data(payload, set()))
    db.add(note)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="book note slug already exists") from error
    db.refresh(note)
    return book_response(note)


@router.get("/{note_id}", response_model=BookNoteResponse)
def get_note(
    note_id: int,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
) -> BookNoteResponse:
    return book_response(get_note_or_404(note_id, db))


@router.patch("/{note_id}", response_model=BookNoteResponse)
def update_note(
    note_id: int,
    payload: BookNoteUpdate,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> BookNoteResponse:
    note = get_note_or_404(note_id, db)
    if note.version != payload.version:
        raise HTTPException(status_code=409, detail="book note was updated elsewhere")
    if (
        note.status == "published"
        and "slug" in payload.model_fields_set
        and payload.slug != note.slug
    ):
        raise HTTPException(status_code=409, detail="published book note slug cannot be changed")
    for field in ("cover_url", "reading_date", "rating"):
        if field in payload.model_fields_set and getattr(payload, field) is None:
            setattr(note, field, None)
    for field, value in book_data(payload, {"version"}).items():
        setattr(note, field, value)
    note.version += 1
    note.updated_at = utc_now()
    if note.status != "published":
        sync_search_document(db, note)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="book note slug already exists") from error
    db.refresh(note)
    return book_response(note)


@router.post("/{note_id}/publish", response_model=BookNoteResponse)
def publish_note(
    note_id: int,
    payload: PublishRequest,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> BookNoteResponse:
    get_note_or_404(note_id, db)
    note = db.scalar(
        select(BookNote)
        .options(selectinload(BookNote.current_revision))
        .where(BookNote.id == note_id)
    )
    assert note is not None
    if note.version != payload.version:
        raise HTTPException(status_code=409, detail="book note was updated elsewhere")
    if not note.book_title.strip() or not note.author.strip() or not note.content.strip():
        raise HTTPException(status_code=422, detail="book title, author, and content are required")
    missing_alt = missing_image_alt_location(note.content)
    if missing_alt is not None:
        line, column = missing_alt
        raise HTTPException(
            status_code=422,
            detail=f"image alt text is required at line {line}, column {column}",
        )
    try:
        create_book_note_publish_revision(db, note)
        note.status = "published"
        note.version += 1
        note.updated_at = utc_now()
        from ..knowledge_links import rebuild_content_links

        rebuild_content_links(db, note)
        sync_search_document(db, note)
        enqueue_for_content(db, note)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="book note was updated elsewhere",
        ) from error
    db.refresh(note)
    return book_response(note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def trash_note(
    note_id: int,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> Response:
    note = get_note_or_404(note_id, db)
    note.deleted_at = utc_now()
    note.version += 1
    from ..knowledge_links import clear_content_links

    clear_content_links(db, note)
    sync_search_document(db, note)
    enqueue_for_content(db, note)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
