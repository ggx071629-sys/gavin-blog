from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import harness_root, load_config
from .result_reporting import summarize_checks


class TelemetryError(ValueError):
    pass


FILE_TOKEN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EVENT_KEYS = {"schema_version", "observed_at", "kind", "task_id", "value", "source"}


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise TelemetryError("observed_at must be an ISO-8601 datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TelemetryError("observed_at must include a timezone")
    return parsed


def validate_event(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise TelemetryError("event must be a JSON object")
    unknown = sorted(set(event) - EVENT_KEYS)
    if unknown:
        raise TelemetryError(f"event contains unsupported fields: {', '.join(unknown)}")
    if event.get("schema_version") != 1:
        raise TelemetryError("schema_version must be 1")
    observed_at = event.get("observed_at")
    if not isinstance(observed_at, str):
        raise TelemetryError("observed_at must be a string")
    _timestamp(observed_at)
    kind = event.get("kind")
    if not isinstance(kind, str) or not kind.strip():
        raise TelemetryError("kind must be a non-empty string")
    if "value" not in event:
        raise TelemetryError("value is required")
    task_id = event.get("task_id")
    if task_id is not None and not isinstance(task_id, str):
        raise TelemetryError("task_id must be a string or null")
    source = event.get("source")
    if source is not None and (not isinstance(source, str) or not source.strip()):
        raise TelemetryError("source must be a non-empty string when present")
    return event


def local_directory() -> Path:
    return harness_root() / str(load_config()["telemetry"]["local"])


def append_event(
    kind: str,
    value: Any,
    *,
    task_id: str | None = None,
    source: str,
    stream: str = "observations",
    observed_at: str | None = None,
) -> Path:
    if FILE_TOKEN.fullmatch(stream) is None:
        raise TelemetryError("telemetry stream must be a lowercase filename token")
    event = validate_event(
        {
            "schema_version": 1,
            "observed_at": observed_at or datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "task_id": task_id,
            "value": value,
            "source": source,
        }
    )
    directory = local_directory()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{stream}.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    return path


def observe_task_verification(
    task_id: str,
    profile: str,
    execution: dict[str, Any],
    checks: list[dict[str, Any]],
    source_commit: str | None,
) -> Path:
    summary = summarize_checks(checks)
    failures = summary.get("failures", [])
    failure_kinds = sorted(
        {
            str(failure.get("kind"))
            for failure in failures
            if isinstance(failure, dict) and failure.get("kind")
        }
    )
    value = {
        "run_id": str(uuid4()),
        "status": "passed" if summary["checks"]["failed"] == 0 else "failed",
        "duration_ms": summary["duration_ms"],
        "checks": summary["checks"],
        "test_counts": summary.get("test_counts"),
        "failure_kinds": failure_kinds,
        "verification_profile": profile or None,
        "source_commit": source_commit,
        "isolation_cleanup": execution.get("cleanup_status"),
    }
    return append_event(
        "task.verification",
        value,
        task_id=task_id,
        source="tools.harness.verify",
        stream="task-verification",
    )


def observe_task_verification_safely(
    task_id: str,
    profile: str,
    execution: dict[str, Any],
    checks: list[dict[str, Any]],
    source_commit: str | None,
) -> str | None:
    try:
        observe_task_verification(task_id, profile, execution, checks, source_commit)
    except (OSError, ValueError) as error:
        return str(error)
    return None


def load_events(directory: Path | None = None) -> tuple[list[dict[str, Any]], int]:
    root = directory or local_directory()
    if not root.exists():
        return [], 0
    events: list[dict[str, Any]] = []
    files = sorted(root.glob("*.jsonl"))
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise TelemetryError(f"{path.name}: unreadable: {error}") from error
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                raise TelemetryError(f"{path.name}:{line_number}: empty JSONL line")
            try:
                event = json.loads(line)
                events.append(validate_event(event))
            except (json.JSONDecodeError, TelemetryError) as error:
                raise TelemetryError(f"{path.name}:{line_number}: {error}") from error
    return events, len(files)


def _duration_summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "p50": None, "p95": None, "max": None}
    ordered = sorted(values)

    def nearest_rank(percentile: float) -> float:
        index = max(0, math.ceil(percentile * len(ordered)) - 1)
        return round(ordered[index], 3)

    return {
        "count": len(ordered),
        "p50": nearest_rank(0.50),
        "p95": nearest_rank(0.95),
        "max": round(ordered[-1], 3),
    }


def summarize(events: list[dict[str, Any]], source_files: int = 0) -> dict[str, Any]:
    by_kind: dict[str, dict[str, Any]] = {}
    by_stage: dict[str, dict[str, Any]] = {}
    statuses = {"passed": 0, "failed": 0, "skipped": 0, "other": 0}
    durations: list[float] = []
    timestamps: list[datetime] = []

    def add_group(target: dict[str, dict[str, Any]], key: str, status: str, duration: float | None) -> None:
        group = target.setdefault(
            key,
            {"events": 0, "status": {"passed": 0, "failed": 0, "skipped": 0, "other": 0}, "durations": []},
        )
        group["events"] += 1
        group["status"][status] += 1
        if duration is not None:
            group["durations"].append(duration)

    for event in events:
        timestamps.append(_timestamp(str(event["observed_at"])))
        value = event.get("value")
        status = "other"
        duration: float | None = None
        stage: str | None = None
        if isinstance(value, dict):
            raw_status = str(value.get("status", ""))
            if raw_status in {"passed", "failed", "skipped"}:
                status = raw_status
            raw_duration = value.get("duration_ms")
            if isinstance(raw_duration, (int, float)) and not isinstance(raw_duration, bool) and raw_duration >= 0:
                duration = float(raw_duration)
                durations.append(duration)
            if event["kind"] == "release.stage" and isinstance(value.get("stage"), str):
                stage = value["stage"]
        statuses[status] += 1
        add_group(by_kind, str(event["kind"]), status, duration)
        if stage:
            add_group(by_stage, stage, status, duration)

    def finalize(groups: dict[str, dict[str, Any]]) -> dict[str, Any]:
        return {
            key: {
                "events": group["events"],
                "status": group["status"],
                "duration_ms": _duration_summary(group.pop("durations")),
            }
            for key, group in sorted(groups.items())
        }

    return {
        "schema_version": 1,
        "source_files": source_files,
        "events": len(events),
        "window": {
            "first": min(timestamps).isoformat() if timestamps else None,
            "last": max(timestamps).isoformat() if timestamps else None,
        },
        "status": statuses,
        "duration_ms": _duration_summary(durations),
        "by_kind": finalize(by_kind),
        "by_stage": finalize(by_stage),
    }
