"""Explicit offline initialization; stop API/Worker before running on existing data."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd()))

from alembic import command
from alembic.config import Config
from app.config import Settings
from app.content_write_fence import content_write_fence
from app.assistant.provisioning import provision_runtime


def initialize() -> None:
    settings = Settings(_env_file=None)
    # Offline schema provisioning must not attempt provider/readiness admission.
    settings = settings.model_copy(update={
        "assistant_online_enabled": False,
        "assistant_index_worker_enabled": False,
    })
    settings.validate_runtime()
    for directory in ("/data/content", "/data/media", "/data/runtime"):
        Path(directory).mkdir(parents=True, exist_ok=True)
    with content_write_fence(settings):
        config = Config("alembic.ini")
        config.attributes["database_url"] = settings.database_url
        command.upgrade(config, "head")
        provision_runtime(settings)
    print("Content and assistant runtime schemas initialized; public assistant remains disabled.")


if __name__ == "__main__":
    initialize()
