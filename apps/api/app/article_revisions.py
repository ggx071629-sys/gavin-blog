from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .knowledge_links import revision_reference_snapshots, working_reference_snapshots
from .models import Article, ArticleRevision, ArticleRevisionTag, Tag
from .time_utils import utc_now


def canonical_article_sha256(
    *,
    title: str,
    slug: str,
    summary: str,
    content: str,
    category_id: int | None,
    tags: list[Tag],
    references: list[dict[str, str]] | None = None,
) -> str:
    """Deterministic canonical hash over the publish snapshot, tags ordered."""
    ordered_tags = sorted(tags, key=lambda tag: (tag.name, tag.id))
    payload = {
        "title": title,
        "slug": slug,
        "summary": summary,
        "content": content,
        "category_id": category_id,
        "tags": [[tag.id, tag.name, tag.slug] for tag in ordered_tags],
        "references": references or [],
    }
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def current_revision_content_hash(article: Article) -> str:
    from sqlalchemy.orm import object_session

    session = object_session(article)
    references = working_reference_snapshots(session, article) if session is not None else []
    return canonical_article_sha256(
        title=article.title,
        slug=article.slug,
        summary=article.summary,
        content=article.content,
        category_id=article.category_id,
        tags=article.tags,
        references=references,
    )


def create_publish_revision(
    db: Session,
    article: Article,
    *,
    source: str = "editor",
    published_at: datetime | None = None,
    first_published_at: datetime | None = None,
) -> ArticleRevision:
    """Create the next immutable publish revision and point the article at it.

    Callers must commit the surrounding transaction. The article must already
    have its category and tags loaded/attached.
    """
    now = published_at or utc_now()
    if article.published_at is None:
        article.published_at = now
    first = first_published_at or article.published_at
    latest = db.scalar(
        select(ArticleRevision.revision_number)
        .where(ArticleRevision.article_id == article.id)
        .order_by(ArticleRevision.revision_number.desc())
        .limit(1)
    )
    revision_number = (latest or 0) + 1
    category = article.category
    tags = sorted(article.tags, key=lambda tag: (tag.name, tag.id))
    revision = ArticleRevision(
        article_id=article.id,
        revision_number=revision_number,
        title=article.title,
        slug=article.slug,
        summary=article.summary,
        content=article.content,
        first_published_at=first,
        published_at=now,
        category_id=article.category_id,
        category_name=category.name if category else "",
        category_slug=category.slug if category else "",
        source=source,
        content_sha256=canonical_article_sha256(
            title=article.title,
            slug=article.slug,
            summary=article.summary,
            content=article.content,
            category_id=article.category_id,
            tags=tags,
            references=working_reference_snapshots(db, article),
        ),
    )
    db.add(revision)
    db.flush()
    for position, tag in enumerate(tags):
        db.add(
            ArticleRevisionTag(
                revision_id=revision.id,
                tag_id=tag.id,
                name=tag.name,
                slug=tag.slug,
                position=position,
            )
        )
    article.current_revision_id = revision.id
    # The viewonly relationship caches the previous revision; force a reload so
    # public projections and the search sync never read a stale snapshot.
    db.expire(article, ["current_revision"])
    return revision


def refresh_revision_content_hash(db: Session, article: Article, revision: ArticleRevision) -> None:
    # Public refs are often added via db.add() in this session; expire so the
    # hash reads the revision snapshot instead of a stale empty collection.
    db.flush()
    db.expire(revision, ["public_references"])
    revision.content_sha256 = canonical_article_sha256(
        title=revision.title,
        slug=revision.slug,
        summary=revision.summary,
        content=revision.content,
        category_id=article.category_id,
        tags=list(article.tags),
        references=revision_reference_snapshots(revision.public_references),
    )


def has_unpublished_changes(article: Article) -> bool:
    """True when the working copy differs from the current publish revision."""
    revision = article.current_revision
    if revision is None:
        return article.status == "published"
    return current_revision_content_hash(article) != revision.content_sha256
