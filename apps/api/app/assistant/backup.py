from __future__ import annotations

from pathlib import Path

RUNTIME_SUFFIXES = (".db", ".db-wal", ".db-shm", ".owner.lock")


def is_runtime_artifact(path: Path, runtime_path: Path | None) -> bool:
    if runtime_path is None:
        name = path.name
        return name.startswith("assistant_runtime")
    resolved = path.resolve()
    runtime = runtime_path.resolve()
    return (
        resolved == runtime
        or str(resolved).startswith(str(runtime) + "-")
        or resolved == Path(str(runtime) + ".owner.lock")
    )


def content_backup_includes() -> tuple[str, ...]:
    return (
        "assistant_daily_metrics",
        "assistant_budget_policy",
        "assistant_budget_reservations",
        "assistant_index_embedding_budgets",
        "assistant_index_embedding_attempts",
        "assistant_chunks",
        "assistant_index_generations",
        "articles",
        "media_assets",
    )


def runtime_backup_excludes() -> tuple[str, ...]:
    return (
        "assistant_runtime",
        "assistant_runtime.db",
        "assistant_runtime.db-wal",
        "assistant_runtime.db-shm",
    )
