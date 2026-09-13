from __future__ import annotations

import difflib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from ..about_page_service import (
    admin_payload,
    create_publish_revision,
    get_or_create_about_page,
    has_unpublished_changes,
    parse_content,
    serialize_content,
)
from ..dependencies import DbSession, require_admin, require_session_csrf
from ..models import AboutPageRevision, AdminSession
from ..pagination import PageLimit, PageOffset
from ..schemas import (
    AboutPageAdmin,
    AboutPageContent,
    AboutPageRollbackRequest,
    AboutPageUpdate,
    AboutRevisionDetail,
    AboutRevisionDiffResponse,
    AboutRevisionListResponse,
    AboutRevisionSummary,
    PublishRequest,
)
from ..time_utils import utc_now

router = APIRouter(prefix="/admin/about-page", tags=["admin about page"])


def _page_or_create(db: DbSession) -> AboutPageAdmin:
    return admin_payload(db, get_or_create_about_page(db))


def _revision_or_404(db: DbSession, page, revision_id: int) -> AboutPageRevision:
    revision = db.get(AboutPageRevision, revision_id)
    if revision is None or revision.about_page_id != page.id:
        raise HTTPException(status_code=404, detail="about page revision not found")
    return revision


def _revision_summary(revision: AboutPageRevision) -> AboutRevisionSummary:
    return AboutRevisionSummary(
        id=revision.id,
        revision_number=revision.revision_number,
        source=revision.source,
        published_at=revision.published_at,
        content_sha256=revision.content_sha256,
        rollback_from_revision_id=revision.rollback_from_revision_id,
    )


def _revision_detail(revision: AboutPageRevision) -> AboutRevisionDetail:
    return AboutRevisionDetail(
        **_revision_summary(revision).model_dump(),
        content=parse_content(revision.content_json),
    )


def _capability_lines(content: AboutPageContent) -> list[str]:
    lines: list[str] = []
    for capability in content.capabilities:
        lines.append(
            f"- {capability.title}: {capability.description} "
            f"({', '.join(capability.tags)})"
        )
    return lines


def _now_lines(content: AboutPageContent) -> list[str]:
    lines: list[str] = []
    for item in content.now:
        lines.append(f"- {item.label} [{item.status}] -> {item.target}")
    return lines


def _site_lines(content: AboutPageContent) -> list[str]:
    lines: list[str] = [content.site.description]
    for entry in content.site.stack:
        lines.append(f"{entry.label}: {entry.value}")
    return lines


def _diff(before: list[str], after: list[str]) -> str:
    return "\n".join(
        difflib.unified_diff(
            before,
            after,
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )


def _single_diff(before: list[str], after: list[str], label: str) -> str:
    value = _diff(before, after)
    return f"# {label}\n{value}" if value else ""


@router.get("", response_model=AboutPageAdmin)
def get_admin_about_page(
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
) -> AboutPageAdmin:
    return _page_or_create(db)


@router.patch("", response_model=AboutPageAdmin)
def update_about_page(
    payload: AboutPageUpdate,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> AboutPageAdmin:
    page = get_or_create_about_page(db)
    if page.version != payload.version:
        raise HTTPException(status_code=409, detail="about page was updated elsewhere")
    page.content_json = serialize_content(payload.content)
    page.version += 1
    page.updated_at = utc_now()
    db.commit()
    db.refresh(page)
    return admin_payload(db, page)


@router.post("/publish", response_model=AboutPageAdmin)
def publish_about_page(
    payload: PublishRequest,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> AboutPageAdmin:
    page = get_or_create_about_page(db)
    if page.version != payload.version:
        raise HTTPException(status_code=409, detail="about page was updated elsewhere")
    content = parse_content(page.content_json)
    if not content.statement.strip():
        raise HTTPException(status_code=422, detail="statement is required")
    create_publish_revision(db, page)
    page.version += 1
    page.updated_at = utc_now()
    db.commit()
    db.refresh(page)
    return admin_payload(db, page)


@router.get("/revisions", response_model=AboutRevisionListResponse)
def list_about_revisions(
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
    limit: PageLimit = 20,
    offset: PageOffset = 0,
) -> AboutRevisionListResponse:
    page = get_or_create_about_page(db)
    total = (
        db.scalar(
            select(func.count(AboutPageRevision.id)).where(
                AboutPageRevision.about_page_id == page.id
            )
        )
        or 0
    )
    revisions = list(
        db.scalars(
            select(AboutPageRevision)
            .where(AboutPageRevision.about_page_id == page.id)
            .order_by(AboutPageRevision.revision_number.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return AboutRevisionListResponse(
        total=total,
        revisions=[_revision_summary(revision) for revision in revisions],
    )


@router.get("/revisions/{revision_id}", response_model=AboutRevisionDetail)
def get_about_revision(
    revision_id: int,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
) -> AboutRevisionDetail:
    page = get_or_create_about_page(db)
    return _revision_detail(_revision_or_404(db, page, revision_id))


@router.get("/revision-diff", response_model=AboutRevisionDiffResponse)
def about_revision_diff(
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
    from_revision_id: int,
    to_revision_id: int,
) -> AboutRevisionDiffResponse:
    page = get_or_create_about_page(db)
    before = _revision_detail(_revision_or_404(db, page, from_revision_id)).content
    after = _revision_detail(_revision_or_404(db, page, to_revision_id)).content
    return AboutRevisionDiffResponse(
        from_revision_id=from_revision_id,
        to_revision_id=to_revision_id,
        statement=_single_diff(
            [before.statement],
            [after.statement],
            "statement",
        ),
        capabilities=_single_diff(
            _capability_lines(before),
            _capability_lines(after),
            "capabilities",
        ),
        now=_single_diff(_now_lines(before), _now_lines(after), "now"),
        editorial_topics=_single_diff(
            before.editorial_topics,
            after.editorial_topics,
            "editorial_topics",
        ),
        site=_single_diff(_site_lines(before), _site_lines(after), "site"),
    )


@router.post(
    "/revisions/{revision_id}/rollback",
    response_model=AboutPageAdmin,
)
def rollback_about_revision(
    revision_id: int,
    payload: AboutPageRollbackRequest,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> AboutPageAdmin:
    page = get_or_create_about_page(db)
    revision = _revision_or_404(db, page, revision_id)
    if not payload.rollback_confirmed:
        raise HTTPException(status_code=422, detail="rollback confirmation is required")
    if (
        page.version != payload.version
        or page.current_revision_id != payload.current_revision_id
    ):
        raise HTTPException(status_code=409, detail="about page version changed")
    if page.status != "published":
        raise HTTPException(
            status_code=422,
            detail="only a published about page can be rolled back",
        )
    if has_unpublished_changes(db, page):
        raise HTTPException(
            status_code=409,
            detail="about page has unpublished changes; resolve them before rollback",
        )
    page.content_json = revision.content_json
    page.version += 1
    page.updated_at = utc_now()
    new_revision = create_publish_revision(db, page, source="rollback")
    new_revision.rollback_from_revision_id = revision.id
    db.commit()
    db.refresh(page)
    return admin_payload(db, page)
