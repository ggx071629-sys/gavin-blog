from __future__ import annotations

from typing import Any

from sqlalchemy import event

BUSY_TIMEOUT_MS = 5000


def apply_sqlite_pragmas(dbapi_connection: Any, *, foreign_keys: bool) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        cursor.execute("PRAGMA secure_delete=ON")
        cursor.execute("PRAGMA synchronous=FULL")
        cursor.execute("PRAGMA journal_mode=WAL")
        if foreign_keys:
            cursor.execute("PRAGMA foreign_keys=ON")
        _assert_pragmas(cursor, foreign_keys=foreign_keys)
    finally:
        cursor.close()


def _assert_pragmas(cursor: Any, *, foreign_keys: bool) -> None:
    timeout = cursor.execute("PRAGMA busy_timeout").fetchone()[0]
    secure = cursor.execute("PRAGMA secure_delete").fetchone()[0]
    sync = cursor.execute("PRAGMA synchronous").fetchone()[0]
    journal = str(cursor.execute("PRAGMA journal_mode").fetchone()[0]).lower()
    if int(timeout) != BUSY_TIMEOUT_MS:
        raise RuntimeError("assistant sqlite busy_timeout was not applied")
    if int(secure) != 1:
        raise RuntimeError("assistant sqlite secure_delete was not applied")
    if int(sync) != 2:
        raise RuntimeError("assistant sqlite synchronous=FULL was not applied")
    if journal != "wal":
        raise RuntimeError("assistant sqlite WAL was not applied")
    if foreign_keys:
        keys = cursor.execute("PRAGMA foreign_keys").fetchone()[0]
        if int(keys) != 1:
            raise RuntimeError("assistant sqlite foreign_keys was not applied")


async def apply_aiosqlite_pragmas(conn: Any, *, foreign_keys: bool = False) -> None:
    await conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    await conn.execute("PRAGMA secure_delete=ON")
    await conn.execute("PRAGMA synchronous=FULL")
    await conn.execute("PRAGMA journal_mode=WAL")
    if foreign_keys:
        await conn.execute("PRAGMA foreign_keys=ON")
    timeout = (await (await conn.execute("PRAGMA busy_timeout")).fetchone())[0]
    secure = (await (await conn.execute("PRAGMA secure_delete")).fetchone())[0]
    sync = (await (await conn.execute("PRAGMA synchronous")).fetchone())[0]
    journal = str((await (await conn.execute("PRAGMA journal_mode")).fetchone())[0]).lower()
    if int(timeout) != BUSY_TIMEOUT_MS or int(secure) != 1 or int(sync) != 2 or journal != "wal":
        raise RuntimeError("assistant saver sqlite pragmas were not applied")


def listen_control_connect(engine) -> None:
    def _on_connect(dbapi_connection: Any, _: Any) -> None:
        apply_sqlite_pragmas(dbapi_connection, foreign_keys=True)

    event.listen(engine, "connect", _on_connect)
