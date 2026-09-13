from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..dependencies import DbSession
from ..knowledge_links import serialize_backlinks, serialize_wikilinks
from ..models import Article, Project, ProjectRevision
from ..pagination import PageLimit, PageOffset
from ..schemas import PublicProject, RelatedArticle

router = APIRouter(prefix="/projects", tags=["public projects"])


def related_article(article: Article) -> RelatedArticle:
    revision = article.current_revision
    assert revision is not None
    path = (
        f"/notes/{revision.first_published_at.year:04d}/"
        f"{revision.first_published_at.month:02d}/{revision.slug}"
    )
    return RelatedArticle(
        id=article.id,
        title=revision.title,
        slug=revision.slug,
        summary=revision.summary,
        published_at=revision.first_published_at,
        public_path=path,
    )


def public_response(project: Project, db: DbSession) -> PublicProject:
    revision = project.current_revision
    assert revision is not None
    article_ids = [link.article_id for link in revision.article_links]
    articles = (
        list(
            db.scalars(
                select(Article)
                .options(selectinload(Article.current_revision))
                .where(
                    Article.id.in_(article_ids),
                    Article.status == "published",
                    Article.deleted_at.is_(None),
                    Article.current_revision_id.is_not(None),
                )
            ).all()
        )
        if article_ids
        else []
    )
    articles.sort(
        key=lambda article: (
            article.current_revision.first_published_at
            if article.current_revision is not None
            else article.updated_at
        ),
        reverse=True,
    )
    return PublicProject(
        id=project.id,
        title=revision.title,
        slug=revision.slug,
        summary=revision.summary,
        content=revision.content,
        repository_url=revision.repository_url,
        website_url=revision.website_url,
        published_at=revision.first_published_at,
        updated_at=revision.published_at,
        public_path=f"/projects/{revision.slug}",
        related_articles=[related_article(article) for article in articles],
        backlinks=serialize_backlinks(db, "project", project.id),
        wikilinks=serialize_wikilinks(db, revision.content),
    )


@router.get("", response_model=list[PublicProject])
def list_public_projects(
    db: DbSession,
    limit: PageLimit = 20,
    offset: PageOffset = 0,
) -> list[PublicProject]:
    projects = db.scalars(
        select(Project)
        .options(
            selectinload(Project.current_revision).selectinload(
                ProjectRevision.article_links
            )
        )
        .where(
            Project.status == "published",
            Project.deleted_at.is_(None),
            Project.current_revision_id.is_not(None),
        )
        .order_by(Project.published_at.desc(), Project.id.desc())
        .limit(limit)
        .offset(offset)
    ).unique().all()
    return [public_response(project, db) for project in projects]


@router.get("/{slug}", response_model=PublicProject)
def get_public_project(slug: str, db: DbSession) -> PublicProject:
    project = db.scalar(
        select(Project)
        .options(
            selectinload(Project.current_revision).selectinload(
                ProjectRevision.article_links
            )
        )
        .where(
            Project.slug == slug,
            Project.status == "published",
            Project.deleted_at.is_(None),
            Project.current_revision_id.is_not(None),
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return public_response(project, db)
