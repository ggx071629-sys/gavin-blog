from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

import uvicorn

api_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(api_root))

from app.config import Settings  # noqa: E402
from app.db import Base  # noqa: E402
from app.main import create_app  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an isolated API for Playwright")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--web-origin", default="http://127.0.0.1:3000")
    return parser.parse_args()


def build_app(run_root: Path, web_origin: str):
    settings = Settings(
        environment="test",
        database_url="sqlite:///" + (run_root / "e2e.db").as_posix(),
        admin_username="gavin",
        admin_password="correct-horse",
        cookie_secure=False,
        cors_origins=web_origin,
        media_root=str(run_root / "media"),
        _env_file=None,
    )
    app = create_app(settings)
    Base.metadata.create_all(app.state.database.engine)
    return app


if __name__ == "__main__":
    args = parse_args()
    configured_run_root = os.environ.get("GAVIN_E2E_RUN_ROOT")
    if configured_run_root:
        run_root = Path(configured_run_root)
        run_root.mkdir(parents=True, exist_ok=True)
        app = build_app(run_root, args.web_origin)
        uvicorn.run(app, host=args.host, port=args.port)
    else:
        with tempfile.TemporaryDirectory(
            prefix="gavin-e2e-",
            ignore_cleanup_errors=True,
        ) as temporary_directory:
            app = build_app(Path(temporary_directory), args.web_origin)
            uvicorn.run(app, host=args.host, port=args.port)
