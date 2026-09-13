from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .errors import not_ready
from .runtime_db import open_control
from .runtime_schema import META_ONLINE_LOCKED_UNTIL, write_meta
from .time_beijing import next_beijing_midnight


def mark_restored_empty_runtime(runtime_path: Path, now: datetime) -> str:
    """Lock Chat/query/session until the next Beijing midnight after a lost runtime."""
    control = open_control(runtime_path=runtime_path, owner="provision", verify=True)
    try:
        until = next_beijing_midnight(now).isoformat()
        write_meta(control.engine, META_ONLINE_LOCKED_UNTIL, until)
        return until
    finally:
        control.dispose()


def online_lock_until(conn) -> datetime | None:
    raw = None
    row = conn.execute(
        "SELECT value FROM assistant_runtime_meta WHERE key = ?",
        (META_ONLINE_LOCKED_UNTIL,),
    ).fetchone()
    if row is not None:
        raw = row["value"] if hasattr(row, "keys") else row[0]
    if not raw:
        return None
    return datetime.fromisoformat(str(raw))


def raise_if_restore_locked(online, now: datetime) -> None:
    until = online.control.read(lambda conn: online_lock_until(conn))
    if until is not None and now < until:
        raise not_ready()
