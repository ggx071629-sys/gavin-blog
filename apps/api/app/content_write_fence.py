from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import make_url

from .assistant.owner_lock import ExclusiveFileLock
from .config import Settings


def content_database_path(settings: Settings) -> Path:
    url = make_url(settings.database_url)
    if url.drivername != "sqlite" or not url.database or url.database == ":memory:":
        raise RuntimeError("content backup fencing requires a file-backed SQLite database")
    path = Path(url.database)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def content_write_fence_path(settings: Settings) -> Path:
    configured = str(settings.content_write_fence_path or "").strip()
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            raise RuntimeError("content_write_fence_path must be absolute")
        return path.resolve()
    database = content_database_path(settings)
    return database.with_name(database.name + ".write-fence.lock")


def content_write_fence(settings: Settings) -> ExclusiveFileLock:
    return ExclusiveFileLock(content_write_fence_path(settings))
