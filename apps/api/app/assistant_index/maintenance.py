"""Read-only audit or explicit, backed-up repair of the active FTS projection."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from sqlalchemy import select, text

from ..config import Settings
from ..content_write_fence import content_database_path, content_write_fence
from ..db import Database
from ..models import AssistantChunk
from .fts import delete_fts_ids, upsert_chunk_fts
from .integrity import IndexIntegrityError, active_generation, audit_generation
from .runtime import build_runtime


def backup_content(settings, destination: Path) -> None:
    source = content_database_path(settings)
    if destination.resolve() == source:
        raise ValueError("backup must be a new file")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Never overwrite an existing backup or database, including a symlink target.
    with destination.open("xb"):
        pass
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as src:
        with sqlite3.connect(destination) as dest:
            src.backup(dest)
            if dest.execute("PRAGMA quick_check").fetchone() != ("ok",):
                raise RuntimeError("backup integrity check failed")


def repair_active_fts(runtime, *, generation_id: int, backup: Path) -> dict:
    with content_write_fence(runtime.settings):
        # The fence excludes API/worker writes throughout backup and repair.
        backup_content(runtime.settings, backup)
        with runtime.database.session_factory() as db:
            db.execute(text("BEGIN IMMEDIATE"))
            generation = active_generation(db)
            if generation.id != generation_id:
                raise RuntimeError("active generation changed; repair refused")
            before = audit_generation(db, runtime, generation)
            if any(i["layer"] != "fts" or i["code"] == "unavailable" for i in before.issues):
                raise IndexIntegrityError(before)
            affected = {i["identity"] for i in before.issues}
            for chunk_id in sorted(affected):
                chunk = db.scalar(select(AssistantChunk).where(
                    AssistantChunk.generation_id == generation.id,
                    AssistantChunk.chunk_id == chunk_id,
                ))
                if chunk is None:
                    delete_fts_ids(db, [chunk_id], generation_id=generation.id)
                else:
                    upsert_chunk_fts(db, chunk)
            after = audit_generation(db, runtime, generation)
            after.require_passed()
            db.commit()
            return {"before": before.as_dict(), "after": after.as_dict(),
                    "changed_chunk_ids": sorted(affected), "backup": str(backup)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env.e5")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("audit")
    repair = sub.add_parser("repair-fts")
    repair.add_argument("--generation", type=int, required=True)
    repair.add_argument("--backup", type=Path, required=True)
    args = parser.parse_args(argv)
    runtime = None
    database = None
    try:
        settings = Settings(_env_file=args.env_file)
        if not content_database_path(settings).is_file():
            raise ValueError("existing content database required")
        database = Database(settings.database_url)
        runtime = build_runtime(settings, database)
        if args.command == "repair-fts":
            result = repair_active_fts(
                runtime, generation_id=args.generation, backup=args.backup,
            )
            passed = True
        else:
            with content_write_fence(settings), database.session_factory() as db:
                db.execute(text("BEGIN"))
                report = audit_generation(db, runtime, active_generation(db))
            result, passed = report.as_dict(), report.passed
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if passed else 1
    except IndexIntegrityError as exc:
        print(json.dumps(exc.report.as_dict(), ensure_ascii=False, sort_keys=True))
        return 1
    except Exception as exc:
        # Settings/transport errors can contain secrets; expose only a safe class.
        print(json.dumps({"status": "failed", "error": type(exc).__name__}))
        return 1
    finally:
        if runtime is not None:
            runtime.store.client.close()
        if database is not None:
            database.engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
