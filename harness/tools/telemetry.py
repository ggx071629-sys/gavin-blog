from __future__ import annotations

import json
import math
import re
import statistics
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
HEALTH_STATUSES = ("no-data", "insufficient-data", "stable", "signal")


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


def failed_verification_run_ids(
    task_id: str,
    *,
    events: list[dict[str, Any]] | None = None,
) -> list[str]:
    available = events if events is not None else load_events()[0]
    run_ids: list[str] = []
    seen: set[str] = set()
    for event in available:
        if event.get("kind") != "task.verification" or event.get("task_id") != task_id:
            continue
        value = event.get("value")
        if not isinstance(value, dict) or value.get("status") != "failed":
            continue
        run_id = value.get("run_id")
        failure_kinds = value.get("failure_kinds")
        if not isinstance(run_id, str) or not run_id.strip() or run_id in seen:
            continue
        if (
            not isinstance(failure_kinds, list)
            or not failure_kinds
            or not all(isinstance(item, str) and item for item in failure_kinds)
        ):
            continue
        seen.add(run_id)
        run_ids.append(run_id)
    return run_ids


def failure_run_references(
    task_id: str,
    run_ids: list[str],
    *,
    events: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if len(run_ids) < 2:
        raise TelemetryError("repeated failure requires at least two run IDs")
    if len(run_ids) != len(set(run_ids)):
        raise TelemetryError("repeated failure run IDs must be unique")
    available = events if events is not None else load_events()[0]
    matching: dict[str, dict[str, Any]] = {}
    for event in available:
        if event.get("kind") != "task.verification" or event.get("task_id") != task_id:
            continue
        value = event.get("value")
        if not isinstance(value, dict):
            continue
        run_id = value.get("run_id")
        if isinstance(run_id, str):
            matching[run_id] = event

    references: list[dict[str, Any]] = []
    for run_id in run_ids:
        event = matching.get(run_id)
        if event is None:
            raise TelemetryError(
                f"failed verification run not found for task {task_id}: {run_id}"
            )
        value = event["value"]
        assert isinstance(value, dict)
        if value.get("status") != "failed":
            raise TelemetryError(f"verification run is not failed: {run_id}")
        failure_kinds = value.get("failure_kinds")
        if (
            not isinstance(failure_kinds, list)
            or not failure_kinds
            or not all(isinstance(item, str) and item for item in failure_kinds)
        ):
            raise TelemetryError(f"verification run has invalid failure kinds: {run_id}")
        source_commit = value.get("source_commit")
        if source_commit is not None and (
            not isinstance(source_commit, str)
            or re.fullmatch(r"[0-9a-f]{40}", source_commit) is None
        ):
            raise TelemetryError(f"verification run has invalid source commit: {run_id}")
        cleanup = value.get("isolation_cleanup")
        if cleanup not in {None, "passed", "failed"}:
            raise TelemetryError(f"verification run has invalid cleanup status: {run_id}")
        references.append(
            {
                "run_id": run_id,
                "observed_at": str(event.get("observed_at")),
                "source_commit": source_commit,
                "failure_kinds": sorted(set(failure_kinds)),
                "isolation_cleanup": cleanup,
            }
        )
    return references


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


def _health_settings(config: dict[str, Any] | None = None) -> dict[str, int | float]:
    source = config if config is not None else load_config()
    try:
        raw = source["telemetry"]["health"]
        settings: dict[str, int | float] = {
            "min_samples": raw["min_samples"],
            "baseline_samples": raw["baseline_samples"],
            "recent_samples": raw["recent_samples"],
            "consecutive_failures": raw["consecutive_failures"],
            "duration_ratio": raw["duration_ratio"],
        }
    except (KeyError, TypeError) as error:
        raise TelemetryError("telemetry health configuration is incomplete") from error
    integer_keys = (
        "min_samples",
        "baseline_samples",
        "recent_samples",
        "consecutive_failures",
    )
    for key in integer_keys:
        value = settings[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise TelemetryError(f"telemetry health {key} must be a positive integer")
    ratio = settings["duration_ratio"]
    if (
        isinstance(ratio, bool)
        or not isinstance(ratio, (int, float))
        or not math.isfinite(float(ratio))
        or float(ratio) <= 1
    ):
        raise TelemetryError("telemetry health duration_ratio must be greater than 1")
    return settings


def _health_series_key(event: dict[str, Any]) -> str | None:
    kind = event.get("kind")
    if kind == "task.verification":
        task_id = event.get("task_id")
        if isinstance(task_id, str) and task_id.strip():
            return f"task.verification:{task_id}"
        return None
    if kind == "release.run":
        return str(kind)
    value = event.get("value")
    if kind == "release.stage" and isinstance(value, dict):
        stage = value.get("stage")
        if isinstance(stage, str) and stage.strip():
            return f"release.stage:{stage}"
    return None


def _series_health(
    series_key: str,
    events: list[dict[str, Any]],
    settings: dict[str, int | float],
) -> dict[str, Any]:
    statuses: list[str] = []
    durations: list[float] = []
    for event in events:
        value = event.get("value")
        if not isinstance(value, dict):
            continue
        status = value.get("status")
        if status in {"passed", "failed"}:
            statuses.append(str(status))
        duration = value.get("duration_ms")
        if (
            isinstance(duration, (int, float))
            and not isinstance(duration, bool)
            and math.isfinite(float(duration))
            and float(duration) >= 0
        ):
            durations.append(float(duration))

    min_samples = int(settings["min_samples"])
    failure_threshold = int(settings["consecutive_failures"])
    consecutive = 0
    for status in reversed(statuses):
        if status != "failed":
            break
        consecutive += 1

    signals: list[dict[str, Any]] = []
    if len(statuses) >= min_samples and consecutive >= failure_threshold:
        signals.append(
            {
                "kind": "consecutive-failures",
                "observed": consecutive,
                "threshold": failure_threshold,
            }
        )

    duration_enabled = not series_key.startswith("task.verification:")
    baseline_count = int(settings["baseline_samples"])
    recent_count = int(settings["recent_samples"])
    required_durations = baseline_count + recent_count
    duration_result: dict[str, Any] = {
        "enabled": duration_enabled,
        "samples": len(durations),
        "required_samples": required_durations if duration_enabled else None,
        "baseline_median_ms": None,
        "recent_median_ms": None,
        "ratio": None,
        "threshold": float(settings["duration_ratio"]) if duration_enabled else None,
        "zero_baseline": False,
    }
    duration_ready = not duration_enabled
    if duration_enabled and len(durations) >= required_durations:
        selected = durations[-required_durations:]
        baseline = selected[:baseline_count]
        recent = selected[baseline_count:]
        baseline_median = float(statistics.median(baseline))
        recent_median = float(statistics.median(recent))
        duration_result["baseline_median_ms"] = round(baseline_median, 3)
        duration_result["recent_median_ms"] = round(recent_median, 3)
        duration_ready = True
        if baseline_median == 0:
            duration_result["zero_baseline"] = True
        else:
            ratio = recent_median / baseline_median
            duration_result["ratio"] = round(ratio, 3)
            if ratio >= float(settings["duration_ratio"]):
                signals.append(
                    {
                        "kind": "duration-regression",
                        "observed_ratio": round(ratio, 3),
                        "threshold": float(settings["duration_ratio"]),
                    }
                )

    enough_status = len(statuses) >= min_samples
    if signals:
        status = "signal"
    elif enough_status and duration_ready:
        status = "stable"
    else:
        status = "insufficient-data"
    return {
        "status": status,
        "events": len(events),
        "status_samples": len(statuses),
        "consecutive_failures": consecutive,
        "duration": duration_result,
        "signals": signals,
    }


def assess_health(
    events: list[dict[str, Any]],
    source_files: int = 0,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = _health_settings(config)
    grouped: dict[str, list[tuple[datetime, int, dict[str, Any]]]] = {}
    for position, event in enumerate(events):
        key = _health_series_key(event)
        if key is None:
            continue
        grouped.setdefault(key, []).append(
            (_timestamp(str(event["observed_at"])), position, event)
        )

    series = {
        key: _series_health(
            key,
            [item[2] for item in sorted(items, key=lambda item: (item[0], item[1]))],
            settings,
        )
        for key, items in sorted(grouped.items())
    }
    series_status = {status: 0 for status in HEALTH_STATUSES}
    for item in series.values():
        series_status[item["status"]] += 1
    if not series:
        status = "no-data"
    elif series_status["signal"]:
        status = "signal"
    elif series_status["insufficient-data"]:
        status = "insufficient-data"
    else:
        status = "stable"
    return {
        "schema_version": 1,
        "status": status,
        "source_files": source_files,
        "events": len(events),
        "evaluated_events": sum(item["events"] for item in series.values()),
        "settings": settings,
        "series_status": series_status,
        "series": series,
    }
