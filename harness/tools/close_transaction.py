"""Durable rollback journal for close; callers hold the repository operation lock."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

from . import events, indexer, run_store, summarizer
from .run_store import RunStore, StoreError, atomic_write, canonical


def journal_path() -> Path:
    return run_store.store_root() / "close-transaction.json"


def begin(snapshots: list[tuple[str, Path, str, Path, str]], head: str | None) -> None:
    payload = {
        "head": head,
        "tasks": [
            {"task_id": task, "source": source, "digest": digest}
            for task, _, source, _, digest in snapshots
        ],
    }
    key = RunStore(snapshots[0][0]).key(create=True)
    mac = hmac.new(key, canonical(payload), hashlib.sha256).hexdigest()
    atomic_write(journal_path(), canonical({"payload": payload, "mac": mac}))


def finish() -> None:
    journal_path().unlink(missing_ok=True)


def recover() -> None:
    path = journal_path()
    if not path.exists():
        return
    try:
        envelope = json.loads(path.read_bytes())
        payload = envelope["payload"]
        key = RunStore(payload["tasks"][0]["task_id"]).key()
        expected = hmac.new(key, canonical(payload), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, envelope["mac"]):
            raise StoreError("close recovery journal authentication failed")
        # Check every target before changing anything, preserving external edits.
        for task in payload["tasks"]:
            source = summarizer.active_spec(task["task_id"])
            if source.exists() and source.read_text(encoding="utf-8") != task["source"]:
                raise StoreError(
                    "close recovery found an externally edited active spec"
                )
            archive = summarizer.archive_spec(task["task_id"])
            if archive.exists() and task["digest"] not in archive.read_text(
                encoding="utf-8"
            ):
                raise StoreError("close recovery found an unrelated archive")
            event = events.event_path("spec.completed", task["task_id"])
            if event.exists() and task["digest"] not in event.read_text(
                encoding="utf-8"
            ):
                raise StoreError("close recovery found an unrelated event")
        for task in payload["tasks"]:
            summarizer.restore_spec(
                task["task_id"],
                task["source"],
                summarizer.archive_spec(task["task_id"]),
            )
            events.event_path("spec.completed", task["task_id"]).unlink(missing_ok=True)
        indexer.write_indexes()
        finish()
        print("recovered interrupted close transaction; active specs restored")
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise StoreError(
            "close recovery journal is unreadable; manual recovery required"
        ) from error
