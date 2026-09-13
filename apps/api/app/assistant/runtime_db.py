from __future__ import annotations

import logging
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from .constants import BUSY_RETRY_LIMIT
from .errors import AssistantOwnerLockError, AssistantSchemaError
from .owner_lock import ExclusiveFileLock, lock_path_for
from .pragmas import BUSY_TIMEOUT_MS, apply_sqlite_pragmas, listen_control_connect
from .runtime_schema import verify_provisioned_schema

T = TypeVar("T")


def sqlite_url(path: Path) -> str:
    return "sqlite:///" + path.resolve().as_posix()


def connect_control(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(
        path.as_posix(),
        timeout=max(15.0, BUSY_TIMEOUT_MS / 1000),
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    apply_sqlite_pragmas(conn, foreign_keys=True)
    return conn


class RuntimeControl:
    """Application-owned control plane for assistant_runtime. Never used by the index Worker."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.after_commit: Callable[[sqlite3.Connection], None] | None = None
        self.engine = create_engine(
            sqlite_url(path),
            connect_args={"check_same_thread": False, "timeout": BUSY_TIMEOUT_MS / 1000},
            poolclass=NullPool,
        )
        listen_control_connect(self.engine)
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )

    def session(self) -> Session:
        return self.session_factory()

    def read(self, fn: Callable[[sqlite3.Connection], T]) -> T:
        conn = connect_control(self.path)
        try:
            return fn(conn)
        finally:
            conn.close()

    def immediate(
        self, fn: Callable[[sqlite3.Connection], T], *, retries: int = BUSY_RETRY_LIMIT
    ) -> T:
        delay = 0.02
        last: Exception | None = None
        for _ in range(retries):
            conn = connect_control(self.path)
            try:
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    result = fn(conn)
                    conn.commit()
                    if self.after_commit is not None:
                        try:
                            self.after_commit(conn)
                        except Exception:
                            logging.getLogger(__name__).exception(
                                "budget settlement deferred; reservation retained"
                            )
                    return result
                except sqlite3.OperationalError as exc:
                    conn.rollback()
                    last = exc
                    if "busy" in str(exc).lower() or "locked" in str(exc).lower():
                        time.sleep(delay)
                        delay = min(delay * 2, 0.25)
                        continue
                    raise
            finally:
                conn.close()
        assert last is not None
        raise last

    def dispose(self) -> None:
        self.engine.dispose()


def assert_not_worker_owner(owner: str) -> None:
    if owner not in {"api", "provision"}:
        raise AssistantOwnerLockError("non-owner process cannot open assistant_runtime")


def open_control(*, runtime_path: Path, owner: str, verify: bool = True) -> RuntimeControl:
    assert_not_worker_owner(owner)
    control = RuntimeControl(runtime_path)
    if verify:
        try:
            verify_provisioned_schema(control.engine)
        except AssistantSchemaError:
            control.dispose()
            raise
    return control


def acquire_owner_lock(runtime_path: Path) -> ExclusiveFileLock:
    lock = ExclusiveFileLock(lock_path_for(runtime_path))
    lock.acquire()
    return lock
