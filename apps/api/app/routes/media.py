from __future__ import annotations

import hashlib
import io
import json
import logging
import uuid
import warnings
from typing import Annotated, cast

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError, features
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..dependencies import DbSession, require_admin, require_session_csrf
from ..media import MediaStorage
from ..models import AdminSession, MediaAsset
from ..pagination import PageLimit, PageOffset
from ..schemas import (
    ExternalMediaCreate,
    MediaAssetResponse,
    MediaBatchItemResult,
    MediaBatchRequest,
    MediaBatchResponse,
    MediaSource,
    MediaVariant,
)
from ..time_utils import utc_now

router = APIRouter(tags=["media"])
logger = logging.getLogger(__name__)
ALLOWED_UPLOAD_MIMES = {"image/jpeg", "image/png", "image/webp", "image/avif"}


def media_storage(db: DbSession) -> MediaStorage:
    return cast(MediaStorage, db.info["media_storage"])


def response(asset: MediaAsset) -> MediaAssetResponse:
    variants = [MediaVariant(**variant) for variant in json.loads(asset.variants_json)]
    return MediaAssetResponse(
        id=asset.id,
        source=cast(MediaSource, asset.source),
        original_name=asset.original_name,
        alt_text=asset.alt_text,
        mime_type=asset.mime_type,
        width=asset.width,
        height=asset.height,
        byte_size=asset.byte_size,
        url=asset.url,
        variants=variants,
        created_at=asset.created_at,
        deleted_at=asset.deleted_at,
    )


@router.get("/admin/media", response_model=list[MediaAssetResponse])
def list_media(
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
    limit: PageLimit = 20,
    offset: PageOffset = 0,
    q: Annotated[str | None, Query(max_length=200)] = None,
    source_filter: Annotated[str | None, Query(alias="source")] = None,
    status_filter: Annotated[str, Query(alias="status")] = "active",
) -> list[MediaAssetResponse]:
    if source_filter not in {None, "upload", "external"}:
        raise HTTPException(status_code=422, detail="invalid media source filter")
    if status_filter not in {"active", "removed", "all"}:
        raise HTTPException(status_code=422, detail="invalid media status filter")
    statement = select(MediaAsset)
    if status_filter == "active":
        statement = statement.where(MediaAsset.deleted_at.is_(None))
    elif status_filter == "removed":
        statement = statement.where(MediaAsset.deleted_at.is_not(None))
    if source_filter:
        statement = statement.where(MediaAsset.source == source_filter)
    if q and q.strip():
        term = q.strip()
        statement = statement.where(
            or_(
                MediaAsset.original_name.contains(term, autoescape=True),
                MediaAsset.alt_text.contains(term, autoescape=True),
            )
        )
    assets = db.scalars(
        statement
        .order_by(MediaAsset.created_at.desc(), MediaAsset.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [response(asset) for asset in assets]


@router.post(
    "/admin/media",
    response_model=MediaAssetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_media(
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
    file: Annotated[UploadFile, File()],
    alt_text: Annotated[str, Form(max_length=240)] = "",
) -> MediaAssetResponse:
    settings = db.info["settings"]
    if file.content_type not in ALLOWED_UPLOAD_MIMES:
        raise HTTPException(status_code=422, detail="unsupported image MIME type")
    data = await file.read(settings.media_max_bytes + 1)
    if len(data) > settings.media_max_bytes:
        raise HTTPException(status_code=413, detail="image exceeds configured size limit")
    content_sha256 = hashlib.sha256(data).hexdigest()
    existing = db.scalar(
        select(MediaAsset).where(MediaAsset.content_sha256 == content_sha256).limit(1)
    )
    if existing is not None:
        existing.deleted_at = None
        if alt_text.strip() and not existing.alt_text.strip():
            existing.alt_text = alt_text.strip()
        db.commit()
        db.refresh(existing)
        return response(existing)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            source = Image.open(io.BytesIO(data))
            detected_format = source.format
            if detected_format not in {"JPEG", "PNG", "WEBP", "AVIF"}:
                raise HTTPException(status_code=422, detail="unsupported image format")
            if source.width * source.height > settings.media_max_pixels:
                raise HTTPException(
                    status_code=422,
                    detail="image exceeds configured pixel limit",
                )
            source.verify()
            source = Image.open(io.BytesIO(data))
            oriented = ImageOps.exif_transpose(source)
            oriented.load()
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        raise HTTPException(status_code=422, detail="file is not a valid image") from error
    rendered = oriented.convert("RGBA" if oriented.mode in {"RGBA", "LA"} else "RGB")
    key = uuid.uuid4().hex
    pending: list[tuple[str, str, bytes]] = []
    formats = [("webp", "image/webp")]
    if features.check("avif"):
        formats.append(("avif", "image/avif"))
    for image_format, mime_type in formats:
        buffer = io.BytesIO()
        rendered.save(buffer, format=image_format.upper(), quality=82)
        pending.append((image_format, mime_type, buffer.getvalue()))
    asset = MediaAsset(
        source="upload",
        original_name=(file.filename or "image")[:255],
        alt_text=alt_text,
        mime_type=pending[0][1],
        width=rendered.width,
        height=rendered.height,
        byte_size=len(pending[0][2]),
        url="pending",
        storage_key=key,
        content_sha256=content_sha256,
    )
    storage = media_storage(db)
    committed = False
    try:
        db.add(asset)
        db.flush()
        variants = [
            {
                "format": image_format,
                "mime_type": mime_type,
                "url": f"/api/v1/media/{asset.id}/{image_format}",
                "byte_size": len(encoded),
                "width": rendered.width,
                "height": rendered.height,
            }
            for image_format, mime_type, encoded in pending
        ]
        storage.write_batch(
            key,
            {f"image.{image_format}": encoded for image_format, _, encoded in pending},
        )
        asset.url = str(variants[0]["url"])
        asset.variants_json = json.dumps(variants)
        db.commit()
        committed = True
    except IntegrityError as error:
        db.rollback()
        duplicate = db.scalar(
            select(MediaAsset).where(MediaAsset.content_sha256 == content_sha256).limit(1)
        )
        if duplicate is not None:
            duplicate.deleted_at = None
            db.commit()
            return response(duplicate)
        raise HTTPException(
            status_code=500,
            detail="media upload could not be completed",
        ) from error
    except (OSError, SQLAlchemyError, ValueError) as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="media upload could not be completed",
        ) from error
    finally:
        if not committed:
            try:
                storage.delete(key)
            except OSError:
                logger.exception("failed to compensate media upload for key %s", key)
    db.refresh(asset)
    return response(asset)


def get_asset_or_404(asset_id: int, db: DbSession) -> MediaAsset:
    asset = db.get(MediaAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="media not found")
    return asset


@router.post("/admin/media/discard-batch", response_model=MediaBatchResponse)
def discard_media_batch(
    payload: MediaBatchRequest,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> MediaBatchResponse:
    results: list[MediaBatchItemResult] = []
    for asset_id in payload.asset_ids:
        asset = db.get(MediaAsset, asset_id)
        if asset is None:
            results.append(
                MediaBatchItemResult(
                    id=asset_id,
                    ok=False,
                    error_code="NOT_FOUND",
                    error_message="媒体不存在",
                )
            )
            continue
        asset.deleted_at = asset.deleted_at or utc_now()
        results.append(MediaBatchItemResult(id=asset_id, ok=True))
    db.commit()
    return MediaBatchResponse(results=results)


@router.post("/admin/media/{asset_id}/discard", response_model=MediaAssetResponse)
def discard_media(
    asset_id: int,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> MediaAssetResponse:
    asset = get_asset_or_404(asset_id, db)
    asset.deleted_at = asset.deleted_at or utc_now()
    db.commit()
    db.refresh(asset)
    return response(asset)


@router.post("/admin/media/{asset_id}/restore", response_model=MediaAssetResponse)
def restore_media(
    asset_id: int,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> MediaAssetResponse:
    asset = get_asset_or_404(asset_id, db)
    asset.deleted_at = None
    db.commit()
    db.refresh(asset)
    return response(asset)


@router.post(
    "/admin/media/external",
    response_model=MediaAssetResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_external_media(
    payload: ExternalMediaCreate,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> MediaAssetResponse:
    url = str(payload.url)
    asset = MediaAsset(
        source="external",
        original_name="external image",
        alt_text=payload.alt_text,
        mime_type="image/external",
        url=url,
        variants_json="[]",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return response(asset)


@router.get("/media/{asset_id}/{image_format}", response_class=FileResponse)
def public_media(asset_id: int, image_format: str, db: DbSession) -> FileResponse:
    asset = db.get(MediaAsset, asset_id)
    if asset is None or asset.source != "upload" or asset.storage_key is None:
        raise HTTPException(status_code=404, detail="media not found")
    variant = next(
        (item for item in json.loads(asset.variants_json) if item["format"] == image_format),
        None,
    )
    if variant is None:
        raise HTTPException(status_code=404, detail="media variant not found")
    try:
        path = media_storage(db).path(asset.storage_key, f"image.{image_format}")
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="media file not found") from error
    return FileResponse(path, media_type=variant["mime_type"])
