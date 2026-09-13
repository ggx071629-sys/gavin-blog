from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from ..dependencies import DbSession
from ..models import Article, ArticleRevision, ArticleRevisionTag, Category, Tag
from ..schemas import PublicTaxonomy, TaxonomyOption

router = APIRouter(prefix="/taxonomy", tags=["public taxonomy"])


@router.get("", response_model=PublicTaxonomy)
def get_public_taxonomy(db: DbSession) -> PublicTaxonomy:
    category_rows = db.execute(
        select(Category.id, Category.name, Category.slug, func.count(Article.id))
        .join(ArticleRevision, ArticleRevision.category_id == Category.id)
        .join(Article, Article.current_revision_id == ArticleRevision.id)
        .where(Article.status == "published", Article.deleted_at.is_(None))
        .group_by(Category.id, Category.name, Category.slug)
        .order_by(Category.name)
    ).all()
    tag_rows = db.execute(
        select(Tag.id, Tag.name, Tag.slug, func.count(Article.id))
        .join(ArticleRevisionTag, ArticleRevisionTag.tag_id == Tag.id)
        .join(ArticleRevision, ArticleRevision.id == ArticleRevisionTag.revision_id)
        .join(Article, Article.current_revision_id == ArticleRevision.id)
        .where(Article.status == "published", Article.deleted_at.is_(None))
        .group_by(Tag.id, Tag.name, Tag.slug)
        .order_by(Tag.name)
    ).all()
    total_article_count = db.scalar(
        select(func.count(Article.id)).where(
            Article.status == "published",
            Article.deleted_at.is_(None),
        )
    )
    return PublicTaxonomy(
        categories=[
            TaxonomyOption(id=row.id, name=row.name, slug=row.slug, article_count=row[3])
            for row in category_rows
        ],
        tags=[
            TaxonomyOption(id=row.id, name=row.name, slug=row.slug, article_count=row[3])
            for row in tag_rows
        ],
        total_article_count=int(total_article_count or 0),
    )
