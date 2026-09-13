from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import selectinload

from ..dependencies import DbSession
from ..knowledge_links import serialize_backlinks, serialize_wikilinks
from ..models import Article, ArticleRevision, ArticleRevisionTag, Category, Tag
from ..pagination import PageLimit, PageOffset
from ..schemas import ArticleContext, PublicArticle, PublicReference, RelatedArticle, TaxonomyItem

router = APIRouter(prefix="/articles", tags=["public articles"])


def public_response(article: Article, db: DbSession) -> PublicArticle:
    assert article.published_at is not None
    revision = article.current_revision
    if revision is None and article.current_revision_id is not None:
        revision = db.get(ArticleRevision, article.current_revision_id)
    assert revision is not None, "published article must have a current revision"
    path = (
        f"/notes/{article.published_at.year:04d}/{article.published_at.month:02d}/"
        f"{revision.slug}"
    )
    category = _revision_category(db, article, revision)
    tags = _revision_tags(db, revision)
    references = [
        PublicReference(
            display_title=entry.display_title,
            url=entry.url,
        )
        for entry in revision.public_references
        if entry.enabled
    ]
    return PublicArticle(
        id=article.id,
        title=revision.title,
        slug=revision.slug,
        summary=revision.summary,
        content=revision.content,
        published_at=article.published_at,
        updated_at=(
            article.published_at
            if revision.revision_number == 1
            else revision.published_at
        ),
        public_path=path,
        category=category,
        tags=tags,
        references=references,
        wikilinks=serialize_wikilinks(db, revision.content),
    )


def _revision_category(
    db: DbSession,
    article: Article,
    revision: ArticleRevision,
) -> TaxonomyItem | None:
    del article
    if revision.category_id is None and not revision.category_slug:
        return None
    live = (
        db.get(Category, revision.category_id)
        if revision.category_id is not None
        else None
    )
    if live is not None:
        return TaxonomyItem.model_validate(live)
    if revision.category_id is None:
        return None
    return TaxonomyItem(
        id=revision.category_id,
        name=revision.category_name,
        slug=revision.category_slug,
        description="",
    )


def _revision_tags(
    db: DbSession,
    revision: ArticleRevision,
) -> list[TaxonomyItem]:
    tags = list(revision.tags)
    tag_ids = [tag.tag_id for tag in tags]
    rows = (
        list(db.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all())
        if tag_ids
        else []
    )
    live = {tag.id: tag for tag in rows}
    return [
        TaxonomyItem(
            id=tag.tag_id,
            name=live[tag.tag_id].name if tag.tag_id in live else tag.name,
            slug=live[tag.tag_id].slug if tag.tag_id in live else tag.slug,
            description=live[tag.tag_id].description if tag.tag_id in live else "",
        )
        for tag in tags
    ]


def _public_article_query():
    return (
        select(Article)
        .options(
            selectinload(Article.category),
            selectinload(Article.current_revision).selectinload(ArticleRevision.tags),
        )
        .where(Article.status == "published", Article.deleted_at.is_(None))
    )


def _find_public_article(
    db: DbSession,
    year: int,
    month: int,
    slug: str,
) -> Article:
    article = db.scalar(_public_article_query().where(Article.slug == slug))
    if (
        article is None
        or article.published_at is None
        or article.published_at.year != year
        or article.published_at.month != month
    ):
        raise HTTPException(status_code=404, detail="article not found")
    return article


def _related_response(article: Article, db: DbSession) -> RelatedArticle:
    public = public_response(article, db)
    return RelatedArticle(
        id=public.id,
        title=public.title,
        slug=public.slug,
        summary=public.summary,
        published_at=public.published_at,
        public_path=public.public_path,
    )


def _neighbor_article(db: DbSession, article: Article, *, newer: bool) -> Article | None:
    assert article.published_at is not None
    if newer:
        boundary = or_(
            Article.published_at > article.published_at,
            and_(Article.published_at == article.published_at, Article.id > article.id),
        )
        ordering = (Article.published_at.asc(), Article.id.asc())
    else:
        boundary = or_(
            Article.published_at < article.published_at,
            and_(Article.published_at == article.published_at, Article.id < article.id),
        )
        ordering = (Article.published_at.desc(), Article.id.desc())
    return db.scalar(_public_article_query().where(boundary).order_by(*ordering).limit(1))


def _related_articles(db: DbSession, article: Article) -> list[Article]:
    revision = article.current_revision
    if revision is None and article.current_revision_id is not None:
        revision = db.get(ArticleRevision, article.current_revision_id)
    assert revision is not None
    category_id = revision.category_id
    tag_ids = {tag.tag_id for tag in revision.tags}
    related_filters = []
    if category_id is not None:
        related_filters.append(ArticleRevision.category_id == category_id)
    if tag_ids:
        related_filters.append(
            ArticleRevision.tags.any(ArticleRevisionTag.tag_id.in_(tag_ids))
        )
    if not related_filters:
        return []

    candidates = db.scalars(
        _public_article_query()
        .join(ArticleRevision, Article.current_revision_id == ArticleRevision.id)
        .where(Article.id != article.id, or_(*related_filters))
    ).unique().all()

    def score(candidate: Article) -> tuple[int, int, float, int]:
        candidate_revision = candidate.current_revision
        assert candidate_revision is not None
        candidate_tags = {tag.tag_id for tag in candidate_revision.tags}
        return (
            int(category_id is not None and candidate_revision.category_id == category_id),
            len(tag_ids & candidate_tags),
            candidate.published_at.timestamp() if candidate.published_at else 0.0,
            candidate.id,
        )

    return sorted(candidates, key=score, reverse=True)[:3]


@router.get("", response_model=list[PublicArticle])
def list_public_articles(
    db: DbSession,
    category: str | None = None,
    tag: str | None = None,
    limit: PageLimit = 20,
    offset: PageOffset = 0,
) -> list[PublicArticle]:
    query = (
        select(Article)
        .options(
            selectinload(Article.category),
            selectinload(Article.tags),
            selectinload(Article.current_revision).selectinload(ArticleRevision.tags),
        )
        .where(Article.status == "published", Article.deleted_at.is_(None))
    )
    if category or tag:
        query = query.join(
            ArticleRevision,
            Article.current_revision_id == ArticleRevision.id,
        )
    if category:
        query = query.outerjoin(Category, Category.id == ArticleRevision.category_id).where(
            or_(
                Category.slug == category,
                and_(Category.id.is_(None), ArticleRevision.category_slug == category),
            )
        )
    if tag:
        query = query.join(
            ArticleRevisionTag,
            ArticleRevisionTag.revision_id == ArticleRevision.id,
        ).outerjoin(Tag, Tag.id == ArticleRevisionTag.tag_id).where(
            or_(
                Tag.slug == tag,
                and_(Tag.id.is_(None), ArticleRevisionTag.slug == tag),
            )
        )
    articles = db.scalars(
        query.order_by(Article.published_at.desc(), Article.id.desc())
        .limit(limit)
        .offset(offset)
    ).unique().all()
    return [public_response(article, db) for article in articles]


@router.get("/{year}/{month}/{slug}", response_model=PublicArticle)
def get_public_article(year: int, month: int, slug: str, db: DbSession) -> PublicArticle:
    return public_response(_find_public_article(db, year, month, slug), db)


@router.get("/{year}/{month}/{slug}/context", response_model=ArticleContext)
def get_public_article_context(
    year: int,
    month: int,
    slug: str,
    db: DbSession,
) -> ArticleContext:
    article = _find_public_article(db, year, month, slug)
    previous = _neighbor_article(db, article, newer=False)
    next_article = _neighbor_article(db, article, newer=True)
    return ArticleContext(
        previous=_related_response(previous, db) if previous else None,
        next=_related_response(next_article, db) if next_article else None,
        related=[_related_response(candidate, db) for candidate in _related_articles(db, article)],
        backlinks=serialize_backlinks(db, "article", article.id),
    )
