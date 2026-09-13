from __future__ import annotations

import difflib

from sqlalchemy import select
from sqlalchemy.orm import Session

from .article_revisions import (
    create_publish_revision,
    has_unpublished_changes,
    refresh_revision_content_hash,
)
from .assistant_index.outbox import enqueue_for_content
from .knowledge_links import rebuild_content_links, sync_working_references_from_revision
from .models import (
    Article,
    ArticleRevision,
    ArticleRevisionPublicReference,
    Category,
    Tag,
)
from .search import sync_search_document
from .time_utils import utc_now

ARTICLE_VERSION_CONFLICT = "ARTICLE_VERSION_CONFLICT"
ARTICLE_WORKING_COPY_DIRTY = "ARTICLE_WORKING_COPY_DIRTY"
PUBLISH_NOT_ELIGIBLE = "PUBLISH_NOT_ELIGIBLE"


class ArticleRevisionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def list_article_revisions(
    db: Session,
    article_id: int,
    *,
    limit: int = 20,
    offset: int = 0,
) -> list[ArticleRevision]:
    return list(
        db.scalars(
            select(ArticleRevision)
            .where(ArticleRevision.article_id == article_id)
            .order_by(ArticleRevision.revision_number.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )


def get_revision_or_404(
    db: Session,
    article_id: int,
    revision_id: int,
) -> ArticleRevision:
    revision = db.get(ArticleRevision, revision_id)
    if revision is None or revision.article_id != article_id:
        raise ArticleRevisionError("REVISION_NOT_FOUND", "文章修订不存在")
    return revision


def revision_diff(
    db: Session,
    article_id: int,
    *,
    from_revision_id: int,
    to_revision_id: int,
) -> dict:
    from_revision = get_revision_or_404(db, article_id, from_revision_id)
    to_revision = get_revision_or_404(db, article_id, to_revision_id)
    return {
        "article_id": article_id,
        "from_revision_id": from_revision.id,
        "to_revision_id": to_revision.id,
        "title": _diff(from_revision.title, to_revision.title),
        "summary": _diff(from_revision.summary, to_revision.summary),
        "content": _diff(from_revision.content, to_revision.content),
        "category": _diff(
            from_revision.category_name,
            to_revision.category_name,
        ),
        "tags": _diff(
            ", ".join(tag.name for tag in from_revision.tags),
            ", ".join(tag.name for tag in to_revision.tags),
        ),
        "references": _diff(
            _reference_lines(from_revision),
            _reference_lines(to_revision),
        ),
    }


def rollback_article(
    db: Session,
    *,
    article: Article,
    revision: ArticleRevision,
    version: int,
    current_revision_id: int,
    rollback_confirmed: bool,
) -> ArticleRevision:
    if not rollback_confirmed:
        raise ArticleRevisionError(PUBLISH_NOT_ELIGIBLE, "必须显式确认回滚")
    if article.version != version or article.current_revision_id != current_revision_id:
        raise ArticleRevisionError(ARTICLE_VERSION_CONFLICT, "文章版本已变化，请刷新后重试")
    if article.status != "published":
        raise ArticleRevisionError("INVALID_STATE", "只有已发布文章可以回滚")
    if has_unpublished_changes(article):
        raise ArticleRevisionError(
            ARTICLE_WORKING_COPY_DIRTY,
            "目标文章存在未发布的人工修改，不能覆盖",
        )
    if revision.slug != article.slug:
        raise ArticleRevisionError("SLUG_CHANGED", "历史修订 slug 与当前文章不一致，禁止回滚")
    if revision.category_id is not None:
        category = db.get(Category, revision.category_id)
        if category is None:
            raise ArticleRevisionError(
                "CATEGORY_DELETED",
                "历史修订栏目实体已删除，禁止回滚",
            )
    article.title = revision.title
    article.slug = revision.slug
    article.summary = revision.summary
    article.content = revision.content
    article.category_id = revision.category_id
    article.category = db.get(Category, revision.category_id) if revision.category_id else None
    tag_ids = [tag.tag_id for tag in revision.tags]
    article.tags = list(db.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all()) if tag_ids else []
    article.version += 1
    article.updated_at = utc_now()
    new_revision = create_publish_revision(
        db,
        article,
        source="rollback",
    )
    new_revision.rollback_from_revision_id = revision.id
    _copy_public_references(db, new_revision, revision)
    db.flush()
    db.refresh(new_revision)
    sync_working_references_from_revision(db, article, new_revision.public_references)
    refresh_revision_content_hash(db, article, new_revision)
    rebuild_content_links(db, article)
    sync_search_document(db, article)
    enqueue_for_content(db, article)
    return new_revision


def _copy_public_references(
    db: Session,
    new_revision: ArticleRevision,
    previous_revision: ArticleRevision | None,
) -> None:
    if previous_revision is None:
        return
    for entry in previous_revision.public_references:
        db.add(
            ArticleRevisionPublicReference(
                revision_id=new_revision.id,
                position=entry.position,
                display_title=entry.display_title,
                url=entry.url,
                enabled=entry.enabled,
            )
        )


def _reference_lines(revision: ArticleRevision) -> str:
    return "\n".join(
        f"{entry.display_title} {entry.url}"
        for entry in revision.public_references
        if entry.enabled
    )


def _diff(before: str, after: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )
