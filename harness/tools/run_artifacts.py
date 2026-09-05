"""Bounded, local-only diagnostics, exported before the worktree is removed."""

from __future__ import annotations

import contextvars
import shutil
import time
from pathlib import Path

from . import run_store

LOG_LIMIT = 2 * 1024 * 1024
RUN_LIMIT = 64 * 1024 * 1024
TOTAL_LIMIT = 512 * 1024 * 1024
RETENTION_SECONDS = 14 * 86400
log_path: contextvars.ContextVar[Path | None] = contextvars.ContextVar(
    "gate_log", default=None
)


def retain(root: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    used = sum(path.stat().st_size for path in destination.rglob("*") if path.is_file())
    omitted = 0
    for relative in (
        "apps/web/test-results",
        "apps/web/playwright-report",
        "test-results",
    ):
        source = root / relative
        if not source.is_dir() or source.is_symlink():
            continue
        for path in sorted(source.rglob("*")):
            if (
                not path.is_file()
                or path.is_symlink()
                or not path.resolve().is_relative_to(root.resolve())
            ):
                continue
            size = path.stat().st_size
            if size + used > RUN_LIMIT:
                omitted += 1
                continue
            target = destination / "artifacts" / path.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            used += size
    if omitted:
        (destination / "omitted.txt").write_text(
            f"{omitted} files omitted by 64 MiB limit\n"
        )


def prune() -> None:
    roots = [run_store.store_root() / "artifacts", run_store.store_root() / "diagnostics" / "artifacts"]
    entries = []
    for root in roots:
        if not root.is_dir():
            continue
        for directory in root.iterdir():
            if directory.is_symlink() or not directory.is_dir():
                continue
            size = sum(p.stat().st_size for p in directory.rglob("*") if p.is_file() and not p.is_symlink())
            entries.append((directory.stat().st_mtime, size, directory, root))
    total = sum(size for _, size, _, _ in entries)
    for modified, size, directory, root in sorted(entries):
        if time.time() - modified > RETENTION_SECONDS or total > TOTAL_LIMIT:
            if directory.resolve().parent != root.resolve():
                raise ValueError("artifact cleanup escaped its root")
            shutil.rmtree(directory)
            total -= size
