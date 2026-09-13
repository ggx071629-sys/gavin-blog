from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import (
    AboutPage,
    AboutPageRevision,
    Article,
    ArticleRevision,
    BookNote,
    BookNoteRevision,
    Category,
    Profile,
    Project,
    ProjectRevision,
    Tag,
)
from ..profile_service import PROFILE_SINGLETON_ID, default_profile, public_payload
from .constants import (
    DEFAULT_PIPELINE_VERSION,
    SOURCE_ABOUT,
    SOURCE_ARTICLE,
    SOURCE_BOOK,
    SOURCE_PROFILE,
    SOURCE_PROJECT,
)


@dataclass(frozen=True)
class SourceDocument:
    source_type: str
    source_id: int
    source_version: str
    title: str
    public_path: str
    body: str
    content_hash: str
    pipeline_version: str


def pipeline_version_from(db: Session) -> str:
    settings = db.info.get("settings")
    if settings is not None and getattr(settings, "assistant_pipeline_version", None):
        return str(settings.assistant_pipeline_version)
    return DEFAULT_PIPELINE_VERSION


def _hash_payload(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _article_taxonomy(db: Session, revision: ArticleRevision) -> tuple[str, list[str]]:
    live_category = (
        db.get(Category, revision.category_id) if revision.category_id is not None else None
    )
    category_name = live_category.name if live_category else revision.category_name
    revision_tags = list(revision.tags)
    tag_ids = [tag.tag_id for tag in revision_tags]
    tag_rows = list(db.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all()) if tag_ids else []
    names_by_id = {tag.id: tag.name for tag in tag_rows}
    tag_names = [names_by_id.get(tag.tag_id, tag.name) for tag in revision_tags]
    return category_name, tag_names


def _article_path(article: Article, slug: str) -> str:
    assert article.published_at is not None
    return (
        f"/notes/{article.published_at.year:04d}/{article.published_at.month:02d}/{slug}"
    )


def project_article(db: Session, article: Article) -> SourceDocument | None:
    if (
        article.status != "published"
        or article.deleted_at is not None
        or article.published_at is None
        or article.current_revision_id is None
    ):
        return None
    revision = article.current_revision
    if revision is None:
        revision = db.scalar(
            select(ArticleRevision)
            .options(selectinload(ArticleRevision.tags))
            .where(ArticleRevision.id == article.current_revision_id)
        )
    if revision is None:
        return None
    category_name, tag_names = _article_taxonomy(db, revision)
    taxonomy = " ".join([category_name, *tag_names]).strip()
    body = "\n\n".join(
        part for part in (revision.title, revision.summary, taxonomy, revision.content) if part
    )
    pipeline_version = pipeline_version_from(db)
    public_path = _article_path(article, revision.slug)
    payload = {
        "source_type": SOURCE_ARTICLE,
        "source_id": article.id,
        "source_version": str(revision.id),
        "title": revision.title,
        "summary": revision.summary,
        "taxonomy": taxonomy,
        "content": revision.content,
        "public_path": public_path,
        "pipeline_version": pipeline_version,
    }
    return SourceDocument(
        source_type=SOURCE_ARTICLE,
        source_id=article.id,
        source_version=str(revision.id),
        title=revision.title,
        public_path=public_path,
        body=body,
        content_hash=_hash_payload(payload),
        pipeline_version=pipeline_version,
    )


def project_project(db: Session, project: Project) -> SourceDocument | None:
    if (
        project.status != "published"
        or project.deleted_at is not None
        or project.published_at is None
        or project.current_revision_id is None
    ):
        return None
    revision = project.current_revision
    if revision is None:
        revision = db.get(ProjectRevision, project.current_revision_id)
    if revision is None:
        return None
    body = "\n\n".join(
        part for part in (revision.title, revision.summary, revision.content) if part
    )
    pipeline_version = pipeline_version_from(db)
    public_path = f"/projects/{revision.slug}"
    payload = {
        "source_type": SOURCE_PROJECT,
        "source_id": project.id,
        "source_version": str(revision.id),
        "title": revision.title,
        "summary": revision.summary,
        "content": revision.content,
        "public_path": public_path,
        "pipeline_version": pipeline_version,
    }
    return SourceDocument(
        source_type=SOURCE_PROJECT,
        source_id=project.id,
        source_version=str(revision.id),
        title=revision.title,
        public_path=public_path,
        body=body,
        content_hash=_hash_payload(payload),
        pipeline_version=pipeline_version,
    )


def project_book(db: Session, note: BookNote) -> SourceDocument | None:
    if (
        note.status != "published"
        or note.deleted_at is not None
        or note.published_at is None
        or note.current_revision_id is None
    ):
        return None
    revision = note.current_revision
    if revision is None:
        revision = db.get(BookNoteRevision, note.current_revision_id)
    if revision is None:
        return None
    body = "\n\n".join(
        part
        for part in (revision.book_title, revision.author, revision.summary, revision.content)
        if part
    )
    pipeline_version = pipeline_version_from(db)
    public_path = (
        f"/books/{revision.first_published_at.year:04d}/"
        f"{revision.first_published_at.month:02d}/{revision.slug}"
    )
    payload = {
        "source_type": SOURCE_BOOK,
        "source_id": note.id,
        "source_version": str(revision.id),
        "title": revision.book_title,
        "author": revision.author,
        "summary": revision.summary,
        "content": revision.content,
        "public_path": public_path,
        "pipeline_version": pipeline_version,
    }
    return SourceDocument(
        source_type=SOURCE_BOOK,
        source_id=note.id,
        source_version=str(revision.id),
        title=revision.book_title,
        public_path=public_path,
        body=body,
        content_hash=_hash_payload(payload),
        pipeline_version=pipeline_version,
    )


def project_profile(db: Session, profile: Profile | None = None) -> SourceDocument:
    row = profile if profile is not None else db.get(Profile, PROFILE_SINGLETON_ID)
    if row is None:
        row = default_profile()
    public = public_payload(row)
    lines = [public.name, public.title, public.bio]
    if public.skills:
        lines.append(" ".join(public.skills))
    for value in (
        public.city,
        public.email,
        public.github_url,
        public.website_url,
        public.resume_url,
    ):
        if value:
            lines.append(value)
    body = "\n\n".join(part for part in lines if part)
    pipeline_version = pipeline_version_from(db)
    payload = {
        "source_type": SOURCE_PROFILE,
        "source_id": PROFILE_SINGLETON_ID,
        "source_version": str(row.version),
        "public": public.model_dump(),
        "pipeline_version": pipeline_version,
    }
    return SourceDocument(
        source_type=SOURCE_PROFILE,
        source_id=PROFILE_SINGLETON_ID,
        source_version=str(row.version),
        title=public.name,
        public_path="/",
        body=body,
        content_hash=_hash_payload(payload),
        pipeline_version=pipeline_version,
    )


def project_about(db: Session, page: AboutPage | None = None) -> SourceDocument | None:
    from ..about_page_service import ABOUT_PAGE_SINGLETON_ID, parse_content

    row = page if page is not None else db.get(AboutPage, ABOUT_PAGE_SINGLETON_ID)
    if row is None or row.status != "published" or row.current_revision_id is None:
        return None
    revision = db.get(AboutPageRevision, row.current_revision_id)
    if (
        revision is None
        or revision.about_page_id != row.id
        or not revision.assistant_eligible
    ):
        return None
    content = parse_content(revision.content_json)
    lines = ["# 关于 Gavin", content.statement, "## 能力自述"]
    for capability in content.capabilities:
        lines.extend([
            f"### {capability.title}", capability.description, "、".join(capability.tags),
        ])
    lines.append("## 当前方向")
    statuses = {"in_progress": "进行中", "building": "构建中", "exploring": "探索中"}
    lines.extend(
        f"{item.label}（{statuses.get(item.status, item.status)}）" for item in content.now
    )
    lines.extend(["## 写作主题", "、".join(content.editorial_topics), "## 关于本站"])
    lines.append(content.site.description)
    lines.extend(f"{item.label}：{item.value}" for item in content.site.stack)
    body = "\n\n".join(line for line in lines if line)
    pipeline_version = pipeline_version_from(db)
    version = str(revision.id)
    return SourceDocument(
        source_type=SOURCE_ABOUT,
        source_id=row.id,
        source_version=version,
        title="关于 Gavin",
        public_path="/about",
        body=body,
        content_hash=_hash_payload({
            "source_type": SOURCE_ABOUT, "source_id": row.id,
            "source_version": version, "body": body, "pipeline_version": pipeline_version,
        }),
        pipeline_version=pipeline_version,
    )


def project_resume(db: Session) -> SourceDocument | None:
    from ..assistant_resume.storage import current_version
    from ..models import AssistantResumeSource

    row = db.get(AssistantResumeSource, 1, populate_existing=True)
    if row is None or not row.url or not row.enabled:
        return None
    version = current_version(db, row)
    if version is None:
        return None
    pipeline = pipeline_version_from(db)
    return SourceDocument(
        source_type="resume", source_id=1, source_version=version.id,
        title="Gavin 简历", public_path=f"/api/v1/assistant/resume/{version.id}",
        body=version.body,
        content_hash=_hash_payload({"body": version.body, "version": version.id,
                                   "parser": version.parser_version, "pipeline": pipeline}),
        pipeline_version=pipeline,
    )


def project_source(db: Session, source_type: str, source_id: int) -> SourceDocument | None:
    if source_type == "resume":
        return project_resume(db) if source_id == 1 else None
    if source_type == SOURCE_ABOUT:
        page = db.get(AboutPage, source_id)
        return project_about(db, page) if page is not None else None
    if source_type == SOURCE_ARTICLE:
        article = db.get(Article, source_id)
        return project_article(db, article) if article is not None else None
    if source_type == SOURCE_PROJECT:
        project = db.get(Project, source_id)
        return project_project(db, project) if project is not None else None
    if source_type == SOURCE_BOOK:
        note = db.get(BookNote, source_id)
        return project_book(db, note) if note is not None else None
    if source_type == SOURCE_PROFILE:
        return project_profile(db)
    return None


def iter_public_sources(db: Session) -> list[SourceDocument]:
    documents: list[SourceDocument] = []
    articles = db.scalars(
        select(Article)
        .options(
            selectinload(Article.current_revision).selectinload(ArticleRevision.tags),
        )
        .where(
            Article.status == "published",
            Article.deleted_at.is_(None),
            Article.current_revision_id.is_not(None),
        )
        .order_by(Article.id)
    ).unique().all()
    for article in articles:
        document = project_article(db, article)
        if document is not None:
            documents.append(document)
    projects = db.scalars(
        select(Project)
        .options(selectinload(Project.current_revision))
        .where(
            Project.status == "published",
            Project.deleted_at.is_(None),
            Project.current_revision_id.is_not(None),
        )
        .order_by(Project.id)
    ).unique().all()
    for project in projects:
        document = project_project(db, project)
        if document is not None:
            documents.append(document)
    notes = db.scalars(
        select(BookNote)
        .options(selectinload(BookNote.current_revision))
        .where(
            BookNote.status == "published",
            BookNote.deleted_at.is_(None),
            BookNote.current_revision_id.is_not(None),
        )
        .order_by(BookNote.id)
    ).unique().all()
    for note in notes:
        document = project_book(db, note)
        if document is not None:
            documents.append(document)
    documents.append(project_profile(db))
    about = project_about(db)
    if about is not None:
        documents.append(about)
    resume = project_resume(db)
    if resume is not None:
        documents.append(resume)
    return documents


def source_revision_set_digest(documents: list[SourceDocument]) -> str:
    payload = [
        [document.source_type, document.source_id, document.source_version, document.content_hash]
        for document in documents
    ]
    payload.sort()
    return _hash_payload({"sources": payload})
