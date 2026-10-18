"""Machine-local authenticated run journal. No repository JSON is a trust root."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .config import project_root


class StoreError(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def store_root() -> Path:
    identity = hashlib.sha256(str(project_root().resolve()).encode()).hexdigest()
    return Path(tempfile.gettempdir()) / "gavin-harness-runs" / identity


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


@contextmanager
def repository_lock() -> Iterator[None]:
    root = store_root()
    root.mkdir(parents=True, exist_ok=True)
    with (root / "operation.lock").open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise StoreError(
                "another verify/close holds the repository lock"
            ) from error
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class RunStore:
    def __init__(self, task_id: str) -> None:
        from .summarizer import validate_task_id

        validate_task_id(task_id)
        self.task_id = task_id
        self.root = store_root()
        self.path = self.root / f"{task_id}.json"

    def key(self, *, create: bool = False) -> bytes:
        path = self.root / "authentication.key"
        if create and not path.exists():
            self.root.mkdir(parents=True, exist_ok=True)
            # A lost key never authenticates old records. Fresh execution can replace them.
            with path.open("xb") as handle:
                os.chmod(path, 0o600)
                handle.write(secrets.token_bytes(32))
                handle.flush()
                os.fsync(handle.fileno())
        try:
            key = path.read_bytes()
        except OSError as error:
            raise StoreError(
                "local authentication key is missing; run verify --fresh"
            ) from error
        if len(key) != 32:
            raise StoreError("local authentication key is invalid")
        return key

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "schema_version": 1,
                "task_id": self.task_id,
                "runs": [],
                "aggregate": None,
            }
        try:
            envelope = json.loads(self.path.read_bytes())
            payload = envelope["payload"]
            expected = hmac.new(
                self.key(), canonical(payload), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(expected, envelope["mac"]):
                raise StoreError("local run authentication failed; run verify --fresh")
            if payload["task_id"] != self.task_id or payload["schema_version"] != 1:
                raise StoreError("local run identity is invalid")
            return payload
        except (KeyError, TypeError, json.JSONDecodeError, OSError) as error:
            raise StoreError(
                "local run record is unreadable; run verify --fresh"
            ) from error

    def write(self, payload: dict[str, Any]) -> None:
        if len(canonical(payload)) > 16 * 1024 * 1024:
            raise StoreError(
                "run ledger exceeds 16 MiB; preserve it and start a new task"
            )
        mac = hmac.new(
            self.key(create=True), canonical(payload), hashlib.sha256
        ).hexdigest()
        atomic_write(self.path, canonical({"payload": payload, "mac": mac}) + b"\n")

    def recover(self, *, fresh: bool = False) -> dict[str, Any]:
        try:
            ledger = self.read()
        except StoreError:
            if not fresh:
                raise
            # Keep untrusted history for diagnosis, never fall back to it.
            if self.path.exists():
                os.replace(
                    self.path, self.path.with_suffix(f".invalid-{secrets.token_hex(6)}")
                )
            try:
                self.key()
            except StoreError:
                key_path = self.root / "authentication.key"
                if key_path.exists():
                    os.replace(
                        key_path,
                        key_path.with_suffix(f".invalid-{secrets.token_hex(6)}"),
                    )
            ledger = self.read()
        for run in ledger["runs"]:
            if run["state"] == "running":
                run["state"] = "interrupted"
                run["cleanup_status"] = "unknown"
                ledger["aggregate"] = None
        self.write(ledger)
        return ledger


def latest_attempts(ledger: dict[str, Any], identity: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for run in ledger["runs"]:
        if run["identity"] != identity:
            continue
        for attempt in run["attempts"]:
            latest[attempt["gate"]] = {
                **attempt,
                "run_id": run["id"],
                "reusable": (
                    run["cleanup_status"] == "passed"
                    and run["state"] in {"passed", "failed"}
                    and attempt.get("check", {}).get("status") == "passed"
                ),
            }
    return latest
