from __future__ import annotations

import io
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Literal, cast

import yaml
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StrictInt,
    StrictStr,
    TypeAdapter,
    ValidationError,
    field_validator,
)
from sqlalchemy import delete, literal, select, union_all
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from yaml.tokens import AliasToken, AnchorToken

from ..assistant_index.outbox import enqueue_for_content, enqueue_purge
from ..dependencies import DbSession, require_admin, require_session_csrf
from ..models import (
    AdminSession,
    Article,
    ArticleRevision,
    BookNote,
    BookNoteRevision,
    Category,
    Project,
    ProjectRevision,
    Tag,
    project_articles,
)
from ..pagination import PageLimit, PageOffset
from ..schemas import (
    ArticleCreate,
    BookNoteCreate,
    MarkdownImportItem,
    MarkdownImportResponse,
    ProjectCreate,
    TrashItem,
    validate_slug,
)
from ..search import sync_search_document
from ..time_utils import utc_now

router = APIRouter(prefix="/admin", tags=["admin content tools"])
ContentType = Literal["article", "project", "book"]
MODEL_BY_TYPE: dict[ContentType, type[Article | Project | BookNote]] = {
    "article": Article,
    "project": Project,
    "book": BookNote,
}
MAX_IMPORT_FILES = 50
MAX_IMPORT_BYTES = 2 * 1024 * 1024
MAX_IMPORT_TOTAL_BYTES = 10 * 1024 * 1024
MAX_FRONT_MATTER_BYTES = 64 * 1024
MAX_METADATA_DEPTH = 8
MAX_METADATA_NODES = 200


def validate_slug_list(values: list[str]) -> list[str]:
    return [validate_slug(value) for value in values]


def validate_datetime_input(value: object) -> object:
    if value is not None and not isinstance(value, (str, datetime)):
        raise ValueError("timestamp must be an ISO 8601 string")
    return value


class ImportMetadataBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: StrictStr
    summary: StrictStr = Field(default="", max_length=320)
    status: Literal["draft", "published"] | None = None
    published_at: datetime | None = None
    deleted_at: datetime | None = None

    _slug = field_validator("slug")(validate_slug)
    _lifecycle_times = field_validator("published_at", "deleted_at", mode="before")(
        validate_datetime_input
    )


class ArticleImportMetadata(ImportMetadataBase):
    type: Literal["article"]
    title: StrictStr = Field(min_length=1, max_length=180)
    category_slug: StrictStr | None = Field(default=None, max_length=160)
    tag_slugs: list[StrictStr] = Field(default_factory=list, max_length=100)

    _category_slug = field_validator("category_slug")(
        lambda value: validate_slug(value) if value else value
    )
    _tag_slugs = field_validator("tag_slugs")(validate_slug_list)


class ProjectImportMetadata(ImportMetadataBase):
    type: Literal["project"]
    title: StrictStr = Field(min_length=1, max_length=180)
    repository_url: HttpUrl | None = None
    website_url: HttpUrl | None = None
    article_slugs: list[StrictStr] = Field(default_factory=list, max_length=100)

    _article_slugs = field_validator("article_slugs")(validate_slug_list)


class BookImportMetadata(ImportMetadataBase):
    type: Literal["book"]
    book_title: StrictStr = Field(min_length=1, max_length=180)
    author: StrictStr = Field(min_length=1, max_length=180)
    cover_url: HttpUrl | None = None
    reading_status: Literal["planned", "reading", "completed", "paused"] = "planned"
    reading_date: date | None = None
    rating: StrictInt | None = Field(default=None, ge=1, le=5)

    @field_validator("reading_date", mode="before")
    @classmethod
    def validate_reading_date_input(cls, value: object) -> object:
        if value is not None and not isinstance(value, (str, date)):
            raise ValueError("reading_date must be an ISO 8601 date string")
        return value


ImportMetadata = Annotated[
    ArticleImportMetadata | ProjectImportMetadata | BookImportMetadata,
    Field(discriminator="type"),
]
IMPORT_METADATA_ADAPTER: TypeAdapter[ImportMetadata] = TypeAdapter(ImportMetadata)


def title_of(item: Article | Project | BookNote) -> str:
    return item.book_title if isinstance(item, BookNote) else item.title


def get_trashed(content_type: ContentType, content_id: int, db: DbSession):
    item = cast(
        Article | Project | BookNote | None,
        db.get(MODEL_BY_TYPE[content_type], content_id),
    )
    if item is None or item.deleted_at is None:
        raise HTTPException(status_code=404, detail="trashed content not found")
    return item


@router.get("/trash", response_model=list[TrashItem])
def list_trash(
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
    limit: PageLimit = 20,
    offset: PageOffset = 0,
) -> list[TrashItem]:
    trash_union = union_all(
        select(
            literal("article").label("content_type"),
            Article.id.label("content_id"),
            Article.title.label("title"),
            Article.slug.label("slug"),
            Article.status.label("status"),
            Article.deleted_at.label("deleted_at"),
        ).where(Article.deleted_at.is_not(None)),
        select(
            literal("book").label("content_type"),
            BookNote.id.label("content_id"),
            BookNote.book_title.label("title"),
            BookNote.slug.label("slug"),
            BookNote.status.label("status"),
            BookNote.deleted_at.label("deleted_at"),
        ).where(BookNote.deleted_at.is_not(None)),
        select(
            literal("project").label("content_type"),
            Project.id.label("content_id"),
            Project.title.label("title"),
            Project.slug.label("slug"),
            Project.status.label("status"),
            Project.deleted_at.label("deleted_at"),
        ).where(Project.deleted_at.is_not(None)),
    ).subquery()
    rows = db.execute(
        select(trash_union)
        .order_by(
            trash_union.c.deleted_at.desc(),
            trash_union.c.content_type.asc(),
            trash_union.c.content_id.desc(),
        )
        .limit(limit)
        .offset(offset)
    ).mappings()
    return [TrashItem(**row) for row in rows]


@router.post("/trash/{content_type}/{content_id}/restore", response_model=TrashItem)
def restore_content(
    content_type: ContentType,
    content_id: int,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> TrashItem:
    item = get_trashed(content_type, content_id, db)
    previous_deleted_at = item.deleted_at
    item.deleted_at = None
    item.version += 1
    sync_search_document(db, item)
    enqueue_for_content(db, item)
    from ..knowledge_links import rebuild_content_links

    if getattr(item, "status", None) == "published":
        rebuild_content_links(db, item)
    db.commit()
    return TrashItem(
        content_type=content_type,
        content_id=item.id,
        title=title_of(item),
        slug=item.slug,
        status=item.status,
        deleted_at=previous_deleted_at,
    )


def detach_published_article(db: DbSession, article: Article) -> None:
    db.execute(delete(project_articles).where(project_articles.c.article_id == article.id))
    article.current_revision_id = None
    db.flush()
    db.execute(delete(ArticleRevision).where(ArticleRevision.article_id == article.id))
    db.flush()


@router.delete("/trash/{content_type}/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def permanently_delete_content(
    content_type: ContentType,
    content_id: int,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> Response:
    item = get_trashed(content_type, content_id, db)
    from ..knowledge_links import clear_content_links

    clear_content_links(db, item)
    sync_search_document(db, item)
    enqueue_purge(db, item)
    if isinstance(item, Article):
        detach_published_article(db, item)
    db.delete(item)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="content is still referenced") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def iso(value: date | datetime | None) -> str | None:
    return value.isoformat() if value else None


def export_snapshot(item: Article | Project | BookNote) -> tuple[dict, str]:
    published = item.status == "published" and item.current_revision is not None
    common = {
        "slug": item.slug,
        "summary": item.summary,
        "status": item.status,
        "published_at": iso(item.published_at),
        "deleted_at": iso(item.deleted_at),
    }
    if isinstance(item, Article):
        revision = item.current_revision if published else None
        if isinstance(revision, ArticleRevision):
            metadata = {
                **common,
                "slug": revision.slug,
                "summary": revision.summary,
                "type": "article",
                "title": revision.title,
                "category_slug": revision.category_slug or None,
                "tag_slugs": [tag.slug for tag in revision.tags],
            }
            return metadata, revision.content
        return {
            **common,
            "type": "article",
            "title": item.title,
            "category_slug": item.category.slug if item.category else None,
            "tag_slugs": [tag.slug for tag in item.tags],
        }, item.content
    if isinstance(item, Project):
        project_revision = item.current_revision if published else None
        if isinstance(project_revision, ProjectRevision):
            article_ids = [link.article_id for link in project_revision.article_links]
            return {
                **common,
                "slug": project_revision.slug,
                "summary": project_revision.summary,
                "type": "project",
                "title": project_revision.title,
                "repository_url": project_revision.repository_url,
                "website_url": project_revision.website_url,
                "article_slugs": [
                    article.slug for article in item.articles if article.id in set(article_ids)
                ],
            }, project_revision.content
        return {
            **common,
            "type": "project",
            "title": item.title,
            "repository_url": item.repository_url,
            "website_url": item.website_url,
            "article_slugs": [article.slug for article in item.articles],
        }, item.content
    book_revision = item.current_revision if published else None
    if isinstance(book_revision, BookNoteRevision):
        return {
            **common,
            "slug": book_revision.slug,
            "summary": book_revision.summary,
            "type": "book",
            "book_title": book_revision.book_title,
            "author": book_revision.author,
            "cover_url": book_revision.cover_url,
            "reading_status": book_revision.reading_status,
            "reading_date": iso(book_revision.reading_date),
            "rating": book_revision.rating,
        }, book_revision.content
    return {
        **common,
        "type": "book",
        "book_title": item.book_title,
        "author": item.author,
        "cover_url": item.cover_url,
        "reading_status": item.reading_status,
        "reading_date": iso(item.reading_date),
        "rating": item.rating,
    }, item.content


def markdown_document(item: Article | Project | BookNote) -> tuple[str, str]:
    metadata, content = export_snapshot(item)
    dumped = yaml.safe_dump(
        metadata,
        allow_unicode=True,
        sort_keys=False,
    ).rstrip()
    filename_slug = str(metadata["slug"])
    return filename_slug, f"---\n{dumped}\n---\n\n{content.rstrip()}\n"


@router.get("/exports/markdown", response_class=StreamingResponse)
def export_markdown(
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
) -> StreamingResponse:
    output = io.BytesIO()
    queries = (
        (
            "articles",
            select(Article)
            .options(
                selectinload(Article.category),
                selectinload(Article.tags),
                selectinload(Article.current_revision).selectinload(ArticleRevision.tags),
            )
            .order_by(Article.id),
        ),
        (
            "projects",
            select(Project)
            .options(
                selectinload(Project.articles),
                selectinload(Project.current_revision).selectinload(
                    ProjectRevision.article_links
                ),
            )
            .order_by(Project.id),
        ),
        (
            "books",
            select(BookNote)
            .options(selectinload(BookNote.current_revision))
            .order_by(BookNote.id),
        ),
    )
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for folder, query in queries:
            for item in db.scalars(query).unique().all():
                slug, document = markdown_document(item)
                archive.writestr(f"{folder}/{slug}.md", document)
    output.seek(0)
    filename = f"gavin-markdown-{utc_now():%Y%m%d}.zip"
    return StreamingResponse(
        output,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def validate_metadata_complexity(metadata: object, filename: str) -> None:
    pending: list[tuple[object, int]] = [(metadata, 0)]
    nodes = 0
    while pending:
        value, depth = pending.pop()
        nodes += 1
        if depth > MAX_METADATA_DEPTH or nodes > MAX_METADATA_NODES:
            raise HTTPException(status_code=422, detail=f"{filename}: front matter is too complex")
        if isinstance(value, dict):
            pending.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            pending.extend((item, depth + 1) for item in value)


def parse_markdown(filename: str, data: bytes) -> tuple[ImportMetadata, str]:
    if len(data) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail=f"{filename}: file is too large")
    try:
        document = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=422, detail=f"{filename}: UTF-8 is required") from error
    # Windows 编辑器与导出常见的 CRLF（含单独的 CR）先统一为 LF，再做 front matter 与正文解析；
    # 这样同一内容的 LF/CRLF 文件得到一致的元数据与正文，而不是被误判为缺少 front matter。
    document = document.replace("\r\n", "\n").replace("\r", "\n")
    if not document.startswith("---\n") or "\n---\n" not in document[4:]:
        raise HTTPException(status_code=422, detail=f"{filename}: front matter is required")
    raw_metadata, content = document[4:].split("\n---\n", 1)
    if len(raw_metadata.encode("utf-8")) > MAX_FRONT_MATTER_BYTES:
        raise HTTPException(status_code=413, detail=f"{filename}: front matter is too large")
    try:
        if any(isinstance(token, (AliasToken, AnchorToken)) for token in yaml.scan(raw_metadata)):
            raise HTTPException(
                status_code=422,
                detail=f"{filename}: YAML aliases are not supported",
            )
        raw = yaml.safe_load(raw_metadata)
    except (yaml.YAMLError, RecursionError) as error:
        raise HTTPException(
            status_code=422,
            detail=f"{filename}: front matter must be safe YAML",
        ) from error
    validate_metadata_complexity(raw, filename)
    try:
        metadata = IMPORT_METADATA_ADAPTER.validate_python(raw)
    except ValidationError as error:
        raise HTTPException(
            status_code=422,
            detail=f"{filename}: front matter fields are invalid",
        ) from error
    return metadata, content.lstrip("\n")


def conflict_exists(db: DbSession, content_type: ContentType, slug: str) -> bool:
    model = MODEL_BY_TYPE[content_type]
    return db.scalar(select(model.id).where(model.slug == slug).limit(1)) is not None


@router.post("/imports/markdown", response_model=MarkdownImportResponse)
async def import_markdown(
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
    files: Annotated[list[UploadFile], File()],
) -> MarkdownImportResponse:
    if not files or len(files) > MAX_IMPORT_FILES:
        raise HTTPException(status_code=422, detail="import requires 1-50 Markdown files")
    parsed: list[tuple[str, ImportMetadata, str]] = []
    seen: set[tuple[str, str]] = set()
    total_bytes = 0
    for upload in files:
        filename = Path(upload.filename or "content.md").name
        if len(filename) > 255:
            raise HTTPException(status_code=422, detail="import filename is too long")
        if not filename.lower().endswith(".md"):
            raise HTTPException(status_code=422, detail=f"{filename}: Markdown file required")
        data = await upload.read(MAX_IMPORT_BYTES + 1)
        total_bytes += len(data)
        if total_bytes > MAX_IMPORT_TOTAL_BYTES:
            raise HTTPException(status_code=413, detail="import batch exceeds total size limit")
        metadata, content = parse_markdown(filename, data)
        content_type = metadata.type
        slug = metadata.slug
        key = (content_type, slug)
        if key in seen or conflict_exists(db, content_type, slug):
            raise HTTPException(status_code=409, detail=f"{filename}: slug already exists")
        seen.add(key)
        parsed.append((filename, metadata, content))

    imported: list[MarkdownImportItem] = []
    try:
        for filename, metadata, content in sorted(
            parsed, key=lambda item: 1 if item[1].type == "project" else 0
        ):
            content_type = metadata.type
            warnings: list[str] = []
            item: Article | Project | BookNote
            if isinstance(metadata, ArticleImportMetadata):
                category = None
                if metadata.category_slug:
                    category = db.scalar(
                        select(Category).where(Category.slug == metadata.category_slug)
                    )
                    if category is None:
                        warnings.append(f"missing category: {metadata.category_slug}")
                tag_slugs = set(metadata.tag_slugs)
                tags = (
                    list(db.scalars(select(Tag).where(Tag.slug.in_(tag_slugs))).all())
                    if tag_slugs
                    else []
                )
                missing_tags = tag_slugs - {tag.slug for tag in tags}
                warnings.extend(f"missing tag: {slug}" for slug in sorted(missing_tags))
                payload = ArticleCreate(
                    title=metadata.title,
                    slug=metadata.slug,
                    summary=metadata.summary,
                    content=content,
                )
                item = Article(
                    **payload.model_dump(exclude={"category_id", "tag_ids", "references"}),
                    category=category,
                    tags=tags,
                )
            elif isinstance(metadata, ProjectImportMetadata):
                article_slugs = set(metadata.article_slugs)
                articles = (
                    list(db.scalars(select(Article).where(Article.slug.in_(article_slugs))).all())
                    if article_slugs
                    else []
                )
                missing_articles = article_slugs - {article.slug for article in articles}
                warnings.extend(f"missing article: {slug}" for slug in sorted(missing_articles))
                project_payload = ProjectCreate(
                    title=metadata.title,
                    slug=metadata.slug,
                    summary=metadata.summary,
                    content=content,
                    repository_url=metadata.repository_url,
                    website_url=metadata.website_url,
                )
                project_data = project_payload.model_dump(exclude={"article_ids"})
                for field in ("repository_url", "website_url"):
                    if project_data[field] is not None:
                        project_data[field] = str(project_data[field])
                item = Project(**project_data, articles=articles)
            else:
                book_payload = BookNoteCreate(
                    book_title=metadata.book_title,
                    author=metadata.author,
                    slug=metadata.slug,
                    cover_url=metadata.cover_url,
                    reading_status=metadata.reading_status,
                    reading_date=metadata.reading_date,
                    rating=metadata.rating,
                    summary=metadata.summary,
                    content=content,
                )
                book_data = book_payload.model_dump()
                if book_data["cover_url"] is not None:
                    book_data["cover_url"] = str(book_data["cover_url"])
                item = BookNote(**book_data)
            db.add(item)
            db.flush()
            imported.append(
                MarkdownImportItem(
                    filename=filename,
                    content_type=content_type,
                    content_id=item.id,
                    slug=item.slug,
                    warnings=warnings,
                )
            )
        db.commit()
    except ValidationError as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=error.errors()) from error
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="imported content conflicts with existing data"
        ) from error
    return MarkdownImportResponse(imported=imported)
