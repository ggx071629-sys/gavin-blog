from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config

from ..assistant.backup import content_backup_includes, runtime_backup_excludes
from ..assistant.provisioning import provision_runtime
from ..assistant.recovery import mark_restored_empty_runtime
from ..config import Settings
from ..content_write_fence import content_database_path, content_write_fence

SNAPSHOT_SCHEMA_VERSION = 1
SNAPSHOT_MANIFEST = "snapshot-manifest.json"


class BackupRestoreError(RuntimeError):
    """A consistency, integrity, isolation, or restore invariant failed."""


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            value.update(chunk)
    return "sha256:" + value.hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupRestoreError("snapshot manifest is unreadable") from exc
    if not isinstance(payload, dict):
        raise BackupRestoreError("snapshot manifest root must be an object")
    return payload


def _sqlite_integrity(connection: sqlite3.Connection) -> dict[str, Any]:
    quick = [str(row[0]) for row in connection.execute("PRAGMA quick_check")]
    foreign = connection.execute("PRAGMA foreign_key_check").fetchall()
    if quick != ["ok"] or foreign:
        raise BackupRestoreError("SQLite integrity or foreign-key validation failed")
    fts_tables = [
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND lower(sql) LIKE '%using fts5%' ORDER BY name"
        )
    ]
    for table in fts_tables:
        if not table.replace("_", "").isalnum():
            raise BackupRestoreError("FTS table name is unsafe")
        connection.execute(f'INSERT INTO "{table}"("{table}") VALUES (\'integrity-check\')')
    return {
        "quick_check": "ok",
        "foreign_key_violations": 0,
        "fts5_tables_checked": fts_tables,
    }


def _schema_facts(connection: sqlite3.Connection) -> dict[str, Any]:
    tables = {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
        )
    }
    if "alembic_version" not in tables:
        raise BackupRestoreError("content database has no Alembic version")
    versions = [
        str(row[0])
        for row in connection.execute(
            "SELECT version_num FROM alembic_version ORDER BY version_num"
        )
    ]
    if not versions:
        raise BackupRestoreError("content database Alembic version is empty")
    required = set(content_backup_includes())
    # The immediately preceding schema predates the common budget authority.
    # Verify its original table set, then migrate before admitting a restored DB.
    if versions == ["20260907_0024"]:
        required -= {"assistant_budget_policy", "assistant_budget_reservations"}
    missing = sorted(required - tables)
    if missing:
        raise BackupRestoreError("content database is missing backup tables: " + ", ".join(missing))
    counts = {
        table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        for table in sorted(required)
    }
    return {"table_counts": counts, "alembic_versions": versions}


def _expected_media(connection: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    expected: dict[str, dict[str, Any]] = {}
    rows = connection.execute(
        "SELECT id, storage_key, variants_json FROM media_assets "
        "WHERE source = 'upload' ORDER BY id"
    ).fetchall()
    for asset_id, storage_key, variants_json in rows:
        if not isinstance(storage_key, str) or len(storage_key) != 32 or not storage_key.isalnum():
            raise BackupRestoreError(f"media asset {asset_id} has an invalid storage key")
        try:
            variants = json.loads(str(variants_json))
        except json.JSONDecodeError as exc:
            raise BackupRestoreError(f"media asset {asset_id} variants are invalid") from exc
        if not isinstance(variants, list) or not variants:
            raise BackupRestoreError(f"media asset {asset_id} has no stored variants")
        for variant in variants:
            image_format = variant.get("format") if isinstance(variant, dict) else None
            if not isinstance(image_format, str) or not image_format.isalnum():
                raise BackupRestoreError(f"media asset {asset_id} variant is invalid")
            relative = f"{storage_key}/image.{image_format}"
            if relative in expected:
                raise BackupRestoreError("media manifest contains a duplicate path")
            expected[relative] = {"asset_id": int(asset_id), "format": image_format}
    return expected


def _copy_media(
    source_root: Path,
    destination_root: Path,
    connection: sqlite3.Connection,
) -> tuple[list[dict[str, Any]], int]:
    expected = _expected_media(connection)
    actual: dict[str, Path] = {}
    if source_root.exists():
        for path in source_root.rglob("*"):
            if path.is_symlink():
                raise BackupRestoreError("media backup refuses symbolic links")
            if not path.is_file():
                continue
            relative = path.relative_to(source_root).as_posix()
            if any(part.startswith(".") for part in Path(relative).parts):
                raise BackupRestoreError("media staging residue exists during backup")
            actual[relative] = path
    missing = sorted(set(expected) - set(actual))
    orphaned = sorted(set(actual) - set(expected))
    if missing or orphaned:
        raise BackupRestoreError(
            f"database/media manifest mismatch: missing={missing}; orphaned={orphaned}"
        )
    files = []
    total_bytes = 0
    for relative in sorted(expected):
        source = actual[relative]
        destination = destination_root.joinpath(*relative.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        source_hash = _digest(source)
        destination_hash = _digest(destination)
        if source_hash != destination_hash:
            raise BackupRestoreError("media copy hash changed during the fenced snapshot")
        size = destination.stat().st_size
        total_bytes += size
        files.append(
            {
                "path": relative,
                "sha256": destination_hash,
                "byte_size": size,
                **expected[relative],
            }
        )
    return files, total_bytes


def create_consistent_snapshot(
    *,
    settings: Settings,
    snapshot_dir: Path,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    source_database = content_database_path(settings)
    source_media = Path(settings.media_root).resolve()
    destination = snapshot_dir.resolve()
    if not source_database.is_file():
        raise BackupRestoreError("content SQLite database is missing")
    if destination.exists():
        raise BackupRestoreError("snapshot destination already exists")
    if destination == source_media or destination.is_relative_to(source_media):
        raise BackupRestoreError("snapshot destination cannot be inside the live media root")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    temporary.mkdir()
    lock = content_write_fence(settings)
    try:
        lock.acquire()
        backup_database = temporary / "content.sqlite3"
        with sqlite3.connect(source_database) as source, sqlite3.connect(backup_database) as backup:
            source.backup(backup)
        with sqlite3.connect(backup_database) as backup:
            integrity = _sqlite_integrity(backup)
            schema = _schema_facts(backup)
            media_files, media_bytes = _copy_media(
                source_media,
                temporary / "media",
                backup,
            )
        manifest: dict[str, Any] = {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "created_at": (created_at or datetime.now(UTC)).astimezone(UTC).isoformat(),
            "consistency_strategy": "write-fence-and-online-backup",
            "content_database": {
                "path": "content.sqlite3",
                "sha256": _digest(backup_database),
                "byte_size": backup_database.stat().st_size,
                **integrity,
                **schema,
            },
            "media": {
                "root": "media",
                "asset_count": len({item["asset_id"] for item in media_files}),
                "file_count": len(media_files),
                "byte_size": media_bytes,
                "files": media_files,
            },
            "exclusions": {
                "assistant_runtime": True,
                "wal_shm": True,
                "langgraph_checkpoints_writes": True,
                "runtime_names": list(runtime_backup_excludes()),
            },
            "encrypted_off_host_receipt_included": False,
        }
        destination.mkdir()
        shutil.copy2(backup_database, destination / "content.sqlite3")
        shutil.copytree(temporary / "media", destination / "media")
        if _digest(destination / "content.sqlite3") != manifest["content_database"]["sha256"]:
            raise BackupRestoreError("published snapshot database hash changed")
        _atomic_json(destination / SNAPSHOT_MANIFEST, manifest)
        return manifest
    except (OSError, sqlite3.Error, ValueError) as exc:
        if isinstance(exc, BackupRestoreError):
            raise
        raise BackupRestoreError("consistent snapshot failed") from exc
    finally:
        lock.release()
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
        if destination.exists() and not (destination / SNAPSHOT_MANIFEST).is_file():
            shutil.rmtree(destination, ignore_errors=True)


def verify_snapshot(snapshot_dir: Path) -> dict[str, Any]:
    root = snapshot_dir.resolve()
    manifest = _read_json(root / SNAPSHOT_MANIFEST)
    if set(manifest) != {
        "schema_version",
        "created_at",
        "consistency_strategy",
        "content_database",
        "media",
        "exclusions",
        "encrypted_off_host_receipt_included",
    }:
        raise BackupRestoreError("snapshot manifest fields are invalid")
    if manifest["schema_version"] != SNAPSHOT_SCHEMA_VERSION:
        raise BackupRestoreError("snapshot manifest schema is unsupported")
    if manifest["consistency_strategy"] != "write-fence-and-online-backup":
        raise BackupRestoreError("snapshot consistency strategy is invalid")
    if manifest["encrypted_off_host_receipt_included"] is not False:
        raise BackupRestoreError("local snapshot cannot claim an off-host encryption receipt")
    database = root / str(manifest["content_database"].get("path"))
    if not database.is_file() or _digest(database) != manifest["content_database"].get("sha256"):
        raise BackupRestoreError("snapshot content database hash is invalid")
    with sqlite3.connect(database) as connection:
        _sqlite_integrity(connection)
        _schema_facts(connection)
        expected = _expected_media(connection)
    recorded_files = manifest["media"].get("files")
    if not isinstance(recorded_files, list):
        raise BackupRestoreError("snapshot media files are invalid")
    observed: set[str] = set()
    total = 0
    for item in recorded_files:
        if not isinstance(item, dict) or set(item) != {
            "path",
            "sha256",
            "byte_size",
            "asset_id",
            "format",
        }:
            raise BackupRestoreError("snapshot media record is invalid")
        relative = item["path"]
        if not isinstance(relative, str) or relative in observed or relative not in expected:
            raise BackupRestoreError("snapshot media record path is invalid")
        path = root / "media" / Path(relative)
        if not path.is_file() or path.is_symlink() or _digest(path) != item["sha256"]:
            raise BackupRestoreError("snapshot media hash is invalid")
        if path.stat().st_size != item["byte_size"]:
            raise BackupRestoreError("snapshot media size is invalid")
        observed.add(relative)
        total += path.stat().st_size
    if observed != set(expected):
        raise BackupRestoreError("snapshot media records do not match the database")
    if (
        manifest["media"].get("file_count") != len(observed)
        or manifest["media"].get("byte_size") != total
    ):
        raise BackupRestoreError("snapshot media summary is invalid")
    return manifest


def _content_alembic_config(database_path: Path) -> Config:
    api_root = Path(__file__).resolve().parents[2]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    config.set_main_option("script_location", str(api_root / "migrations"))
    config.attributes["database_url"] = f"sqlite:///{database_path.as_posix()}"
    return config


def restore_to_fresh_target(
    *,
    settings: Settings,
    snapshot_dir: Path,
    destination_database: Path,
    destination_media: Path,
    destination_runtime: Path,
    restored_at: datetime | None = None,
) -> dict[str, Any]:
    manifest = verify_snapshot(snapshot_dir)
    database = destination_database.resolve()
    media = destination_media.resolve()
    runtime = destination_runtime.resolve()
    for path in (database, media, runtime):
        if path.exists():
            raise BackupRestoreError("restore destination must be fresh and empty")
    live_paths = {
        content_database_path(settings),
        Path(settings.media_root).resolve(),
        Path(str(settings.assistant_runtime_path or "__missing_runtime__")).resolve(),
    }
    if any(path in live_paths for path in (database, media, runtime)):
        raise BackupRestoreError("restore refuses to overwrite a live candidate path")
    database.parent.mkdir(parents=True, exist_ok=True)
    media.parent.mkdir(parents=True, exist_ok=True)
    database_tmp = database.with_name(f".{database.name}.{uuid.uuid4().hex}.tmp")
    media_tmp = media.with_name(f".{media.name}.{uuid.uuid4().hex}.tmp")
    try:
        shutil.copy2(snapshot_dir / "content.sqlite3", database_tmp)
        shutil.copytree(snapshot_dir / "media", media_tmp)
        database_tmp.replace(database)
        media_tmp.replace(media)
        command.upgrade(_content_alembic_config(database), "head")
        with sqlite3.connect(database) as connection:
            from ..assistant.time_beijing import beijing_date
            from ..assistant.total_budget import ceiling

            # Worker shares this authority but must never open the restored runtime.
            blocked_day = beijing_date(restored_at or datetime.now(UTC)).isoformat()
            connection.execute(
                "INSERT INTO assistant_budget_policy"
                "(id,cap_micro_cny,version,blocked_beijing_date) "
                "VALUES(1,?,1,?) ON CONFLICT(id) DO UPDATE SET "
                "blocked_beijing_date=excluded.blocked_beijing_date,version=version+1",
                (ceiling(settings), blocked_day),
            )
            connection.commit()
            integrity = _sqlite_integrity(connection)
            schema = _schema_facts(connection)
        restored_settings = settings.model_copy(
            update={
                "database_url": f"sqlite:///{database.as_posix()}",
                "media_root": str(media),
                "assistant_runtime_path": str(runtime),
                "assistant_online_enabled": False,
                "assistant_index_worker_enabled": False,
            }
        )
        provision_runtime(restored_settings)
        lock_until = mark_restored_empty_runtime(
            runtime,
            (restored_at or datetime.now(UTC)).astimezone(UTC),
        )
        report = {
            "schema_version": 1,
            "restored_at": (restored_at or datetime.now(UTC)).astimezone(UTC).isoformat(),
            "source_snapshot_sha256": _digest(snapshot_dir / SNAPSHOT_MANIFEST),
            "content_database_sha256": _digest(database),
            "media_file_count": manifest["media"]["file_count"],
            "integrity": integrity,
            "schema": schema,
            "runtime_created_empty": True,
            "online_locked_until": lock_until,
            "qdrant_recovery_required": True,
            "readiness_receipt_required": True,
            "public_switches_enabled": False,
        }
        return report
    except (OSError, sqlite3.Error, ValueError) as exc:
        if isinstance(exc, BackupRestoreError):
            raise
        raise BackupRestoreError("fresh-target restore failed") from exc
    finally:
        database_tmp.unlink(missing_ok=True)
        if media_tmp.exists():
            shutil.rmtree(media_tmp, ignore_errors=True)
