"""Offline owner operation: stop API first, validate probe, finalize, sign readiness.

This never enables the operational gate and never calls Chat. Enable explicitly
from the authenticated administration UI after starting API and checking status.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, "/app")

from app.assistant.admin_operations import finalize_rebuild
from app.assistant.readiness import write_receipt
from app.assistant.runtime import start_assistant_online, stop_assistant_online
from app.assistant_qualification.profile import load_profile
from app.assistant_qualification.provider_probe import validate_provider_probe_artifact
from app.config import Settings
from app.db import Database
from app.models import AssistantIndexCommand


async def run(args) -> None:
    settings = Settings(_env_file=None)
    settings.validate_runtime()
    if settings.environment != "production" or not settings.assistant_online_enabled:
        raise RuntimeError("requires the explicit production assistant configuration")
    profile_path = Path(str(settings.assistant_qualification_profile_path))
    validate_provider_probe_artifact(args.probe, load_profile(profile_path), settings)
    database = Database(settings.database_url)
    online = await start_assistant_online(settings, database)
    try:
        if args.operation:
            if args.version is None:
                raise RuntimeError("--operation requires the observed --version")
            finalize_rebuild(
                online, operation_id=args.operation, expected_version=args.version,
                idempotency_key=f"deployment-finalize-{args.operation}",
            )
        receipt = write_receipt(
            settings, probe_live=True, lock=online.lock,
            qualification_profile=profile_path, provider_probe=args.probe,
        )
        print(f"Readiness receipt created: {receipt}. Operational gate remains unchanged.")
    finally:
        await stop_assistant_online(online)
        database.engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path)
    parser.add_argument("--list-rebuilds", action="store_true")
    parser.add_argument("--operation")
    parser.add_argument("--version", type=int)
    args = parser.parse_args()
    if args.list_rebuilds:
        import json

        settings = Settings(_env_file=None)
        settings.validate_runtime()
        database = Database(settings.database_url)
        with database.session_factory() as db:
            rows = db.execute(select(
                AssistantIndexCommand.id, AssistantIndexCommand.version,
                AssistantIndexCommand.status, AssistantIndexCommand.generation_id,
            ).order_by(AssistantIndexCommand.created_at.desc()).limit(10)).mappings().all()
            print(json.dumps([dict(row) for row in rows]))
        database.engine.dispose()
    else:
        if args.probe is None:
            parser.error("--probe is required for readiness; use --list-rebuilds to inspect")
        asyncio.run(run(args))
