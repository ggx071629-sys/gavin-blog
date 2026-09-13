from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import AboutPage, AboutPageRevision
from .profile_service import DEFAULT_BIO
from .schemas import AboutPageAdmin, AboutPageContent
from .time_utils import utc_now

ABOUT_PAGE_SINGLETON_ID = 1


def default_about_content() -> AboutPageContent:
    """Structured copy matching the current public About page before this feature."""
    return AboutPageContent(
        statement=DEFAULT_BIO,
        capabilities=[
            {
                "title": "后端工程",
                "description": "从 API、数据库到服务架构，构建能够真正运行和持续维护的后端系统。",
                "tags": ["Python", "FastAPI", "SQL"],
            },
            {
                "title": "AI 应用",
                "description": (
                    "把 LLM 接入实际业务，而不止停留在 Demo。包括 "
                    "RAG、Agent、工具调用与应用后端。"
                ),
                "tags": ["LLM", "RAG", "Agent"],
            },
            {
                "title": "产品构建",
                "description": (
                    "从一个想法开始，完成技术方案、前后端实现，"
                    "直到部署成一个真正可以使用的产品。"
                ),
                "tags": ["Nuxt", "API", "Deployment"],
            },
            {
                "title": "问题排查",
                "description": "定位那些“不应该出问题，但就是出问题了”的问题。",
                "tags": ["Debugging", "Performance", "Infrastructure"],
            },
        ],
        now=[
            {
                "label": "重构这个网站",
                "status": "in_progress",
                "target": "projects",
            },
            {
                "label": "一个 AI 应用",
                "status": "building",
                "target": "projects",
            },
            {
                "label": "最近正在研究的技术",
                "status": "exploring",
                "target": "articles",
            },
        ],
        editorial_topics=["工程实践", "问题排查", "AI 应用", "项目复盘"],
        site={
            "description": "这里记录做过的事情、踩过的坑，以及随着实践不断改变的认识。",
            "stack": [
                {"label": "WRITING", "value": "Markdown"},
                {"label": "FRONTEND", "value": "Nuxt 4 SSR"},
                {"label": "BACKEND", "value": "FastAPI"},
                {"label": "DATABASE", "value": "SQLite WAL"},
            ],
        },
    )


def serialize_content(content: AboutPageContent) -> str:
    return json.dumps(
        content.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def parse_content(raw: str) -> AboutPageContent:
    return AboutPageContent.model_validate_json(raw)


def canonical_about_sha256(content: AboutPageContent) -> str:
    payload = json.dumps(
        content.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def working_content_sha256(page: AboutPage) -> str:
    return canonical_about_sha256(parse_content(page.content_json))


def get_about_page(db: Session) -> AboutPage | None:
    return db.get(AboutPage, ABOUT_PAGE_SINGLETON_ID)


def _seed_initial_revision(db: Session, page: AboutPage, *, now: datetime | None = None) -> None:
    now = now or utc_now()
    content = parse_content(page.content_json)
    revision = AboutPageRevision(
        about_page_id=page.id,
        revision_number=1,
        content_json=page.content_json,
        content_sha256=canonical_about_sha256(content),
        source="editor",
        assistant_eligible=False,
        first_published_at=now,
        published_at=now,
        created_at=now,
    )
    db.add(revision)
    db.flush()
    page.current_revision_id = revision.id
    page.published_at = now
    page.status = "published"


def get_or_create_about_page(db: Session) -> AboutPage:
    """Return the singleton working copy, seeding an initial published revision."""
    page = get_about_page(db)
    if page is None:
        page = AboutPage(
            id=ABOUT_PAGE_SINGLETON_ID,
            content_json=serialize_content(default_about_content()),
            status="published",
            version=1,
        )
        db.add(page)
        db.flush()
        _seed_initial_revision(db, page)
        db.commit()
        db.refresh(page)
    elif page.current_revision_id is None:
        _seed_initial_revision(db, page)
        db.commit()
        db.refresh(page)
    return page


def current_revision(db: Session, page: AboutPage) -> AboutPageRevision | None:
    if page.current_revision_id is None:
        return None
    return db.get(AboutPageRevision, page.current_revision_id)


def has_unpublished_changes(db: Session, page: AboutPage) -> bool:
    revision = current_revision(db, page)
    if revision is None:
        return page.status == "published"
    return working_content_sha256(page) != revision.content_sha256


def next_revision_number(db: Session, page: AboutPage) -> int:
    latest = db.scalar(
        select(func.max(AboutPageRevision.revision_number)).where(
            AboutPageRevision.about_page_id == page.id
        )
    )
    return (latest or 0) + 1


def create_publish_revision(
    db: Session,
    page: AboutPage,
    *,
    source: str = "editor",
    now: datetime | None = None,
) -> AboutPageRevision:
    """Append the next immutable revision and point the page at it."""
    now = now or utc_now()
    content = parse_content(page.content_json)
    revision = AboutPageRevision(
        about_page_id=page.id,
        revision_number=next_revision_number(db, page),
        content_json=page.content_json,
        content_sha256=canonical_about_sha256(content),
        source=source,
        assistant_eligible=True,
        first_published_at=page.published_at or now,
        published_at=now,
        created_at=now,
    )
    db.add(revision)
    db.flush()
    page.current_revision_id = revision.id
    page.published_at = page.published_at or now
    page.status = "published"
    page.updated_at = now
    db.expire(page, ["revisions"])
    from .assistant_index.outbox import enqueue_about

    enqueue_about(db, page)
    return revision


def admin_payload(db: Session, page: AboutPage) -> AboutPageAdmin:
    revision = current_revision(db, page)
    return AboutPageAdmin(
        id=page.id,
        content=parse_content(page.content_json),
        status=page.status,
        version=page.version,
        current_revision_id=page.current_revision_id,
        current_publish_revision=revision.revision_number if revision is not None else None,
        has_unpublished_changes=has_unpublished_changes(db, page),
        published_at=page.published_at,
        created_at=page.created_at,
        updated_at=page.updated_at,
    )
