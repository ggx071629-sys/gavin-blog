"""Isolated HTTP account fixture: fake mailbox only, never loads local secrets."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config

api_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(api_root))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    for key in list(os.environ):
        if key.upper().startswith("GAVIN_"):
            del os.environ[key]
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        environment="test",
        database_url="sqlite:///" + (root / "account.db").as_posix(),
        admin_username="gavin",
        admin_password="correct-horse",
        cookie_secure=False,
        media_root=str(root / "media"),
        admin_email="fixture@example.invalid",
        smtp_username="fixture@example.invalid",
        smtp_password="fixture-only",
        account_code_secret="fixture-only-independent-secret-at-least-32",
        _env_file=None,
    )
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    config.attributes["database_url"] = settings.database_url
    command.upgrade(config, "head")
    app = create_app(settings)

    def sender(_settings, code: str, purpose: str) -> None:
        (root / f"{purpose}.json").write_text(json.dumps({"code": code}), encoding="utf-8")

    app.state.account_sender = sender
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
