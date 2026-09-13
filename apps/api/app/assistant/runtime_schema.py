from __future__ import annotations

import hashlib

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .constants import CONTROL_TABLES, SAVER_TABLES, SCHEMA_VERSION
from .errors import AssistantSchemaError

META_FINGERPRINT = "schema_fingerprint"
META_SCHEMA_VERSION = "schema_version"
META_SAVER_FINGERPRINT = "saver_fingerprint"
META_ONLINE_LOCKED_UNTIL = "online_locked_until"


def sqlite_master_fingerprint(engine: Engine) -> str:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT type, name, sql FROM sqlite_master "
                "WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' "
                "ORDER BY type, name"
            )
        ).fetchall()
    payload = "\n".join(f"{row[0]}|{row[1]}|{row[2]}" for row in rows)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def table_names(engine: Engine) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        ).fetchall()
    return {str(row[0]) for row in rows}


def assert_allowlist(engine: Engine) -> None:
    names = table_names(engine)
    unexpected = names - CONTROL_TABLES - SAVER_TABLES
    missing_control = CONTROL_TABLES - names
    if unexpected:
        raise AssistantSchemaError(f"unexpected assistant_runtime tables: {sorted(unexpected)}")
    if missing_control:
        raise AssistantSchemaError(
            f"missing assistant_runtime control tables: {sorted(missing_control)}"
        )


def read_meta(engine: Engine, key: str) -> str | None:
    with engine.connect() as conn:
        value = conn.execute(
            text("SELECT value FROM assistant_runtime_meta WHERE key = :key"),
            {"key": key},
        ).scalar()
    return str(value) if value is not None else None


def write_meta(engine: Engine, key: str, value: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO assistant_runtime_meta(key, value) VALUES (:key, :value) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
            ),
            {"key": key, "value": value},
        )


def verify_provisioned_schema(engine: Engine) -> str:
    names = table_names(engine)
    if not names:
        raise AssistantSchemaError("assistant_runtime schema is missing")
    try:
        assert_allowlist(engine)
    except AssistantSchemaError:
        raise
    fingerprint = sqlite_master_fingerprint(engine)
    stored = read_meta(engine, META_FINGERPRINT)
    version = read_meta(engine, META_SCHEMA_VERSION)
    if stored is None or version is None:
        raise AssistantSchemaError("assistant_runtime schema fingerprint is missing")
    if version != SCHEMA_VERSION:
        raise AssistantSchemaError("assistant_runtime schema version mismatch")
    if stored != fingerprint:
        raise AssistantSchemaError("assistant_runtime schema fingerprint mismatch")
    return fingerprint


def persist_fingerprint(engine: Engine) -> str:
    assert_allowlist(engine)
    fingerprint = sqlite_master_fingerprint(engine)
    write_meta(engine, META_FINGERPRINT, fingerprint)
    write_meta(engine, META_SCHEMA_VERSION, SCHEMA_VERSION)
    return fingerprint
