from __future__ import annotations

import base64
import io
import logging
import warnings
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.media import LocalMediaStorage
from app.models import MediaAsset
from app.routes import media as media_routes

from .conftest import login

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_media_upload_conversion_external_registration_and_public_read(
    client: TestClient,
) -> None:
    assert client.get("/api/v1/admin/media").status_code == 401
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    no_csrf = client.post(
        "/api/v1/admin/media",
        files={"file": ("pixel.png", PNG, "image/png")},
    )
    assert no_csrf.status_code == 403
    uploaded = client.post(
        "/api/v1/admin/media",
        files={"file": ("pixel.png", PNG, "image/png")},
        data={"alt_text": "Blue pixel"},
        headers=headers,
    )
    assert uploaded.status_code == 201, uploaded.text
    asset = uploaded.json()
    assert asset["source"] == "upload"
    assert asset["alt_text"] == "Blue pixel"
    assert asset["width"] == asset["height"] == 1
    assert "webp" in {variant["format"] for variant in asset["variants"]}
    public = client.get(asset["url"])
    assert public.status_code == 200
    assert public.headers["content-type"].startswith("image/webp")

    external = client.post(
        "/api/v1/admin/media/external",
        json={"url": "https://example.com/diagram.png", "alt_text": "Architecture"},
        headers=headers,
    )
    assert external.status_code == 201
    assert external.json()["url"] == "https://example.com/diagram.png"
    assert len(client.get("/api/v1/admin/media").json()) == 2


def test_media_deduplicates_filters_and_keeps_public_url_after_soft_delete(
    client: TestClient,
) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    first = client.post(
        "/api/v1/admin/media",
        files={"file": ("pixel.png", PNG, "image/png")},
        data={"alt_text": "知识图谱"},
        headers=headers,
    )
    duplicate = client.post(
        "/api/v1/admin/media",
        files={"file": ("same-bytes.png", PNG, "image/png")},
        headers=headers,
    )
    assert first.status_code == duplicate.status_code == 201
    assert duplicate.json()["id"] == first.json()["id"]
    asset_id = first.json()["id"]
    public_url = first.json()["url"]

    filtered = client.get(
        "/api/v1/admin/media",
        params={"q": "知识", "source": "upload", "status": "active"},
    )
    assert [item["id"] for item in filtered.json()] == [asset_id]

    discarded = client.post(
        f"/api/v1/admin/media/{asset_id}/discard",
        headers=headers,
    )
    assert discarded.status_code == 200
    assert discarded.json()["deleted_at"] is not None
    assert client.get("/api/v1/admin/media").json() == []
    assert [item["id"] for item in client.get(
        "/api/v1/admin/media", params={"status": "removed"}
    ).json()] == [asset_id]
    assert client.get(public_url).status_code == 200

    restored = client.post(
        f"/api/v1/admin/media/{asset_id}/restore",
        headers=headers,
    )
    assert restored.status_code == 200
    assert restored.json()["deleted_at"] is None

    batch = client.post(
        "/api/v1/admin/media/discard-batch",
        headers=headers,
        json={"asset_ids": [asset_id, 999_999]},
    )
    assert batch.status_code == 200
    assert batch.json()["results"][0]["ok"] is True
    assert batch.json()["results"][1]["error_code"] == "NOT_FOUND"


def test_media_rejects_untrusted_payloads(client: TestClient) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    wrong_mime = client.post(
        "/api/v1/admin/media",
        files={"file": ("pixel.txt", PNG, "text/plain")},
        headers=headers,
    )
    assert wrong_mime.status_code == 422
    fake_image = client.post(
        "/api/v1/admin/media",
        files={"file": ("fake.png", b"not an image", "image/png")},
        headers=headers,
    )
    assert fake_image.status_code == 422


def encode_image(image_format: str, size: tuple[int, int]) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color="white").save(buffer, format=image_format)
    return buffer.getvalue()


def test_media_rejects_pixel_limit_before_transpose_or_decode(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csrf = login(client)
    client.app.state.settings.media_max_pixels = 100

    def unexpected_transpose(_: Image.Image) -> Image.Image:
        raise AssertionError("oversized image reached EXIF transpose")

    monkeypatch.setattr(media_routes.ImageOps, "exif_transpose", unexpected_transpose)
    response = client.post(
        "/api/v1/admin/media",
        files={"file": ("compressed.png", encode_image("PNG", (20, 20)), "image/png")},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "image exceeds configured pixel limit"


def test_media_rejects_detected_format_before_transpose_or_decode(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csrf = login(client)

    def unexpected_transpose(_: Image.Image) -> Image.Image:
        raise AssertionError("unsupported format reached EXIF transpose")

    monkeypatch.setattr(media_routes.ImageOps, "exif_transpose", unexpected_transpose)
    response = client.post(
        "/api/v1/admin/media",
        files={"file": ("disguised.png", encode_image("GIF", (1, 1)), "image/png")},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "unsupported image format"


def test_media_turns_decompression_bomb_warning_into_request_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csrf = login(client)

    def warn_on_open(*_: object, **__: object) -> Image.Image:
        warnings.warn(
            "injected decompression bomb",
            Image.DecompressionBombWarning,
            stacklevel=2,
        )
        raise AssertionError("warning was not promoted to an error")

    monkeypatch.setattr(media_routes.Image, "open", warn_on_open)
    response = client.post(
        "/api/v1/admin/media",
        files={"file": ("bomb.png", PNG, "image/png")},
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "file is not a valid image"


def test_local_storage_removes_staging_batch_when_a_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = LocalMediaStorage(tmp_path)
    original_write = Path.write_bytes
    writes = 0

    def fail_second_write(path: Path, data: bytes) -> int:
        nonlocal writes
        writes += 1
        if writes == 2:
            raise OSError("forced variant write failure")
        return original_write(path, data)

    monkeypatch.setattr(Path, "write_bytes", fail_second_write)

    with pytest.raises(OSError, match="forced variant write failure"):
        storage.write_batch("a" * 32, {"image.webp": b"webp", "image.avif": b"avif"})

    assert list(tmp_path.iterdir()) == []


def test_upload_rolls_back_partial_storage_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    media_root = Path(client.app.state.settings.media_root)

    def fail_after_partial_write(
        storage: LocalMediaStorage,
        key: str,
        files: dict[str, bytes],
    ) -> None:
        directory = storage.root.resolve() / key
        directory.mkdir(parents=True)
        (directory / next(iter(files))).write_bytes(next(iter(files.values())))
        raise OSError("forced storage failure")

    monkeypatch.setattr(LocalMediaStorage, "write_batch", fail_after_partial_write)
    response = client.post(
        "/api/v1/admin/media",
        files={"file": ("pixel.png", PNG, "image/png")},
        headers=headers,
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "media upload could not be completed"
    assert not media_root.exists() or list(media_root.iterdir()) == []
    with client.app.state.database.session_factory() as db:
        assert db.scalar(select(MediaAsset)) is None


def test_upload_removes_files_when_database_commit_fails(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    media_root = Path(client.app.state.settings.media_root)

    def fail_commit(_: Session) -> None:
        raise SQLAlchemyError("forced commit failure")

    monkeypatch.setattr(Session, "commit", fail_commit)
    response = client.post(
        "/api/v1/admin/media",
        files={"file": ("pixel.png", PNG, "image/png")},
        headers=headers,
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "media upload could not be completed"
    assert not media_root.exists() or list(media_root.iterdir()) == []
    with client.app.state.database.session_factory() as db:
        assert db.scalar(select(MediaAsset)) is None


def test_cleanup_failure_does_not_replace_original_upload_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}

    def fail_write(_: LocalMediaStorage, __: str, ___: dict[str, bytes]) -> None:
        raise OSError("original storage failure")

    def fail_delete(_: LocalMediaStorage, __: str) -> None:
        raise OSError("cleanup failure")

    monkeypatch.setattr(LocalMediaStorage, "write_batch", fail_write)
    monkeypatch.setattr(LocalMediaStorage, "delete", fail_delete)
    with caplog.at_level(logging.ERROR):
        response = client.post(
            "/api/v1/admin/media",
            files={"file": ("pixel.png", PNG, "image/png")},
            headers=headers,
        )

    assert response.status_code == 500
    assert response.json()["detail"] == "media upload could not be completed"
    assert "failed to compensate media upload" in caplog.text
