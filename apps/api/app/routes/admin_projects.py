from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from ..admin_list_query import ListSearch, ListStatus, query_content
from ..assistant_index.outbox import enqueue_for_content
from ..content_revisions import (
    create_project_publish_revision,
    project_has_unpublished_changes,
)
from ..dependencies import DbSession, require_admin, require_session_csrf
from ..markdown_media import missing_image_alt_location
from ..models import AdminSession, Article, Project
from ..pagination import PageLimit, PageOffset
from ..schemas import (
    ProjectCreate,
    ProjectListQueryResponse,
    ProjectResponse,
    ProjectUpdate,
    PublishRequest,
)
from ..search import sync_search_document
from ..time_utils import utc_now

router = APIRouter(prefix="/admin/projects", tags=["admin projects"])


def project_response(project: Project) -> ProjectResponse:
    revision = project.current_revision
    public_path = (
        f"/projects/{revision.slug}"
        if revision is not None and project.deleted_at is None
        else None
    )
    return ProjectResponse.model_validate(project).model_copy(
        update={
            "public_path": public_path,
            "article_ids": sorted(article.id for article in project.articles),
            "current_revision_id": project.current_revision_id,
            "current_publish_revision": (
                revision.revision_number if revision is not None else None
            ),
            "has_unpublished_changes": project_has_unpublished_changes(project),
        }
    )


def get_project_or_404(project_id: int, db: DbSession) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.deleted_at is not None:
        raise HTTPException(status_code=404, detail="project not found")
    return project


def resolve_articles(db: DbSession, article_ids: list[int]) -> list[Article]:
    unique_ids = set(article_ids)
    articles = (
        list(
            db.scalars(
                select(Article).where(
                    Article.id.in_(unique_ids),
                    Article.deleted_at.is_(None),
                )
            ).all()
        )
        if unique_ids
        else []
    )
    if len(articles) != len(unique_ids):
        raise HTTPException(status_code=422, detail="one or more articles do not exist")
    return articles


def project_data(payload: ProjectCreate | ProjectUpdate, exclude: set[str]) -> dict:
    data = payload.model_dump(exclude=exclude, exclude_none=True)
    for field in ("repository_url", "website_url"):
        if field in data:
            data[field] = str(data[field])
    return data


@router.get("/query", response_model=ProjectListQueryResponse)
def query_projects(
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
    q: ListSearch = "",
    status: ListStatus | None = None,
    limit: PageLimit = 20,
    offset: PageOffset = 0,
) -> dict:
    return query_content(
        db,
        Project,
        (Project.title,),
        q,
        status,
        limit,
        offset,
        project_response,
        tuple(
            selectinload(field)
            for field in (
                Project.articles,
                Project.current_revision,
            )
        ),
    )


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
    limit: PageLimit = 20,
    offset: PageOffset = 0,
) -> list[ProjectResponse]:
    projects = (
        db.scalars(
            select(Project)
            .options(
                selectinload(Project.articles),
                selectinload(Project.current_revision),
            )
            .where(Project.deleted_at.is_(None))
            .order_by(Project.updated_at.desc(), Project.id.desc())
            .limit(limit)
            .offset(offset)
        )
        .unique()
        .all()
    )
    return [project_response(project) for project in projects]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> ProjectResponse:
    project = Project(
        **project_data(payload, {"article_ids"}),
        articles=resolve_articles(db, payload.article_ids),
    )
    db.add(project)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="project slug already exists") from error
    db.refresh(project)
    return project_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
) -> ProjectResponse:
    return project_response(get_project_or_404(project_id, db))


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> ProjectResponse:
    project = get_project_or_404(project_id, db)
    if project.version != payload.version:
        raise HTTPException(status_code=409, detail="project was updated elsewhere")
    if (
        project.status == "published"
        and "slug" in payload.model_fields_set
        and payload.slug != project.slug
    ):
        raise HTTPException(status_code=409, detail="published project slug cannot be changed")
    if "article_ids" in payload.model_fields_set:
        if payload.article_ids is None:
            raise HTTPException(status_code=422, detail="article_ids cannot be null")
        project.articles = resolve_articles(db, payload.article_ids)
    for field in ("repository_url", "website_url"):
        if field in payload.model_fields_set and getattr(payload, field) is None:
            setattr(project, field, None)
    for field, value in project_data(payload, {"version", "article_ids"}).items():
        setattr(project, field, value)
    project.version += 1
    project.updated_at = utc_now()
    if project.status != "published":
        sync_search_document(db, project)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="project slug already exists") from error
    db.refresh(project)
    return project_response(project)


@router.post("/{project_id}/publish", response_model=ProjectResponse)
def publish_project(
    project_id: int,
    payload: PublishRequest,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> ProjectResponse:
    get_project_or_404(project_id, db)
    project = db.scalar(
        select(Project)
        .options(
            selectinload(Project.articles),
            selectinload(Project.current_revision),
        )
        .where(Project.id == project_id)
    )
    assert project is not None
    if project.version != payload.version:
        raise HTTPException(status_code=409, detail="project was updated elsewhere")
    if not project.title.strip() or not project.content.strip():
        raise HTTPException(status_code=422, detail="title and content are required")
    missing_alt = missing_image_alt_location(project.content)
    if missing_alt is not None:
        line, column = missing_alt
        raise HTTPException(
            status_code=422,
            detail=f"image alt text is required at line {line}, column {column}",
        )
    try:
        create_project_publish_revision(db, project)
        project.status = "published"
        project.version += 1
        project.updated_at = utc_now()
        from ..knowledge_links import rebuild_content_links

        rebuild_content_links(db, project)
        sync_search_document(db, project)
        enqueue_for_content(db, project)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="project was updated elsewhere",
        ) from error
    db.refresh(project)
    return project_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def trash_project(
    project_id: int,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> Response:
    project = get_project_or_404(project_id, db)
    project.deleted_at = utc_now()
    project.version += 1
    from ..knowledge_links import clear_content_links

    clear_content_links(db, project)
    sync_search_document(db, project)
    enqueue_for_content(db, project)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
