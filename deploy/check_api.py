"""Refuse an unmigrated volume, then exec exactly one API owner."""
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from alembic.config import Config
from alembic.script import ScriptDirectory
from app.config import Settings
from app.content_write_fence import content_database_path


def main() -> None:
    settings = Settings(_env_file=None)
    settings.validate_runtime()
    path = content_database_path(settings)
    expected = set(ScriptDirectory.from_config(Config("alembic.ini")).get_heads())
    try:
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            actual = {row[0] for row in db.execute("SELECT version_num FROM alembic_version")}
    except sqlite3.Error:
        raise SystemExit("Database is not initialized. Run: docker compose run --rm init") from None
    if actual != expected:
        raise SystemExit("Database revision mismatch. Stop writers, back up, then run the init service.")
    os.execvp("uvicorn", [
        "uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0",
        "--port", "8000", "--workers", "1", "--no-proxy-headers", "--no-access-log",
        "--timeout-graceful-shutdown", "45",
    ])


if __name__ == "__main__":
    main()
