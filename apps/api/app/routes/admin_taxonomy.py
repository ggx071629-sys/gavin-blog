from __future__ import annotations

from typing import Annotated, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..assistant_index.outbox import enqueue_for_content
from ..dependencies import DbSession, require_admin, require_session_csrf
from ..models import (
    AdminSession,
    Article,
    ArticleRevision,
    ArticleRevisionTag,
    Category,
    Tag,
    article_tags,
)
from ..schemas import TaxonomyCreate, TaxonomyItem, TaxonomyUpdate
from ..search import sync_search_document

router = APIRouter(prefix="/admin", tags=["admin taxonomy"])
TaxonomyModel = TypeVar("TaxonomyModel", Category, Tag)


def commit_or_conflict(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail) from error


def get_or_404(model: type[TaxonomyModel], item_id: int, db: Session) -> TaxonomyModel:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="taxonomy item not found")
    return item


def create_item(model: type[TaxonomyModel], payload: TaxonomyCreate, db: Session) -> TaxonomyItem:
    item = model(**payload.model_dump())
    db.add(item)
    commit_or_conflict(db, "taxonomy name or slug already exists")
    db.refresh(item)
    return TaxonomyItem.model_validate(item)


def update_item(
    model: type[TaxonomyModel],
    item_id: int,
    payload: TaxonomyUpdate,
    db: Session,
) -> tuple[TaxonomyModel, bool]:
    item = get_or_404(model, item_id, db)
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    name_changed = "name" in changes and changes["name"] != item.name
    for field, value in changes.items():
        setattr(item, field, value)
    return item, name_changed


@router.get("/categories", response_model=list[TaxonomyItem])
def list_categories(
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name)).all())


@router.post("/categories", response_model=TaxonomyItem, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: TaxonomyCreate,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> TaxonomyItem:
    return create_item(Category, payload, db)


@router.patch("/categories/{item_id}", response_model=TaxonomyItem)
def update_category(
    item_id: int,
    payload: TaxonomyUpdate,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> TaxonomyItem:
    item, name_changed = update_item(Category, item_id, payload, db)
    if name_changed:
        articles = db.scalars(
            select(Article)
            .join(ArticleRevision, Article.current_revision_id == ArticleRevision.id)
            .where(
                Article.status == "published",
                Article.deleted_at.is_(None),
                ArticleRevision.category_id == item_id,
            )
        ).unique().all()
        for article in articles:
            sync_search_document(db, article)
            enqueue_for_content(db, article)
    commit_or_conflict(db, "taxonomy name or slug already exists")
    db.refresh(item)
    return TaxonomyItem.model_validate(item)


@router.delete("/categories/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    item_id: int,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> Response:
    item = get_or_404(Category, item_id, db)
    if db.scalar(select(Article.id).where(Article.category_id == item_id).limit(1)) is not None:
        raise HTTPException(status_code=409, detail="category is used by an article")
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tags", response_model=list[TaxonomyItem])
def list_tags(
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
) -> list[Tag]:
    return list(db.scalars(select(Tag).order_by(Tag.name)).all())


@router.post("/tags", response_model=TaxonomyItem, status_code=status.HTTP_201_CREATED)
def create_tag(
    payload: TaxonomyCreate,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> TaxonomyItem:
    return create_item(Tag, payload, db)


@router.patch("/tags/{item_id}", response_model=TaxonomyItem)
def update_tag(
    item_id: int,
    payload: TaxonomyUpdate,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> TaxonomyItem:
    item, name_changed = update_item(Tag, item_id, payload, db)
    if name_changed:
        articles = db.scalars(
            select(Article)
            .join(ArticleRevision, Article.current_revision_id == ArticleRevision.id)
            .join(ArticleRevisionTag, ArticleRevisionTag.revision_id == ArticleRevision.id)
            .where(
                Article.status == "published",
                Article.deleted_at.is_(None),
                ArticleRevisionTag.tag_id == item_id,
            )
        ).unique().all()
        for article in articles:
            sync_search_document(db, article)
            enqueue_for_content(db, article)
    commit_or_conflict(db, "taxonomy name or slug already exists")
    db.refresh(item)
    return TaxonomyItem.model_validate(item)


@router.delete("/tags/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    item_id: int,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> Response:
    item = get_or_404(Tag, item_id, db)
    in_use = db.scalar(
        select(article_tags.c.article_id).where(article_tags.c.tag_id == item_id).limit(1)
    )
    if in_use is not None:
        raise HTTPException(status_code=409, detail="tag is used by an article")
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
