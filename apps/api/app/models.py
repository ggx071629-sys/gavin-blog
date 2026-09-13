from __future__ import annotations

from datetime import date, datetime
from secrets import token_urlsafe

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .time_utils import UTCDateTime, utc_now

article_tags = Table(
    "article_tags",
    Base.metadata,
    Column("article_id", ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="RESTRICT"), primary_key=True),
)

project_articles = Table(
    "project_articles",
    Base.metadata,
    Column("project_id", ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("article_id", ForeignKey("articles.id", ondelete="RESTRICT"), primary_key=True),
)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(240), default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now)

    articles: Mapped[list[Article]] = relationship(back_populates="category")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(240), default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now)

    articles: Mapped[list[Article]] = relationship(
        secondary=article_tags,
        back_populates="tags",
    )


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(180))
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    summary: Mapped[str] = mapped_column(String(320), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True, index=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    # Pointer to the immutable, monotonically numbered publish revision that
    # public reads, RSS/sitemap, and the public search index resolve against.
    current_revision_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    category: Mapped[Category | None] = relationship(back_populates="articles")
    tags: Mapped[list[Tag]] = relationship(
        secondary=article_tags,
        back_populates="articles",
        order_by="Tag.name",
    )
    projects: Mapped[list[Project]] = relationship(
        secondary=project_articles,
        back_populates="articles",
    )
    revisions: Mapped[list[ArticleRevision]] = relationship(
        back_populates="article",
        order_by="ArticleRevision.revision_number",
        passive_deletes=True,
    )
    current_revision: Mapped[ArticleRevision | None] = relationship(
        primaryjoin="foreign(Article.current_revision_id) == ArticleRevision.id",
        viewonly=True,
        uselist=False,
    )
    working_references: Mapped[list[ArticleWorkingReference]] = relationship(
        back_populates="article",
        order_by="ArticleWorkingReference.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ArticleRevision(Base):
    """Immutable publish snapshot for one article release.

    A new row is created for every explicit publish; autosaves never touch this
    table. `articles.version` continues to be the working-copy optimistic lock.
    """

    __tablename__ = "article_revisions"
    __table_args__ = (
        UniqueConstraint("article_id", "revision_number"),
        CheckConstraint(
            "source IN ('editor', 'incubator', 'rollback')",
            name="ck_article_revisions_source",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="RESTRICT"),
        index=True,
    )
    revision_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(180))
    slug: Mapped[str] = mapped_column(String(160))
    summary: Mapped[str] = mapped_column(String(320), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    first_published_at: Mapped[datetime] = mapped_column(UTCDateTime())
    published_at: Mapped[datetime] = mapped_column(UTCDateTime())
    category_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category_name: Mapped[str] = mapped_column(String(80), default="")
    category_slug: Mapped[str] = mapped_column(String(80), default="")
    source: Mapped[str] = mapped_column(String(16), default="editor")
    content_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    # For rollback revisions only: the historical revision this snapshot copies.
    rollback_from_revision_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    article: Mapped[Article] = relationship(back_populates="revisions")
    tags: Mapped[list[ArticleRevisionTag]] = relationship(
        back_populates="revision",
        order_by="ArticleRevisionTag.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    public_references: Mapped[list[ArticleRevisionPublicReference]] = relationship(
        back_populates="revision",
        order_by="ArticleRevisionPublicReference.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ArticleRevisionTag(Base):
    """Ordered category/tag snapshot resolved at publish time."""

    __tablename__ = "article_revision_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    revision_id: Mapped[int] = mapped_column(
        ForeignKey("article_revisions.id", ondelete="CASCADE"),
        index=True,
    )
    tag_id: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(80))
    position: Mapped[int] = mapped_column(Integer, default=0)

    revision: Mapped[ArticleRevision] = relationship(back_populates="tags")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(180))
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    summary: Mapped[str] = mapped_column(String(320), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    repository_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True, index=True)
    current_revision_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    articles: Mapped[list[Article]] = relationship(
        secondary=project_articles,
        back_populates="projects",
        order_by="Article.updated_at.desc()",
    )
    revisions: Mapped[list[ProjectRevision]] = relationship(
        back_populates="project",
        order_by="ProjectRevision.revision_number",
        passive_deletes=True,
    )
    current_revision: Mapped[ProjectRevision | None] = relationship(
        primaryjoin="foreign(Project.current_revision_id) == ProjectRevision.id",
        viewonly=True,
        uselist=False,
    )


class BookNote(Base):
    __tablename__ = "book_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_title: Mapped[str] = mapped_column(String(180))
    author: Mapped[str] = mapped_column(String(180))
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reading_status: Mapped[str] = mapped_column(String(16), default="planned", index=True)
    reading_date: Mapped[date | None] = mapped_column(nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str] = mapped_column(String(320), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True, index=True)
    current_revision_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    revisions: Mapped[list[BookNoteRevision]] = relationship(
        back_populates="note",
        order_by="BookNoteRevision.revision_number",
        passive_deletes=True,
    )
    current_revision: Mapped[BookNoteRevision | None] = relationship(
        primaryjoin="foreign(BookNote.current_revision_id) == BookNoteRevision.id",
        viewonly=True,
        uselist=False,
    )


class ProjectRevision(Base):
    """Immutable snapshot created by an explicit project publish."""

    __tablename__ = "project_revisions"
    __table_args__ = (UniqueConstraint("project_id", "revision_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
    )
    revision_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(180))
    slug: Mapped[str] = mapped_column(String(160))
    summary: Mapped[str] = mapped_column(String(320), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    repository_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    first_published_at: Mapped[datetime] = mapped_column(UTCDateTime())
    published_at: Mapped[datetime] = mapped_column(UTCDateTime())
    content_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    project: Mapped[Project] = relationship(back_populates="revisions")
    article_links: Mapped[list[ProjectRevisionArticle]] = relationship(
        back_populates="revision",
        order_by="ProjectRevisionArticle.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ProjectRevisionArticle(Base):
    __tablename__ = "project_revision_articles"
    __table_args__ = (UniqueConstraint("revision_id", "article_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    revision_id: Mapped[int] = mapped_column(
        ForeignKey("project_revisions.id", ondelete="CASCADE"),
        index=True,
    )
    # Deliberately not an FK: permanent article deletion must not invalidate an
    # immutable project snapshot or block content cleanup.
    article_id: Mapped[int] = mapped_column(Integer, index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    revision: Mapped[ProjectRevision] = relationship(back_populates="article_links")


class BookNoteRevision(Base):
    """Immutable snapshot created by an explicit book-note publish."""

    __tablename__ = "book_note_revisions"
    __table_args__ = (UniqueConstraint("book_note_id", "revision_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_note_id: Mapped[int] = mapped_column(
        ForeignKey("book_notes.id", ondelete="CASCADE"),
        index=True,
    )
    revision_number: Mapped[int] = mapped_column(Integer)
    book_title: Mapped[str] = mapped_column(String(180))
    author: Mapped[str] = mapped_column(String(180))
    slug: Mapped[str] = mapped_column(String(160))
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reading_status: Mapped[str] = mapped_column(String(16))
    reading_date: Mapped[date | None] = mapped_column(nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str] = mapped_column(String(320), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    first_published_at: Mapped[datetime] = mapped_column(UTCDateTime())
    published_at: Mapped[datetime] = mapped_column(UTCDateTime())
    content_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    note: Mapped[BookNote] = relationship(back_populates="revisions")


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(16), index=True)
    original_name: Mapped[str] = mapped_column(String(255), default="")
    alt_text: Mapped[str] = mapped_column(String(240), default="")
    mime_type: Mapped[str] = mapped_column(String(100))
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    byte_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    url: Mapped[str] = mapped_column(String(1000))
    storage_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    content_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    variants_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True, index=True)


class AccountChallenge(Base):
    __tablename__ = "account_challenges"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    purpose: Mapped[str] = mapped_column(String(16), index=True)
    credential_version: Mapped[int] = mapped_column(Integer)
    digest: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(16), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())


class AccountAttempt(Base):
    __tablename__ = "account_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), index=True)
    ip_hash: Mapped[str] = mapped_column(String(64))
    purpose: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, index=True)


class AdminCredential(Base):
    __tablename__ = "admin_credentials"
    __table_args__ = (CheckConstraint("id = 1"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    version: Mapped[int] = mapped_column(Integer, default=1)


class AdminSession(Base):
    __tablename__ = "admin_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    public_id: Mapped[str] = mapped_column(String(64), unique=True, default=token_urlsafe)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class Profile(Base):
    """Site-wide singleton personal profile shown on the homepage."""

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), default="Gavin")
    title: Mapped[str] = mapped_column(String(120), default="")
    bio: Mapped[str] = mapped_column(String(240), default="")
    skills_json: Mapped[str] = mapped_column(Text, default="[]")
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    city_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    github_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    email_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    resume_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now)


class AboutPage(Base):
    """Singleton working copy of the public About page content.

    Autosaves mutate only this row; explicit publish appends an immutable
    ``AboutPageRevision`` and advances ``current_revision_id``. Public reads
    resolve the current publish revision, never this working copy.
    """

    __tablename__ = "about_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(16), default="published", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    # Pointer to the immutable AboutPageRevision that public reads resolve.
    current_revision_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now)

    revisions: Mapped[list[AboutPageRevision]] = relationship(
        back_populates="about_page",
        order_by="AboutPageRevision.revision_number",
        passive_deletes=True,
    )


class AboutPageRevision(Base):
    """Immutable publish snapshot for one About page release."""

    __tablename__ = "about_page_revisions"
    __table_args__ = (
        UniqueConstraint("about_page_id", "revision_number"),
        CheckConstraint(
            "source IN ('editor', 'rollback')",
            name="ck_about_page_revisions_source",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    about_page_id: Mapped[int] = mapped_column(
        ForeignKey("about_pages.id", ondelete="CASCADE"),
        index=True,
    )
    revision_number: Mapped[int] = mapped_column(Integer)
    content_json: Mapped[str] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(16), default="editor")
    assistant_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    first_published_at: Mapped[datetime] = mapped_column(UTCDateTime())
    published_at: Mapped[datetime] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    rollback_from_revision_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    about_page: Mapped[AboutPage] = relationship(back_populates="revisions")


class ArticleRevisionPublicReference(Base):
    """Public-facing reference snapshot attached to one article revision."""

    __tablename__ = "article_revision_public_references"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    revision_id: Mapped[int] = mapped_column(
        ForeignKey("article_revisions.id", ondelete="CASCADE"),
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, default=0)
    display_title: Mapped[str] = mapped_column(String(180))
    url: Mapped[str] = mapped_column(String(1000))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    revision: Mapped[ArticleRevision] = relationship(back_populates="public_references")


class ArticleWorkingReference(Base):
    """Working-copy references that snapshot onto a publish revision."""

    __tablename__ = "article_working_references"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('external', 'internal')",
            name="ck_article_working_references_kind",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"),
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[str] = mapped_column(String(16), default="external")
    display_title: Mapped[str] = mapped_column(String(180))
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    target_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    article: Mapped[Article] = relationship(back_populates="working_references")


class ContentLink(Base):
    """Published outbound knowledge link from one public object to another."""

    __tablename__ = "content_links"
    __table_args__ = (
        UniqueConstraint("source_type", "source_id", "target_type", "target_id"),
        CheckConstraint(
            "source_type IN ('article', 'project', 'book')",
            name="ck_content_links_source_type",
        ),
        CheckConstraint(
            "target_type IN ('article', 'project', 'book')",
            name="ck_content_links_target_type",
        ),
        CheckConstraint(
            "kind IN ('wikilink', 'reference')",
            name="ck_content_links_kind",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(16), index=True)
    source_id: Mapped[int] = mapped_column(Integer, index=True)
    source_revision_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_type: Mapped[str] = mapped_column(String(16), index=True)
    target_id: Mapped[int] = mapped_column(Integer, index=True)
    kind: Mapped[str] = mapped_column(String(16), default="wikilink")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class AssistantIndexTask(Base):
    """Derived-index outbox. No content foreign keys so purge tombstones survive."""

    __tablename__ = "assistant_index_tasks"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('article', 'project', 'book', 'profile', 'about', 'resume')",
            name="ck_assistant_index_tasks_source_type",
        ),
        CheckConstraint(
            "operation IN ('upsert', 'delete', 'purge')",
            name="ck_assistant_index_tasks_operation",
        ),
        CheckConstraint(
            "status IN ('pending', 'leased', 'succeeded', 'failed')",
            name="ck_assistant_index_tasks_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(16), index=True)
    source_id: Mapped[int] = mapped_column(Integer, index=True)
    target_version: Mapped[str] = mapped_column(String(64))
    pipeline_version: Mapped[str] = mapped_column(String(64))
    operation: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    lease_owner: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    available_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, index=True)
    last_error_summary: Mapped[str | None] = mapped_column(String(240), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    version: Mapped[int] = mapped_column(Integer, default=1)
    safe_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    intent_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    parent_task_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operator_authorized: Mapped[int] = mapped_column(Integer, default=0)
    worker_fence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_state: Mapped[str | None] = mapped_column(String(16), nullable=True)


class AssistantIndexGeneration(Base):
    """Rebuildable index generation plus the manifest required to switch pointers."""

    __tablename__ = "assistant_index_generations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('staging', 'active', 'previous', 'failed', 'abandoned')",
            name="ck_assistant_index_generations_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    collection_name: Mapped[str] = mapped_column(String(80), unique=True)
    embedding_provider: Mapped[str] = mapped_column(String(80))
    embedding_model: Mapped[str] = mapped_column(String(160))
    embedding_model_version: Mapped[str] = mapped_column(String(80))
    vector_dimension: Mapped[int] = mapped_column(Integer)
    distance_metric: Mapped[str] = mapped_column(String(32))
    pipeline_version: Mapped[str] = mapped_column(String(64))
    source_revision_set_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vector_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outbox_high_water: Mapped[int | None] = mapped_column(Integer, nullable=True)
    built_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    manifest_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    chunks: Mapped[list[AssistantChunk]] = relationship(
        back_populates="generation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AssistantIndexPointer(Base):
    __tablename__ = "assistant_index_pointers"
    __table_args__ = (CheckConstraint("id = 1", name="ck_assistant_index_pointers_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    active_generation_id: Mapped[int | None] = mapped_column(
        ForeignKey("assistant_index_generations.id", ondelete="SET NULL"),
        nullable=True,
    )
    previous_generation_id: Mapped[int | None] = mapped_column(
        ForeignKey("assistant_index_generations.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class AssistantChunk(Base):
    """Canonical derived chunk stored in SQLite. Qdrant holds vectors only."""

    __tablename__ = "assistant_chunks"
    __table_args__ = (
        UniqueConstraint("generation_id", "chunk_id", name="uq_assistant_chunks_generation_chunk"),
        UniqueConstraint(
            "generation_id",
            "source_type",
            "source_id",
            "ordinal",
            name="uq_assistant_chunks_generation_source_ordinal",
        ),
        CheckConstraint(
            "source_type IN ('article', 'project', 'book', 'profile', 'about', 'resume')",
            name="ck_assistant_chunks_source_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chunk_id: Mapped[str] = mapped_column(String(64), index=True)
    source_type: Mapped[str] = mapped_column(String(16), index=True)
    source_id: Mapped[int] = mapped_column(Integer, index=True)
    source_version: Mapped[str] = mapped_column(String(64))
    generation_id: Mapped[int] = mapped_column(
        ForeignKey("assistant_index_generations.id", ondelete="CASCADE"),
        index=True,
    )
    pipeline_version: Mapped[str] = mapped_column(String(64))
    ordinal: Mapped[int] = mapped_column(Integer)
    heading_path: Mapped[str] = mapped_column(String(500), default="")
    content_hash: Mapped[str] = mapped_column(String(64))
    page_content: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(180))
    public_path: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)

    generation: Mapped[AssistantIndexGeneration] = relationship(back_populates="chunks")


class AssistantDailyMetric(Base):
    """Beijing-day aggregates copied from runtime. Never a billing source of truth."""

    __tablename__ = "assistant_daily_metrics"

    beijing_date: Mapped[str] = mapped_column(String(10), primary_key=True)
    chat_turns: Mapped[int] = mapped_column(Integer, default=0)
    chat_reserved_micro_cny: Mapped[int] = mapped_column(Integer, default=0)
    chat_settled_micro_cny: Mapped[int] = mapped_column(Integer, default=0)
    query_embedding_calls: Mapped[int] = mapped_column(Integer, default=0)
    query_embedding_micro_cny: Mapped[int] = mapped_column(Integer, default=0)
    index_embedding_calls: Mapped[int] = mapped_column(Integer, default=0)
    index_embedding_micro_cny: Mapped[int] = mapped_column(Integer, default=0)
    copied_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class AssistantBudgetPolicy(Base):
    __tablename__ = "assistant_budget_policy"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cap_micro_cny: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, default=1)
    blocked_beijing_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    runtime_accounted_date: Mapped[str | None] = mapped_column(String(10), nullable=True)


class AssistantBudgetReservation(Base):
    """Common content-owned authority. Contains no session or question body."""
    __tablename__ = "assistant_budget_reservations"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    beijing_date: Mapped[str] = mapped_column(String(10), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    scope: Mapped[str] = mapped_column(String(16))
    reserved_micro_cny: Mapped[int] = mapped_column(Integer, default=0)
    settled_micro_cny: Mapped[int] = mapped_column(Integer, default=0)
    terminal: Mapped[int] = mapped_column(Integer, default=0)


class AssistantIndexEmbeddingBudget(Base):
    """Index-worker daily embedding budget. Lives in the backed-up content database."""

    __tablename__ = "assistant_index_embedding_budgets"

    beijing_date: Mapped[str] = mapped_column(String(10), primary_key=True)
    reserved_micro_cny: Mapped[int] = mapped_column(Integer, default=0)
    settled_micro_cny: Mapped[int] = mapped_column(Integer, default=0)
    circuit_open: Mapped[int] = mapped_column(Integer, default=0)


class AssistantIndexEmbeddingAttempt(Base):
    """Worker-owned embedding attempts. No chunk body, vectors, raw responses, or sessions."""

    __tablename__ = "assistant_index_embedding_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('prepared', 'sending', 'succeeded', 'unknown', 'failed', 'deferred')",
            name="ck_assistant_index_embedding_attempts_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    generation_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    fencing_token: Mapped[str] = mapped_column(String(64))
    price_snapshot_json: Mapped[str] = mapped_column(Text)
    beijing_date: Mapped[str] = mapped_column(String(10), index=True)
    status: Mapped[str] = mapped_column(String(16), default="prepared", index=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_cost_micro_cny: Mapped[int] = mapped_column(Integer, default=0)
    settled_micro_cny: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class AssistantIndexWorkerState(Base):
    __tablename__ = "assistant_index_worker_state"
    __table_args__ = (CheckConstraint("id = 1", name="ck_assistant_index_worker_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    fencing_token: Mapped[int] = mapped_column(Integer, default=0)
    heartbeat_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class AssistantIndexCommand(Base):
    __tablename__ = "assistant_index_commands"
    __table_args__ = (
        CheckConstraint("kind IN ('rebuild')", name="ck_assistant_index_commands_kind"),
        CheckConstraint(
            "status IN ('pending', 'running', 'waiting', 'catch_up', 'ready_to_switch', "
            "'switch_pending', 'switched', 'failed', 'abandoned')",
            name="ck_assistant_index_commands_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(24))
    idempotency_key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    generation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    previous_generation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    worker_fence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_cursor: Mapped[str | None] = mapped_column(String(80), nullable=True)
    outbox_high_water: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_revision_set_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manifest_json: Mapped[str] = mapped_column(Text, default="{}")
    finalize_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    finalize_idempotency_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    safe_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    terminal_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class AssistantIndexRebuildProgress(Base):
    __tablename__ = "assistant_index_rebuild_progress"
    __table_args__ = (
        UniqueConstraint(
            "command_id", "source_type", "source_id", name="uq_assistant_rebuild_source"
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'waiting', 'dirty', 'failed')",
            name="ck_assistant_rebuild_progress_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    command_id: Mapped[str] = mapped_column(
        ForeignKey("assistant_index_commands.id", ondelete="CASCADE"), index=True
    )
    source_type: Mapped[str] = mapped_column(String(16))
    source_id: Mapped[int] = mapped_column(Integer)
    source_version: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), index=True)
    available_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class AssistantIndexRepairIntent(Base):
    __tablename__ = "assistant_index_repair_intents"
    __table_args__ = (
        UniqueConstraint(
            "source_type",
            "source_id",
            "target_version",
            "generation_id",
            name="uq_assistant_index_repair_intent",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(16))
    source_id: Mapped[int] = mapped_column(Integer)
    target_version: Mapped[str] = mapped_column(String(64))
    generation_id: Mapped[int] = mapped_column(Integer)
    reason_code: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class AssistantIndexProviderFact(Base):
    __tablename__ = "assistant_index_provider_facts"

    kind: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(16))
    reason_code: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(16))
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime())


class AssistantResumeSource(Base):
    __tablename__ = "assistant_resume_source"
    __table_args__ = (CheckConstraint("id = 1", name="ck_resume_source_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    binding_epoch: Mapped[int] = mapped_column(Integer, default=0)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(20), default="unconfigured")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    current_version_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    current_request_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    last_indexed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    last_refresh_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AssistantResumeVersion(Base):
    __tablename__ = "assistant_resume_versions"
    __table_args__ = (
        CheckConstraint("length(pdf_bytes) <= 10485760", name="ck_resume_pdf_bytes"),
        CheckConstraint("length(body) <= 200000", name="ck_resume_body_chars"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    binding_epoch: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    parser_version: Mapped[str] = mapped_column(String(64))
    pdf_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    pages_json: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)


class AssistantResumeRequest(Base):
    __tablename__ = "assistant_resume_requests"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    binding_epoch: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    lease_owner: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(32), nullable=True)
    worker_fence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
