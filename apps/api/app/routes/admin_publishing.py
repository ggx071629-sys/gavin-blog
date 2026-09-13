from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from ..article_revision_history import (
    ArticleRevisionError,
    get_revision_or_404,
    list_article_revisions,
    revision_diff,
    rollback_article,
)
from ..dependencies import DbSession, require_admin, require_session_csrf
from ..http_errors import ApiException
from ..models import AdminSession, Article, ArticleRevision, Category, Tag
from ..pagination import PageLimit, PageOffset
from ..schemas import (
    ApiErrorResponse,
    ArticleRevisionDetail,
    ArticleRevisionDiffResponse,
    ArticleRevisionListResponse,
    ArticleRevisionSummary,
    ArticleRollbackRequest,
    PublicReference,
    TaxonomyItem,
)

router = APIRouter(prefix="/admin", tags=["admin article revisions"])


def api_error(status_code: int, code: str, message: str) -> ApiException:
    return ApiException(status_code=status_code, code=code, message=message)


def _article_or_404(db: DbSession, article_id: int) -> Article:
    article = db.get(Article, article_id)
    if article is None or article.deleted_at is not None:
        raise HTTPException(status_code=404, detail="article not found")
    return article


def _revision_category(
    db: DbSession,
    article: Article,
    revision: ArticleRevision,
) -> TaxonomyItem | None:
    category = db.get(Category, article.category_id) if article.category_id is not None else None
    if category is not None:
        return TaxonomyItem.model_validate(category)
    if revision.category_id is not None:
        return TaxonomyItem(
            id=revision.category_id,
            name=revision.category_name,
            slug=revision.category_slug,
            description="",
        )
    return None


def _revision_tags(
    db: DbSession,
    revision: ArticleRevision,
) -> list[TaxonomyItem]:
    tag_ids = [tag.tag_id for tag in revision.tags]
    rows = list(db.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all()) if tag_ids else []
    live = {tag.id: tag for tag in rows}
    return [
        TaxonomyItem(
            id=tag.tag_id,
            name=live[tag.tag_id].name if tag.tag_id in live else tag.name,
            slug=live[tag.tag_id].slug if tag.tag_id in live else tag.slug,
            description=live[tag.tag_id].description if tag.tag_id in live else "",
        )
        for tag in revision.tags
    ]


def _references(revision: ArticleRevision) -> list[PublicReference]:
    return [
        PublicReference(
            display_title=entry.display_title,
            url=entry.url,
        )
        for entry in revision.public_references
        if entry.enabled
    ]


def _revision_summary(revision: ArticleRevision) -> ArticleRevisionSummary:
    return ArticleRevisionSummary(
        id=revision.id,
        revision_number=revision.revision_number,
        title=revision.title,
        slug=revision.slug,
        source=revision.source,
        published_at=revision.published_at,
        content_sha256=revision.content_sha256,
        rollback_from_revision_id=revision.rollback_from_revision_id,
    )


def _revision_detail(
    db: DbSession,
    article: Article,
    revision: ArticleRevision,
) -> ArticleRevisionDetail:
    return ArticleRevisionDetail(
        id=revision.id,
        article_id=article.id,
        revision_number=revision.revision_number,
        title=revision.title,
        slug=revision.slug,
        summary=revision.summary,
        content=revision.content,
        category=_revision_category(db, article, revision),
        tags=_revision_tags(db, revision),
        references=_references(revision),
        source=revision.source,
        published_at=revision.published_at,
        first_published_at=revision.first_published_at,
        content_sha256=revision.content_sha256,
        rollback_from_revision_id=revision.rollback_from_revision_id,
    )


@router.get(
    "/articles/{article_id}/revisions",
    response_model=ArticleRevisionListResponse,
)
def get_article_revisions(
    article_id: int,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
    limit: PageLimit = 20,
    offset: PageOffset = 0,
) -> ArticleRevisionListResponse:
    article = _article_or_404(db, article_id)
    total = (
        db.scalar(
            select(func.count(ArticleRevision.id)).where(ArticleRevision.article_id == article.id)
        )
        or 0
    )
    revisions = list_article_revisions(
        db,
        article.id,
        limit=limit,
        offset=offset,
    )
    return ArticleRevisionListResponse(
        total=total,
        revisions=[_revision_summary(revision) for revision in revisions],
    )


@router.get(
    "/articles/{article_id}/revisions/{revision_id}",
    response_model=ArticleRevisionDetail,
)
def get_article_revision(
    article_id: int,
    revision_id: int,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
) -> ArticleRevisionDetail:
    article = _article_or_404(db, article_id)
    try:
        revision = get_revision_or_404(db, article.id, revision_id)
    except ArticleRevisionError as error:
        raise api_error(404, error.code, error.message) from error
    return _revision_detail(db, article, revision)


@router.get(
    "/articles/{article_id}/revision-diff",
    response_model=ArticleRevisionDiffResponse,
)
def get_article_revision_diff(
    article_id: int,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
    from_revision_id: Annotated[int, Query(ge=1)],
    to_revision_id: Annotated[int, Query(ge=1)],
) -> ArticleRevisionDiffResponse:
    article = _article_or_404(db, article_id)
    try:
        diff = revision_diff(
            db,
            article.id,
            from_revision_id=from_revision_id,
            to_revision_id=to_revision_id,
        )
    except ArticleRevisionError as error:
        raise api_error(422, error.code, error.message) from error
    return ArticleRevisionDiffResponse(**diff)


@router.post(
    "/articles/{article_id}/revisions/{revision_id}/rollback",
    response_model=ArticleRevisionDetail,
    responses={409: {"model": ApiErrorResponse}, 422: {"model": ApiErrorResponse}},
)
def rollback_revision(
    article_id: int,
    revision_id: int,
    payload: ArticleRollbackRequest,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> ArticleRevisionDetail:
    article = _article_or_404(db, article_id)
    try:
        revision = get_revision_or_404(db, article.id, revision_id)
        new_revision = rollback_article(
            db,
            article=article,
            revision=revision,
            version=payload.version,
            current_revision_id=payload.current_revision_id,
            rollback_confirmed=payload.rollback_confirmed,
        )
        db.commit()
    except ArticleRevisionError as error:
        status_code = 422 if error.code == "PUBLISH_NOT_ELIGIBLE" else 409
        raise api_error(status_code, error.code, error.message) from error
    db.refresh(article)
    return _revision_detail(db, article, new_revision)
