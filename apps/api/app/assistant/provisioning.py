from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import aiosqlite
from alembic import command
from alembic.config import Config
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from ..config import Settings, get_settings
from .constants import SAVER_TABLES, SCHEMA_VERSION
from .errors import AssistantOwnerLockError, AssistantSchemaError
from .owner_lock import ExclusiveFileLock
from .pragmas import apply_aiosqlite_pragmas
from .runtime_db import acquire_owner_lock, sqlite_url
from .runtime_schema import (
    META_SAVER_FINGERPRINT,
    persist_fingerprint,
    sqlite_master_fingerprint,
    table_names,
    write_meta,
)

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "assistant_runtime_alembic.ini"


def runtime_alembic_config(runtime_path: Path) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", sqlite_url(runtime_path))
    config.set_main_option(
        "script_location", str(ALEMBIC_INI.parent / "assistant_runtime_migrations")
    )
    return config


async def setup_saver_schema(runtime_path: Path) -> None:
    conn = await aiosqlite.connect(runtime_path.as_posix())
    try:
        await apply_aiosqlite_pragmas(conn, foreign_keys=False)
        saver = AsyncSqliteSaver(conn)
        await saver.setup()
        await conn.commit()
    finally:
        await conn.close()


def _assert_saver_tables(runtime_path: Path) -> None:
    from sqlalchemy import create_engine

    engine = create_engine(sqlite_url(runtime_path))
    try:
        names = table_names(engine)
        missing = SAVER_TABLES - names
        if missing:
            raise AssistantSchemaError(f"saver tables missing after setup: {sorted(missing)}")
        extra_saver = (names & SAVER_TABLES) - SAVER_TABLES
        if extra_saver:
            raise AssistantSchemaError(f"unexpected saver tables: {sorted(extra_saver)}")
    finally:
        engine.dispose()


def provision_runtime(settings: Settings, *, lock: ExclusiveFileLock | None = None) -> str:
    if not settings.assistant_runtime_path:
        raise AssistantSchemaError("assistant_runtime_path is required to provision")
    runtime_path = Path(settings.assistant_runtime_path)
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    owned = lock is None
    owner = lock or acquire_owner_lock(runtime_path)
    try:
        before = None
        if runtime_path.exists():
            from sqlalchemy import create_engine

            engine = create_engine(sqlite_url(runtime_path))
            try:
                before = table_names(engine)
            finally:
                engine.dispose()
        command.upgrade(runtime_alembic_config(runtime_path), "head")
        asyncio.run(setup_saver_schema(runtime_path))
        _assert_saver_tables(runtime_path)
        from sqlalchemy import create_engine

        engine = create_engine(sqlite_url(runtime_path))
        try:
            after = table_names(engine)
            if before is not None:
                created = after - before
                if created & SAVER_TABLES and any(
                    name not in SAVER_TABLES and name != "assistant_control_alembic_version"
                    for name in created
                ):
                    # Control migrations must not create saver tables; saver setup
                    # may add checkpoints/writes only.
                    if "checkpoints" in before or "writes" in before:
                        pass
            fingerprint = persist_fingerprint(engine)
            write_meta(engine, META_SAVER_FINGERPRINT, sqlite_master_fingerprint(engine))
            stored = sqlite_master_fingerprint(engine)
            if stored != fingerprint:
                raise AssistantSchemaError("provisioned schema fingerprint failed recheck")
            return fingerprint
        finally:
            engine.dispose()
    finally:
        if owned:
            owner.release()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Provision assistant_runtime control and saver schema"
    )
    parser.parse_args(argv)
    settings = get_settings()
    if not settings.assistant_runtime_path:
        raise SystemExit("GAVIN_ASSISTANT_RUNTIME_PATH is required")
    try:
        fingerprint = provision_runtime(settings)
    except AssistantOwnerLockError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"assistant_runtime provisioned schema={SCHEMA_VERSION} fingerprint={fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
