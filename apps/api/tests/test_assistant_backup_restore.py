from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier, Event

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.assistant.owner_lock import ExclusiveFileLock
from app.assistant_qualification.backup_restore import (
    BackupRestoreError,
    create_consistent_snapshot,
    restore_to_fresh_target,
    verify_snapshot,
)
from app.config import Settings
from app.db import Database
from app.main import create_app
from app.models import MediaAsset


def _migrate(database: Path, revision: str = "head") -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
    config.set_main_option("script_location", str(api_root / "migrations"))
    config.attributes["database_url"] = f"sqlite:///{database.as_posix()}"
    command.upgrade(config, revision)


def _prepared_settings(tmp_path: Path, *, revision: str = "head") -> Settings:
    database_path = tmp_path / "live" / "content.db"
    database_path.parent.mkdir(parents=True)
    _migrate(database_path, revision)
    media_root = tmp_path / "live" / "media"
    key = "a" * 32
    variant = media_root / key / "image.webp"
    variant.parent.mkdir(parents=True)
    variant.write_bytes(b"reviewed-media-variant")
    database = Database(f"sqlite:///{database_path.as_posix()}")
    with database.session_factory() as session:
        session.add(
            MediaAsset(
                source="upload",
                original_name="avatar.png",
                alt_text="Avatar",
                mime_type="image/webp",
                width=32,
                height=32,
                byte_size=variant.stat().st_size,
                url="/api/v1/media/1/webp",
                storage_key=key,
                content_sha256="b" * 64,
                variants_json=json.dumps(
                    [
                        {
                            "format": "webp",
                            "mime_type": "image/webp",
                            "url": "/api/v1/media/1/webp",
                            "byte_size": variant.stat().st_size,
                            "width": 32,
                            "height": 32,
                        }
                    ]
                ),
            )
        )
        session.commit()
    database.engine.dispose()
    return Settings(
        environment="test",
        database_url=f"sqlite:///{database_path.as_posix()}",
        content_write_fence_path=str((tmp_path / "live" / "content.write.lock").resolve()),
        media_root=str(media_root),
        assistant_runtime_path=str(tmp_path / "live" / "assistant-runtime.db"),
        admin_password="correct-horse",
        cookie_secure=False,
        _env_file=None,
    )


def test_fenced_snapshot_binds_database_media_schema_and_runtime_exclusion(
    tmp_path: Path,
) -> None:
    settings = _prepared_settings(tmp_path)
    snapshot = tmp_path / "snapshot"
    manifest = create_consistent_snapshot(
        settings=settings,
        snapshot_dir=snapshot,
        created_at=datetime(2026, 8, 30, 9, 0, tzinfo=UTC),
    )
    assert manifest["consistency_strategy"] == "write-fence-and-online-backup"
    assert manifest["media"]["asset_count"] == 1
    assert manifest["media"]["file_count"] == 1
    assert manifest["content_database"]["quick_check"] == "ok"
    assert manifest["content_database"]["alembic_versions"]
    assert manifest["exclusions"]["assistant_runtime"] is True
    assert manifest["encrypted_off_host_receipt_included"] is False
    assert verify_snapshot(snapshot) == manifest


def test_snapshot_tampering_and_database_media_mismatch_fail_closed(tmp_path: Path) -> None:
    settings = _prepared_settings(tmp_path)
    snapshot = tmp_path / "snapshot"
    manifest = create_consistent_snapshot(settings=settings, snapshot_dir=snapshot)
    media_file = snapshot / "media" / manifest["media"]["files"][0]["path"]
    media_file.write_bytes(b"tampered")
    with pytest.raises(BackupRestoreError, match="media hash"):
        verify_snapshot(snapshot)

    settings = _prepared_settings(tmp_path / "second")
    orphan = Path(settings.media_root) / ("c" * 32) / "image.webp"
    orphan.parent.mkdir(parents=True)
    orphan.write_bytes(b"orphan")
    with pytest.raises(BackupRestoreError, match="manifest mismatch"):
        create_consistent_snapshot(
            settings=settings,
            snapshot_dir=tmp_path / "second" / "snapshot",
        )


def test_http_mutation_is_rejected_while_backup_fence_is_held(tmp_path: Path) -> None:
    settings = _prepared_settings(tmp_path)
    app = create_app(settings)
    lock = ExclusiveFileLock(Path(str(settings.content_write_fence_path)))
    lock.acquire()
    try:
        with TestClient(app) as client:
            csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
            blocked = client.post(
                "/api/v1/auth/login",
                json={"username": "gavin", "password": "correct-horse"},
                headers={"X-CSRF-Token": csrf},
            )
            assert blocked.status_code == 503
            assert blocked.headers["retry-after"] == "5"
    finally:
        lock.release()
        app.state.database.engine.dispose()


def test_same_api_owner_serializes_concurrent_mutations_before_file_fence(
    tmp_path: Path,
) -> None:
    settings = _prepared_settings(tmp_path)
    app = create_app(settings)
    first_entered = Event()
    release_first = Event()
    start_together = Barrier(2)

    @app.post("/test/slow-content-mutation")
    async def slow_content_mutation():
        if not first_entered.is_set():
            first_entered.set()
            await asyncio.to_thread(release_first.wait, 5)
        return {"ok": True}

    with TestClient(app) as client:
        def send() -> int:
            start_together.wait(timeout=5)
            return client.post("/test/slow-content-mutation").status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(send)
            second = pool.submit(send)
            assert first_entered.wait(timeout=5)
            time.sleep(0.1)
            release_first.set()
            assert sorted((first.result(timeout=5), second.result(timeout=5))) == [
                200,
                200,
            ]
    app.state.database.engine.dispose()


def test_content_mutation_exception_releases_process_and_file_fences(
    tmp_path: Path,
) -> None:
    settings = _prepared_settings(tmp_path)
    app = create_app(settings)

    @app.post("/test/failing-content-mutation")
    async def failing_content_mutation():
        raise RuntimeError("controlled mutation failure")

    @app.post("/test/successful-content-mutation")
    async def successful_content_mutation():
        return {"ok": True}

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.post("/test/failing-content-mutation").status_code == 500
        assert client.post("/test/successful-content-mutation").status_code == 200
    app.state.database.engine.dispose()


def test_restore_uses_fresh_paths_migrates_checks_fts_and_locks_online_budget(
    tmp_path: Path,
) -> None:
    settings = _prepared_settings(tmp_path)
    snapshot = tmp_path / "snapshot"
    create_consistent_snapshot(settings=settings, snapshot_dir=snapshot)
    destination = tmp_path / "restore"
    database = destination / "content.db"
    media = destination / "media"
    runtime = destination / "runtime.db"
    report = restore_to_fresh_target(
        settings=settings,
        snapshot_dir=snapshot,
        destination_database=database,
        destination_media=media,
        destination_runtime=runtime,
        restored_at=datetime(2026, 8, 30, 10, 0, tzinfo=UTC),
    )
    assert database.is_file()
    assert runtime.is_file()
    assert list(media.rglob("image.webp"))
    assert report["integrity"]["quick_check"] == "ok"
    assert report["runtime_created_empty"] is True
    assert report["qdrant_recovery_required"] is True
    assert report["readiness_receipt_required"] is True
    assert report["public_switches_enabled"] is False
    assert report["online_locked_until"] == "2026-08-30T16:00:00+00:00"
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT blocked_beijing_date FROM assistant_budget_policy WHERE id=1"
        ).fetchone()[0] == "2026-08-30"
    with pytest.raises(BackupRestoreError, match="fresh and empty"):
        restore_to_fresh_target(
            settings=settings,
            snapshot_dir=snapshot,
            destination_database=database,
            destination_media=media,
            destination_runtime=runtime,
        )


def test_restore_previous_schema_creates_shared_budget_and_keeps_restore_lock(tmp_path):
    # Build the previous schema with Alembic instead of deleting two tables from
    # the current schema. A synthetic downgrade keeps tables that never existed
    # before the shared budget authority (for example admin_credentials) and
    # fails with a duplicate CREATE TABLE, which never exercised the real
    # upgrade path.
    previous_revision = "20260907_0024"
    settings = _prepared_settings(tmp_path, revision=previous_revision)
    with sqlite3.connect(tmp_path / "live" / "content.db") as connection:
        assert [
            str(row[0])
            for row in connection.execute("SELECT version_num FROM alembic_version")
        ] == [previous_revision]
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert "assistant_budget_policy" not in tables
    assert "assistant_budget_reservations" not in tables
    assert "admin_credentials" not in tables
    snapshot = tmp_path / "legacy-snapshot"
    manifest = create_consistent_snapshot(settings=settings, snapshot_dir=snapshot)
    assert manifest["content_database"]["alembic_versions"] == [previous_revision]
    destination = tmp_path / "legacy-restore"
    restore_to_fresh_target(
        settings=settings, snapshot_dir=snapshot,
        destination_database=destination / "content.db",
        destination_media=destination / "media",
        destination_runtime=destination / "runtime.db",
        restored_at=datetime(2026, 9, 10, 10, 0, tzinfo=UTC),
    )
    with sqlite3.connect(destination / "content.db") as connection:
        assert connection.execute(
            "SELECT blocked_beijing_date FROM assistant_budget_policy WHERE id=1"
        ).fetchone()[0] == "2026-09-10"
        assert connection.execute(
            "SELECT COUNT(*) FROM assistant_budget_reservations"
        ).fetchone()[0] == 0
