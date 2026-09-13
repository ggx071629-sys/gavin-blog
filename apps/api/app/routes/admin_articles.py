from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from ..admin_list_query import ListSearch, ListStatus, query_content
from ..article_revisions import (
    create_publish_revision,
    has_unpublished_changes,
    refresh_revision_content_hash,
)
from ..assistant_index.outbox import enqueue_for_content
from ..dependencies import DbSession, require_admin, require_session_csrf
from ..knowledge_links import (
    clear_content_links,
    rebuild_content_links,
    replace_working_references,
    serialize_wikilinks,
    serialize_working_references,
    snapshot_working_references,
)
from ..markdown_media import missing_image_alt_location
from ..models import AdminSession, Article, Category, Tag
from ..pagination import PageLimit, PageOffset
from ..schemas import (
    ArticleCreate,
    ArticleListQueryResponse,
    ArticleResponse,
    ArticleUpdate,
    PublishRequest,
)
from ..search import sync_search_document
from ..time_utils import utc_now

router = APIRouter(prefix="/admin/articles", tags=["admin articles"])


def article_response(article: Article) -> ArticleResponse:
    public_path = None
    if article.published_at is not None and article.deleted_at is None:
        public_path = (
            f"/notes/{article.published_at.year:04d}/{article.published_at.month:02d}/"
            f"{article.slug}"
        )
    revision = article.current_revision
    session = article_session(article)
    return ArticleResponse.model_validate(article).model_copy(
        update={
            "public_path": public_path,
            "current_revision_id": article.current_revision_id,
            "current_publish_revision": (
                revision.revision_number if revision is not None else None
            ),
            "has_unpublished_changes": has_unpublished_changes(article),
            "references": serialize_working_references(article),
            "wikilinks": (
                serialize_wikilinks(session, article.content) if session is not None else []
            ),
        }
    )


def article_session(article: Article):
    from sqlalchemy.orm import object_session

    return object_session(article)


@router.get("/query", response_model=ArticleListQueryResponse)
def query_articles(
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
    q: ListSearch = "",
    status: ListStatus | None = None,
    limit: PageLimit = 20,
    offset: PageOffset = 0,
) -> dict:
    return query_content(
        db,
        Article,
        (Article.title,),
        q,
        status,
        limit,
        offset,
        article_response,
        tuple(
            selectinload(field)
            for field in (
                Article.category,
                Article.tags,
                Article.current_revision,
                Article.working_references,
            )
        ),
    )


@router.get("", response_model=list[ArticleResponse])
def list_articles(
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
    limit: PageLimit = 20,
    offset: PageOffset = 0,
) -> list[ArticleResponse]:
    articles = (
        db.scalars(
            select(Article)
            .options(
                selectinload(Article.category),
                selectinload(Article.tags),
                selectinload(Article.current_revision),
                selectinload(Article.working_references),
            )
            .where(Article.deleted_at.is_(None))
            .order_by(Article.updated_at.desc(), Article.id.desc())
            .limit(limit)
            .offset(offset)
        )
        .unique()
        .all()
    )
    return [article_response(article) for article in articles]


@router.post("", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
def create_article(
    payload: ArticleCreate,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> ArticleResponse:
    category, tags = resolve_taxonomy(db, payload.category_id, payload.tag_ids)
    article = Article(
        **payload.model_dump(exclude={"category_id", "tag_ids", "references"}),
        category=category,
        tags=tags,
    )
    db.add(article)
    try:
        db.flush()
        replace_working_references(db, article, payload.references)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="slug already exists") from error
    db.refresh(article)
    return article_response(article)


def get_article_or_404(article_id: int, db: DbSession) -> Article:
    article = db.get(Article, article_id)
    if article is None or article.deleted_at is not None:
        raise HTTPException(status_code=404, detail="article not found")
    return article


def resolve_taxonomy(
    db: DbSession,
    category_id: int | None,
    tag_ids: list[int],
) -> tuple[Category | None, list[Tag]]:
    category = db.get(Category, category_id) if category_id is not None else None
    if category_id is not None and category is None:
        raise HTTPException(status_code=422, detail="category does not exist")
    unique_tag_ids = set(tag_ids)
    tags = (
        list(db.scalars(select(Tag).where(Tag.id.in_(unique_tag_ids))).all())
        if unique_tag_ids
        else []
    )
    if len(tags) != len(unique_tag_ids):
        raise HTTPException(status_code=422, detail="one or more tags do not exist")
    return category, tags


@router.get("/{article_id}", response_model=ArticleResponse)
def get_article(
    article_id: int,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
) -> ArticleResponse:
    return article_response(get_article_or_404(article_id, db))


@router.patch("/{article_id}", response_model=ArticleResponse)
def update_article(
    article_id: int,
    payload: ArticleUpdate,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> ArticleResponse:
    article = get_article_or_404(article_id, db)
    if article.version != payload.version:
        raise HTTPException(status_code=409, detail="article was updated elsewhere")
    if (
        article.status == "published"
        and "slug" in payload.model_fields_set
        and payload.slug != article.slug
    ):
        raise HTTPException(status_code=409, detail="published article slug cannot be changed")
    if "category_id" in payload.model_fields_set:
        category, _resolved_tags = resolve_taxonomy(db, payload.category_id, [])
        article.category = category
    if "tag_ids" in payload.model_fields_set:
        if payload.tag_ids is None:
            raise HTTPException(status_code=422, detail="tag_ids cannot be null")
        _resolved_category, tags = resolve_taxonomy(db, None, payload.tag_ids)
        article.tags = tags
    for field, value in payload.model_dump(
        exclude={"version", "category_id", "tag_ids", "references"},
        exclude_none=True,
    ).items():
        setattr(article, field, value)
    if "references" in payload.model_fields_set:
        if payload.references is None:
            raise HTTPException(status_code=422, detail="references cannot be null")
        replace_working_references(db, article, payload.references)
    article.version += 1
    article.updated_at = utc_now()
    if article.status != "published":
        # Published working-copy autosaves must never leak into public search;
        # the search index only follows publish revisions.
        sync_search_document(db, article)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="slug already exists") from error
    db.refresh(article)
    return article_response(article)


@router.post("/{article_id}/publish", response_model=ArticleResponse)
def publish_article(
    article_id: int,
    payload: PublishRequest,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> ArticleResponse:
    article = get_article_or_404(article_id, db)
    loaded = db.scalar(
        select(Article)
        .options(
            selectinload(Article.category),
            selectinload(Article.tags),
            selectinload(Article.current_revision),
            selectinload(Article.working_references),
        )
        .where(Article.id == article_id)
    )
    assert loaded is not None
    article = loaded
    if article.version != payload.version:
        raise HTTPException(status_code=409, detail="article was updated elsewhere")
    if not article.title.strip() or not article.content.strip():
        raise HTTPException(status_code=422, detail="title and content are required")
    missing_alt = missing_image_alt_location(article.content)
    if missing_alt is not None:
        line, column = missing_alt
        raise HTTPException(
            status_code=422,
            detail=f"image alt text is required at line {line}, column {column}",
        )
    revision = create_publish_revision(db, article)
    snapshot_working_references(db, article, revision.id)
    refresh_revision_content_hash(db, article, revision)
    article.status = "published"
    article.version += 1
    article.updated_at = utc_now()
    rebuild_content_links(db, article)
    sync_search_document(db, article)
    enqueue_for_content(db, article)
    db.commit()
    db.refresh(article)
    return article_response(article)


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def trash_article(
    article_id: int,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> Response:
    article = get_article_or_404(article_id, db)
    article.deleted_at = utc_now()
    article.version += 1
    clear_content_links(db, article)
    sync_search_document(db, article)
    enqueue_for_content(db, article)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
