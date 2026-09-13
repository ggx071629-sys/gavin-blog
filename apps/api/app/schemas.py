from __future__ import annotations

import re
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, field_validator

SiteMediaAssetPath = Annotated[
    str,
    StringConstraints(pattern=r"^/api/v1/media/[1-9]\d*/(?:webp|avif)$"),
]
# 个人名片头像沿用同一站内媒体路径约定。
ProfileMediaAvatarPath = SiteMediaAssetPath


def validate_slug(value: str) -> str:
    value = value.strip().lower()
    if not value or len(value) > 160:
        raise ValueError("slug must contain 1-160 characters")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-")
    if any(character not in allowed for character in value):
        raise ValueError("slug may contain lowercase letters, digits, and hyphens only")
    if value.startswith("-") or value.endswith("-") or "--" in value:
        raise ValueError("slug cannot start, end, or repeat hyphens")
    return value


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=512)


class SessionResponse(BaseModel):
    username: str


class TaxonomyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    slug: str
    description: str = Field(default="", max_length=240)

    _slug = field_validator("slug")(validate_slug)


class TaxonomyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    slug: str | None = None
    description: str | None = Field(default=None, max_length=240)

    _slug = field_validator("slug")(lambda value: validate_slug(value) if value else value)


class TaxonomyItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str


class TaxonomyOption(BaseModel):
    id: int
    name: str
    slug: str
    article_count: int


class PublicTaxonomy(BaseModel):
    categories: list[TaxonomyOption]
    tags: list[TaxonomyOption]
    total_article_count: int


class ArticleReferenceInput(BaseModel):
    kind: Literal["external", "internal"]
    display_title: str = Field(min_length=1, max_length=180)
    url: str | None = Field(default=None, max_length=1000)
    target_type: Literal["article", "project", "book"] | None = None
    target_id: int | None = Field(default=None, ge=1)

    @field_validator("url")
    @classmethod
    def validate_external_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            return None
        if not stripped.startswith("https://"):
            raise ValueError("external reference url must be https")
        return stripped


class ArticleReference(BaseModel):
    kind: Literal["external", "internal"]
    display_title: str
    url: str | None = None
    target_type: Literal["article", "project", "book"] | None = None
    target_id: int | None = None


class WikiResolution(BaseModel):
    token: str
    display_title: str
    public_path: str | None = None
    content_type: Literal["article", "project", "book"] | None = None


class PublicBacklink(BaseModel):
    content_type: Literal["article", "project", "book"]
    id: int
    title: str
    summary: str
    published_at: datetime
    public_path: str


class ArticleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    slug: str
    summary: str = Field(default="", max_length=320)
    content: str = ""
    category_id: int | None = Field(default=None, ge=1)
    tag_ids: list[int] = Field(default_factory=list)
    references: list[ArticleReferenceInput] = Field(default_factory=list, max_length=20)

    _slug = field_validator("slug")(validate_slug)


class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    slug: str | None = None
    summary: str | None = Field(default=None, max_length=320)
    content: str | None = None
    category_id: int | None = Field(default=None, ge=1)
    tag_ids: list[int] | None = None
    references: list[ArticleReferenceInput] | None = Field(default=None, max_length=20)
    version: int = Field(ge=1)

    _slug = field_validator("slug")(lambda value: validate_slug(value) if value else value)


class PublishRequest(BaseModel):
    version: int = Field(ge=1)


class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    summary: str
    content: str
    status: str
    version: int
    current_revision_id: int | None = None
    current_publish_revision: int | None = None
    has_unpublished_changes: bool = False
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    public_path: str | None = None
    category: TaxonomyItem | None
    tags: list[TaxonomyItem]
    references: list[ArticleReference] = Field(default_factory=list)
    wikilinks: list[WikiResolution] = Field(default_factory=list)


class PublicArticle(BaseModel):
    id: int
    title: str
    slug: str
    summary: str
    content: str
    published_at: datetime
    updated_at: datetime
    public_path: str
    category: TaxonomyItem | None
    tags: list[TaxonomyItem]
    references: list[PublicReference] = Field(default_factory=list)
    wikilinks: list[WikiResolution] = Field(default_factory=list)


class PublicReference(BaseModel):
    display_title: str
    url: str


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    slug: str
    summary: str = Field(default="", max_length=320)
    content: str = ""
    repository_url: HttpUrl | None = None
    website_url: HttpUrl | None = None
    article_ids: list[int] = Field(default_factory=list)

    _slug = field_validator("slug")(validate_slug)


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    slug: str | None = None
    summary: str | None = Field(default=None, max_length=320)
    content: str | None = None
    repository_url: HttpUrl | None = None
    website_url: HttpUrl | None = None
    article_ids: list[int] | None = None
    version: int = Field(ge=1)

    _slug = field_validator("slug")(lambda value: validate_slug(value) if value else value)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    summary: str
    content: str
    repository_url: str | None
    website_url: str | None
    status: str
    version: int
    current_revision_id: int | None = None
    current_publish_revision: int | None = None
    has_unpublished_changes: bool = False
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    public_path: str | None = None
    article_ids: list[int] = Field(default_factory=list)


class RelatedArticle(BaseModel):
    id: int
    title: str
    slug: str
    summary: str
    published_at: datetime
    public_path: str


class ArticleContext(BaseModel):
    previous: RelatedArticle | None = None
    next: RelatedArticle | None = None
    related: list[RelatedArticle] = Field(default_factory=list)
    backlinks: list[PublicBacklink] = Field(default_factory=list)


class PublicProject(BaseModel):
    id: int
    title: str
    slug: str
    summary: str
    content: str
    repository_url: str | None
    website_url: str | None
    published_at: datetime
    updated_at: datetime
    public_path: str
    related_articles: list[RelatedArticle]
    backlinks: list[PublicBacklink] = Field(default_factory=list)
    wikilinks: list[WikiResolution] = Field(default_factory=list)


ReadingStatus = Literal["planned", "reading", "completed", "paused"]
MediaSource = Literal["upload", "external"]


class BookNoteCreate(BaseModel):
    book_title: str = Field(min_length=1, max_length=180)
    author: str = Field(min_length=1, max_length=180)
    slug: str
    cover_url: HttpUrl | SiteMediaAssetPath | None = None
    reading_status: ReadingStatus = "planned"
    reading_date: date | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    summary: str = Field(default="", max_length=320)
    content: str = ""

    _slug = field_validator("slug")(validate_slug)


class BookNoteUpdate(BaseModel):
    book_title: str | None = Field(default=None, min_length=1, max_length=180)
    author: str | None = Field(default=None, min_length=1, max_length=180)
    slug: str | None = None
    cover_url: HttpUrl | SiteMediaAssetPath | None = None
    reading_status: ReadingStatus | None = None
    reading_date: date | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    summary: str | None = Field(default=None, max_length=320)
    content: str | None = None
    version: int = Field(ge=1)

    _slug = field_validator("slug")(lambda value: validate_slug(value) if value else value)


class BookNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_title: str
    author: str
    slug: str
    cover_url: str | None
    reading_status: ReadingStatus
    reading_date: date | None
    rating: int | None
    summary: str
    content: str
    status: str
    version: int
    current_revision_id: int | None = None
    current_publish_revision: int | None = None
    has_unpublished_changes: bool = False
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    public_path: str | None = None


class PublicBookNote(BaseModel):
    id: int
    book_title: str
    author: str
    slug: str
    cover_url: str | None
    reading_status: ReadingStatus
    reading_date: date | None
    rating: int | None
    summary: str
    content: str
    published_at: datetime
    updated_at: datetime
    public_path: str
    backlinks: list[PublicBacklink] = Field(default_factory=list)
    wikilinks: list[WikiResolution] = Field(default_factory=list)


class SearchResult(BaseModel):
    content_type: Literal["article", "project", "book"]
    content_id: int
    title: str
    summary: str
    snippet: str
    public_path: str
    published_at: datetime
    score: float


class MediaVariant(BaseModel):
    format: str
    mime_type: str
    url: str
    byte_size: int
    width: int
    height: int


class MediaAssetResponse(BaseModel):
    id: int
    source: MediaSource
    original_name: str
    alt_text: str
    mime_type: str
    width: int | None
    height: int | None
    byte_size: int | None
    url: str
    variants: list[MediaVariant]
    created_at: datetime
    deleted_at: datetime | None = None


class ExternalMediaCreate(BaseModel):
    url: HttpUrl
    alt_text: str = Field(default="", max_length=240)


class MediaBatchRequest(BaseModel):
    asset_ids: list[int] = Field(min_length=1, max_length=100)


class MediaBatchItemResult(BaseModel):
    id: int
    ok: bool
    error_code: str | None = None
    error_message: str | None = None


class MediaBatchResponse(BaseModel):
    results: list[MediaBatchItemResult]


class TrashItem(BaseModel):
    content_type: Literal["article", "project", "book"]
    content_id: int
    title: str
    slug: str
    status: str
    deleted_at: datetime


class MarkdownImportItem(BaseModel):
    filename: str
    content_type: Literal["article", "project", "book"]
    content_id: int
    slug: str
    warnings: list[str] = Field(default_factory=list)


class MarkdownImportResponse(BaseModel):
    imported: list[MarkdownImportItem]


_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_email(value: str) -> str:
    value = value.strip()
    if not _EMAIL_RE.match(value):
        raise ValueError("invalid email address")
    return value


def validate_skills(value: list[str]) -> list[str]:
    cleaned = [item.strip() for item in value]
    if any(not item or len(item) > 30 for item in cleaned):
        raise ValueError("each skill must contain 1-30 characters")
    return cleaned


class ProfilePublic(BaseModel):
    name: str
    title: str
    bio: str
    skills: list[str]
    avatar_url: str | None = None
    github_url: str | None = None
    website_url: str | None = None
    resume_url: str | None = None
    city: str | None = None
    email: str | None = None


class ProfileAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    title: str
    bio: str
    skills: list[str]
    avatar_url: str | None
    city: str | None
    city_visible: bool
    github_url: str | None
    website_url: str | None
    email: str | None
    email_visible: bool
    resume_url: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=120)
    bio: str = Field(min_length=1, max_length=240)
    skills: list[str] = Field(max_length=6)
    avatar_url: HttpUrl | ProfileMediaAvatarPath | None = None
    city: str | None = Field(default=None, max_length=80)
    city_visible: bool = False
    github_url: HttpUrl | None = None
    website_url: HttpUrl | None = None
    email: str | None = None
    email_visible: bool = False
    resume_url: HttpUrl | None = None
    version: int = Field(ge=1)

    _email = field_validator("email")(lambda value: validate_email(value) if value else value)
    _skills = field_validator("skills")(validate_skills)


AboutNowStatus = Literal["in_progress", "building", "exploring"]
AboutNowTarget = Literal["projects", "articles", "books"]
AboutTag = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=30),
]
AboutTopic = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=40),
]


class AboutCapability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=80),
    ]
    description: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=320),
    ]
    tags: list[AboutTag] = Field(default_factory=list, max_length=6)


class AboutNowItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=80),
    ]
    status: AboutNowStatus
    target: AboutNowTarget


class AboutSiteStackItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=40),
    ]
    value: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=80),
    ]


class AboutSite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=320),
    ]
    stack: list[AboutSiteStackItem] = Field(default_factory=list, max_length=8)


class AboutPageContent(BaseModel):
    """Structured About-page copy stored in the working copy and every snapshot."""

    model_config = ConfigDict(extra="forbid")

    statement: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
    ]
    capabilities: list[AboutCapability] = Field(min_length=1, max_length=10)
    now: list[AboutNowItem] = Field(default_factory=list, max_length=10)
    editorial_topics: list[AboutTopic] = Field(min_length=1, max_length=8)
    site: AboutSite


class AboutPageUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: AboutPageContent
    version: int = Field(ge=1)


class AboutPageRollbackRequest(BaseModel):
    version: int = Field(ge=1)
    current_revision_id: int = Field(ge=1)
    rollback_confirmed: bool = False


class AboutPageAdmin(BaseModel):
    id: int
    content: AboutPageContent
    status: str
    version: int
    current_revision_id: int | None = None
    current_publish_revision: int | None = None
    has_unpublished_changes: bool = False
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AboutRevisionSummary(BaseModel):
    id: int
    revision_number: int
    source: str
    published_at: datetime
    content_sha256: str
    rollback_from_revision_id: int | None = None


class AboutRevisionListResponse(BaseModel):
    total: int
    revisions: list[AboutRevisionSummary]


class AboutRevisionDetail(AboutRevisionSummary):
    content: AboutPageContent


class AboutRevisionDiffResponse(BaseModel):
    from_revision_id: int
    to_revision_id: int
    statement: str
    capabilities: str
    now: str
    editorial_topics: str
    site: str


class ApiErrorBody(BaseModel):
    code: str
    message: str


class ApiErrorResponse(BaseModel):
    error: ApiErrorBody


class ArticleRevisionSummary(BaseModel):
    id: int
    revision_number: int
    title: str
    slug: str
    source: str
    published_at: datetime
    content_sha256: str
    rollback_from_revision_id: int | None = None


class ArticleRevisionDetail(BaseModel):
    id: int
    article_id: int
    revision_number: int
    title: str
    slug: str
    summary: str
    content: str
    category: TaxonomyItem | None
    tags: list[TaxonomyItem]
    references: list[PublicReference] = Field(default_factory=list)
    source: str
    published_at: datetime
    first_published_at: datetime
    content_sha256: str
    rollback_from_revision_id: int | None = None


class ArticleRevisionListResponse(BaseModel):
    total: int = 0
    revisions: list[ArticleRevisionSummary] = Field(default_factory=list)


class ArticleRevisionDiffResponse(BaseModel):
    article_id: int
    from_revision_id: int
    to_revision_id: int
    title: str = ""
    summary: str = ""
    content: str = ""
    category: str = ""
    tags: str = ""
    references: str = ""


class ArticleRollbackRequest(BaseModel):
    version: int = Field(ge=1)
    current_revision_id: int = Field(ge=1)
    rollback_confirmed: bool = False


class AdminListCounts(BaseModel):
    all: int
    published: int
    draft: int


class ArticleListQueryResponse(BaseModel):
    items: list[ArticleResponse]
    total: int
    counts: AdminListCounts


class BookListQueryResponse(BaseModel):
    items: list[BookNoteResponse]
    total: int
    counts: AdminListCounts


class ProjectListQueryResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    counts: AdminListCounts
