from __future__ import annotations

import json
from pathlib import Path

from app.config import Settings
from app.main import create_app

app = create_app(
    Settings(
        environment="test",
        database_url="sqlite:///:memory:",
        admin_password="openapi-contract-only",
        cookie_secure=False,
        cors_origins="",
        media_root=".",
        _env_file=None,
    )
)

target = Path(__file__).resolve().parents[3] / "packages" / "contracts" / "openapi.json"
target.parent.mkdir(parents=True, exist_ok=True)
with target.open("w", encoding="utf-8", newline="\n") as handle:
    handle.write(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n")
print(target)
