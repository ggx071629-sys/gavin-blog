from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from .models import (
    Article,
    ArticleRevisionPublicReference,
    ArticleWorkingReference,
    BookNote,
    ContentLink,
    Project,
)
from .schemas import ArticleReference, ArticleReferenceInput, PublicBacklink
from .schemas import WikiResolution as WikiResolutionSchema

ContentKind = Literal["article", "project", "book"]
MAX_BACKLINKS = 20
MAX_WORKING_REFERENCES = 20
WIKILINK_RE = re.compile(r"\[\[([^\[\]]+?)\]\]")
FENCE_RE = re.compile(r"(?ms)^[ \t]*(```+|~~~+)[^\n]*\n.*?^[ \t]*\1[ \t]*$")
INLINE_CODE_RE = re.compile(r"`+[^`\n]+`+")
TYPE_ALIASES: dict[str, ContentKind] = {
    "article": "article",
    "notes": "article",
    "note": "article",
    "project": "project",
    "projects": "project",
    "book": "book",
    "books": "book",
}
ARTICLE_PATH_RE = re.compile(r"^/notes/(\d{4})/(\d{2})/([a-z0-9-]+)/?$")
PROJECT_PATH_RE = re.compile(r"^/projects/([a-z0-9-]+)/?$")
BOOK_PATH_RE = re.compile(r"^/books/(\d{4})/(\d{2})/([a-z0-9-]+)/?$")


@dataclass(frozen=True)
class WikiLink:
    token: str
    display: str


@dataclass(frozen=True)
class ResolvedTarget:
    content_type: ContentKind
    id: int
    title: str
    summary: str
    slug: str
    public_path: str
    published_at: object


@dataclass(frozen=True)
class WikiResolution:
    token: str
    display_title: str
    public_path: str | None
    content_type: ContentKind | None


def mask_code_regions(content: str) -> str:
    def blank(match: re.Match[str]) -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    masked = FENCE_RE.sub(blank, content or "")
    return INLINE_CODE_RE.sub(blank, masked)


def iter_wikilinks(content: str) -> list[WikiLink]:
    links: list[WikiLink] = []
    for match in WIKILINK_RE.finditer(mask_code_regions(content)):
        raw = match.group(1).strip()
        if not raw:
            continue
        if "|" in raw:
            token, display = raw.split("|", 1)
        else:
            token, display = raw, raw
        token = token.strip()
        display = display.strip()
        if token:
            links.append(WikiLink(token=token, display=display or token))
    return links


def article_public_path(article: Article) -> str | None:
    published_at = article.published_at
    slug = article.slug
    if article.current_revision is not None:
        slug = article.current_revision.slug
        published_at = article.current_revision.first_published_at
    if published_at is None:
        return None
    return f"/notes/{published_at.year:04d}/{published_at.month:02d}/{slug}"


def project_public_path(project: Project) -> str | None:
    slug = project.current_revision.slug if project.current_revision is not None else project.slug
    if project.status != "published" or project.deleted_at is not None:
        return None
    return f"/projects/{slug}"


def book_public_path(note: BookNote) -> str | None:
    published_at = note.published_at
    slug = note.slug
    if note.current_revision is not None:
        slug = note.current_revision.slug
        published_at = note.current_revision.first_published_at
    if published_at is None:
        return None
    return f"/books/{published_at.year:04d}/{published_at.month:02d}/{slug}"


def _is_published(item: Article | Project | BookNote) -> bool:
    return (
        item.status == "published"
        and item.deleted_at is None
        and item.current_revision_id is not None
    )


def _article_target(article: Article) -> ResolvedTarget | None:
    if not _is_published(article):
        return None
    path = article_public_path(article)
    revision = article.current_revision
    if path is None or revision is None or article.published_at is None:
        return None
    return ResolvedTarget(
        content_type="article",
        id=article.id,
        title=revision.title,
        summary=revision.summary,
        slug=revision.slug,
        public_path=path,
        published_at=article.published_at,
    )


def _project_target(project: Project) -> ResolvedTarget | None:
    if not _is_published(project):
        return None
    path = project_public_path(project)
    revision = project.current_revision
    if path is None or revision is None or project.published_at is None:
        return None
    return ResolvedTarget(
        content_type="project",
        id=project.id,
        title=revision.title,
        summary=revision.summary,
        slug=revision.slug,
        public_path=path,
        published_at=project.published_at,
    )


def _book_target(note: BookNote) -> ResolvedTarget | None:
    if not _is_published(note):
        return None
    path = book_public_path(note)
    revision = note.current_revision
    if path is None or revision is None or note.published_at is None:
        return None
    return ResolvedTarget(
        content_type="book",
        id=note.id,
        title=revision.book_title,
        summary=revision.summary,
        slug=revision.slug,
        public_path=path,
        published_at=note.published_at,
    )


def _with_revision(model, *filters):
    return select(model).options(selectinload(model.current_revision)).where(*filters)


def published_target(
    db: Session,
    content_type: ContentKind,
    content_id: int,
) -> ResolvedTarget | None:
    if content_type == "article":
        article = db.scalar(_with_revision(Article, Article.id == content_id))
        return _article_target(article) if article is not None else None
    if content_type == "project":
        project = db.scalar(_with_revision(Project, Project.id == content_id))
        return _project_target(project) if project is not None else None
    note = db.scalar(_with_revision(BookNote, BookNote.id == content_id))
    return _book_target(note) if note is not None else None


def _path_from_token(token: str) -> str | None:
    value = token.strip()
    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        value = parsed.path or ""
    if not value.startswith("/"):
        return None
    return value.rstrip("/") or "/"


def resolve_token(db: Session, token: str) -> ResolvedTarget | None:
    path = _path_from_token(token)
    if path is not None:
        return resolve_public_path(db, path)

    kind: ContentKind | None = None
    slug = token
    if ":" in token:
        prefix, remainder = token.split(":", 1)
        mapped = TYPE_ALIASES.get(prefix.strip().lower())
        if mapped is None or not remainder.strip():
            return None
        kind = mapped
        slug = remainder.strip()

    matches: list[ResolvedTarget] = []
    if kind in {None, "article"}:
        article = db.scalar(_with_revision(Article, Article.slug == slug))
        target = _article_target(article) if article is not None else None
        if target is not None:
            matches.append(target)
    if kind in {None, "project"}:
        project = db.scalar(_with_revision(Project, Project.slug == slug))
        target = _project_target(project) if project is not None else None
        if target is not None:
            matches.append(target)
    if kind in {None, "book"}:
        note = db.scalar(_with_revision(BookNote, BookNote.slug == slug))
        target = _book_target(note) if note is not None else None
        if target is not None:
            matches.append(target)
    if len(matches) == 1:
        return matches[0]
    return None


def resolve_public_path(db: Session, path: str) -> ResolvedTarget | None:
    article_match = ARTICLE_PATH_RE.match(path)
    if article_match:
        year = int(article_match.group(1))
        month = int(article_match.group(2))
        slug = article_match.group(3)
        article = db.scalar(_with_revision(Article, Article.slug == slug))
        target = _article_target(article) if article is not None else None
        if (
            target is not None
            and article is not None
            and article.published_at is not None
            and article.published_at.year == year
            and article.published_at.month == month
        ):
            return target
        return None
    project_match = PROJECT_PATH_RE.match(path)
    if project_match:
        project = db.scalar(
            select(Project)
            .options(selectinload(Project.current_revision))
            .where(Project.slug == project_match.group(1))
        )
        return _project_target(project) if project is not None else None
    book_match = BOOK_PATH_RE.match(path)
    if book_match:
        year = int(book_match.group(1))
        month = int(book_match.group(2))
        slug = book_match.group(3)
        note = db.scalar(_with_revision(BookNote, BookNote.slug == slug))
        target = _book_target(note) if note is not None else None
        if (
            target is not None
            and note is not None
            and note.published_at is not None
            and note.published_at.year == year
            and note.published_at.month == month
        ):
            return target
        return None
    return None


def resolve_content_wikilinks(db: Session, content: str) -> list[WikiResolution]:
    seen: set[tuple[str, str]] = set()
    resolutions: list[WikiResolution] = []
    for link in iter_wikilinks(content):
        key = (link.token, link.display)
        if key in seen:
            continue
        seen.add(key)
        resolved = resolve_token(db, link.token)
        resolutions.append(
            WikiResolution(
                token=link.token,
                display_title=link.display,
                public_path=resolved.public_path if resolved else None,
                content_type=resolved.content_type if resolved else None,
            )
        )
    return resolutions


def working_reference_snapshots(db: Session, article: Article) -> list[dict[str, str]]:
    snapshots: list[dict[str, str]] = []
    for entry in sorted(article.working_references, key=lambda item: item.position):
        if entry.kind == "internal" and entry.target_type and entry.target_id:
            target = published_target(db, entry.target_type, entry.target_id)  # type: ignore[arg-type]
            url = (
                target.public_path
                if target is not None
                else f"{entry.target_type}:{entry.target_id}"
            )
        else:
            url = entry.url or ""
        snapshots.append({"display_title": entry.display_title, "url": url})
    return snapshots


def revision_reference_snapshots(
    revision_references: Iterable[ArticleRevisionPublicReference],
) -> list[dict[str, str]]:
    return [
        {"display_title": entry.display_title, "url": entry.url}
        for entry in sorted(revision_references, key=lambda item: item.position)
        if entry.enabled
    ]


def snapshot_working_references(db: Session, article: Article, revision_id: int) -> None:
    db.execute(
        delete(ArticleRevisionPublicReference).where(
            ArticleRevisionPublicReference.revision_id == revision_id
        )
    )
    for position, snapshot in enumerate(working_reference_snapshots(db, article)):
        db.add(
            ArticleRevisionPublicReference(
                revision_id=revision_id,
                position=position,
                display_title=snapshot["display_title"],
                url=snapshot["url"],
                enabled=True,
            )
        )
    db.flush()


def sync_working_references_from_revision(
    db: Session,
    article: Article,
    references: Iterable[ArticleRevisionPublicReference],
) -> None:
    article.working_references.clear()
    db.flush()
    for position, entry in enumerate(sorted(references, key=lambda item: item.position)):
        if not entry.enabled:
            continue
        target = resolve_public_path(db, _path_from_token(entry.url) or entry.url)
        if target is not None:
            article.working_references.append(
                ArticleWorkingReference(
                    position=position,
                    kind="internal",
                    display_title=entry.display_title,
                    url=None,
                    target_type=target.content_type,
                    target_id=target.id,
                )
            )
        else:
            article.working_references.append(
                ArticleWorkingReference(
                    position=position,
                    kind="external",
                    display_title=entry.display_title,
                    url=entry.url,
                    target_type=None,
                    target_id=None,
                )
            )


def _source_identity(
    source: Article | Project | BookNote,
) -> tuple[ContentKind, int, int | None, str, list[str]]:
    revision = source.current_revision
    content = revision.content if revision is not None else ""
    if isinstance(source, Article):
        article_revision = source.current_revision
        urls = [
            entry.url
            for entry in (
                article_revision.public_references if article_revision is not None else []
            )
            if entry.enabled
        ]
        return "article", source.id, source.current_revision_id, content, urls
    if isinstance(source, Project):
        return "project", source.id, source.current_revision_id, content, []
    return "book", source.id, source.current_revision_id, content, []


def rebuild_content_links(db: Session, source: Article | Project | BookNote) -> None:
    source_type, source_id, revision_id, content, reference_urls = _source_identity(source)
    db.execute(
        delete(ContentLink).where(
            ContentLink.source_type == source_type,
            ContentLink.source_id == source_id,
        )
    )
    if not _is_published(source):
        return
    from_references: set[tuple[str, int]] = set()
    targets: dict[tuple[str, int], ResolvedTarget] = {}
    for link in iter_wikilinks(content):
        resolved = resolve_token(db, link.token)
        if resolved is None or (resolved.content_type == source_type and resolved.id == source_id):
            continue
        targets[(resolved.content_type, resolved.id)] = resolved
    for url in reference_urls:
        path = _path_from_token(url) or url
        resolved = resolve_public_path(db, path) if path.startswith("/") else None
        if resolved is None or (resolved.content_type == source_type and resolved.id == source_id):
            continue
        key = (resolved.content_type, resolved.id)
        targets[key] = resolved
        from_references.add(key)
    for link_key, resolved in targets.items():
        db.add(
            ContentLink(
                source_type=source_type,
                source_id=source_id,
                source_revision_id=revision_id,
                target_type=resolved.content_type,
                target_id=resolved.id,
                kind="reference" if link_key in from_references else "wikilink",
            )
        )


def clear_content_links(db: Session, source: Article | Project | BookNote) -> None:
    source_type, source_id, _, _, _ = _source_identity(source)
    db.execute(
        delete(ContentLink).where(
            ContentLink.source_type == source_type,
            ContentLink.source_id == source_id,
        )
    )


def replace_working_references(
    db: Session,
    article: Article,
    items: list[ArticleReferenceInput],
) -> None:
    if len(items) > MAX_WORKING_REFERENCES:
        raise HTTPException(status_code=422, detail="at most 20 references are allowed")
    article.working_references.clear()
    db.flush()
    for position, item in enumerate(items):
        if item.kind == "external":
            if not item.url:
                raise HTTPException(status_code=422, detail="external reference url is required")
            db.add(
                ArticleWorkingReference(
                    article_id=article.id,
                    position=position,
                    kind="external",
                    display_title=item.display_title,
                    url=item.url,
                    target_type=None,
                    target_id=None,
                )
            )
            continue
        if item.target_type is None or item.target_id is None:
            raise HTTPException(status_code=422, detail="internal reference target is required")
        target = published_target(db, item.target_type, item.target_id)
        if target is None:
            raise HTTPException(
                status_code=422,
                detail="internal reference target is not published",
            )
        if target.content_type == "article" and target.id == article.id:
            raise HTTPException(status_code=422, detail="article cannot reference itself")
        db.add(
            ArticleWorkingReference(
                article_id=article.id,
                position=position,
                kind="internal",
                display_title=item.display_title,
                url=None,
                target_type=item.target_type,
                target_id=item.target_id,
            )
        )


def serialize_working_references(article: Article) -> list[ArticleReference]:
    return [
        ArticleReference(
            kind=entry.kind,
            display_title=entry.display_title,
            url=entry.url,
            target_type=entry.target_type,
            target_id=entry.target_id,
        )
        for entry in article.working_references
    ]


def serialize_wikilinks(db: Session, content: str) -> list[WikiResolutionSchema]:
    return [
        WikiResolutionSchema(
            token=item.token,
            display_title=item.display_title,
            public_path=item.public_path,
            content_type=item.content_type,
        )
        for item in resolve_content_wikilinks(db, content)
    ]


def serialize_backlinks(
    db: Session,
    target_type: ContentKind,
    target_id: int,
) -> list[PublicBacklink]:
    return [
        PublicBacklink(
            content_type=item.content_type,
            id=item.id,
            title=item.title,
            summary=item.summary,
            published_at=item.published_at,
            public_path=item.public_path,
        )
        for item in list_backlinks(db, target_type, target_id)
    ]


def list_backlinks(db: Session, target_type: ContentKind, target_id: int) -> list[ResolvedTarget]:
    rows = list(
        db.scalars(
            select(ContentLink).where(
                ContentLink.target_type == target_type,
                ContentLink.target_id == target_id,
            )
        ).all()
    )
    cards: list[ResolvedTarget] = []
    seen: set[tuple[str, int]] = set()
    for row in rows:
        key = (row.source_type, row.source_id)
        if key in seen:
            continue
        seen.add(key)
        card = published_target(db, row.source_type, row.source_id)  # type: ignore[arg-type]
        if card is not None:
            cards.append(card)
    cards.sort(key=lambda item: (item.published_at, item.id), reverse=True)
    return cards[:MAX_BACKLINKS]
