from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import harness_root, load_config
from .summarizer import validate_task_id

EVIDENCE_RUN_KEYS = {
    "run_id",
    "observed_at",
    "source_commit",
    "failure_kinds",
    "isolation_cleanup",
}


def _validated_evidence_runs(
    event_type: str,
    source: str,
    evidence_runs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if event_type != "verification.repeated_failure":
        if evidence_runs:
            raise ValueError(
                "evidence runs are only valid for verification.repeated_failure"
            )
        return []
    if source != "manual":
        raise ValueError("verification.repeated_failure must use manual source")
    if len(evidence_runs) < 2:
        raise ValueError(
            "verification.repeated_failure requires two confirmed failed runs"
        )

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in evidence_runs:
        if set(item) != EVIDENCE_RUN_KEYS:
            raise ValueError("repeated failure evidence run fields are invalid")
        run_id = item.get("run_id")
        if not isinstance(run_id, str) or not run_id.strip() or run_id in seen:
            raise ValueError("repeated failure evidence run IDs must be unique")
        seen.add(run_id)
        observed_at = item.get("observed_at")
        if not isinstance(observed_at, str):
            raise TypeError("repeated failure observed_at must be a datetime")
        try:
            observed = datetime.fromisoformat(observed_at)
        except ValueError as error:
            raise ValueError("repeated failure observed_at must be a datetime") from error
        if observed.tzinfo is None or observed.utcoffset() is None:
            raise ValueError("repeated failure observed_at must include a timezone")
        source_commit = item.get("source_commit")
        if source_commit is not None and (
            not isinstance(source_commit, str)
            or len(source_commit) != 40
            or any(character not in "0123456789abcdef" for character in source_commit)
        ):
            raise ValueError("repeated failure source_commit must be a full Git SHA")
        failure_kinds = item.get("failure_kinds")
        if not isinstance(failure_kinds, list) or not failure_kinds or not all(
            isinstance(value, str) and value for value in failure_kinds
        ):
            raise ValueError("repeated failure failure_kinds must not be empty")
        cleanup = item.get("isolation_cleanup")
        if cleanup not in {None, "passed", "failed"}:
            raise ValueError("repeated failure cleanup status is invalid")
        normalized.append(
            {
                "run_id": run_id,
                "observed_at": observed_at,
                "source_commit": source_commit,
                "failure_kinds": sorted(set(failure_kinds)),
                "isolation_cleanup": cleanup,
            }
        )
    return normalized


def event_path(event_type: str, task_id: str) -> Path:
    validate_task_id(task_id)
    token = event_type.replace(".", "-")
    config = load_config()
    return (
        harness_root()
        / str(config["evolution"]["events"])
        / f"{task_id}--{token}.json"
    )


def emit_event(
    event_type: str,
    task_id: str,
    reason: str,
    source: str,
    *,
    create_proposal: bool = True,
    evidence_runs: list[dict[str, Any]] | None = None,
    evidence_sha256: str | None = None,
) -> tuple[Path, Path | None]:
    config = load_config()
    validate_task_id(task_id)
    allowed = set(config["evolution"]["allowed_events"])
    if event_type not in allowed:
        raise ValueError(f"event type is not allowed: {event_type}")
    if source == "telemetry":
        raise ValueError("telemetry cannot directly trigger evolution")
    evidence_runs = _validated_evidence_runs(event_type, source, evidence_runs or [])
    if evidence_sha256 is not None:
        if event_type != "spec.completed":
            raise ValueError("evidence_sha256 is only valid for spec.completed")
        if re.fullmatch(r"[0-9a-f]{64}", evidence_sha256) is None:
            raise ValueError("evidence_sha256 must be a lowercase SHA-256")

    token = event_type.replace(".", "-")
    events_dir = harness_root() / str(config["evolution"]["events"])
    proposals_dir = harness_root() / str(config["evolution"]["proposals"])
    events_dir.mkdir(parents=True, exist_ok=True)
    proposals_dir.mkdir(parents=True, exist_ok=True)
    target_event = event_path(event_type, task_id)
    proposal_path = proposals_dir / f"{task_id}--{token}.md"
    if target_event.exists() or proposal_path.exists():
        raise FileExistsError("event or proposal already exists")

    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "schema_version": 2 if evidence_sha256 is not None else 1,
        "event_type": event_type,
        "task_id": task_id,
        "created_at": now,
        "source": source,
        "reason": reason,
        "may_modify_agents_md": False,
    }
    if evidence_runs:
        payload["evidence_runs"] = evidence_runs
    if evidence_sha256 is not None:
        payload["evidence_sha256"] = evidence_sha256
    from .run_store import atomic_write
    atomic_write(target_event, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    if create_proposal:
        evidence_section = ""
        if evidence_runs:
            lines = ["## Confirmed failure runs", ""]
            for item in evidence_runs:
                kinds = ", ".join(str(value) for value in item["failure_kinds"])
                lines.append(
                    "- "
                    f"`{item['run_id']}` at {item['observed_at']}; "
                    f"commit `{item['source_commit']}`; kinds `{kinds}`; "
                    f"cleanup `{item['isolation_cleanup']}`"
                )
            evidence_section = "\n".join(lines) + "\n\n"
        proposal_path.write_text(
            "---\n"
            f"id: evolution-{task_id}-{token}\n"
            "level: L1\n"
            f"summary: Review evolution event {event_type} for {task_id}\n"
            "load_when:\n"
            "  - process-evolution\n"
            f"  - task:{task_id}\n"
            f"task_id: {task_id}\n"
            "status: proposed\n"
            "---\n\n"
            f"# Evolution proposal: {event_type}\n\n"
            f"Reason: {reason}\n\n"
            f"{evidence_section}"
            "## Allowed outcome\n\n"
            "After human confirmation, update only relevant L1/L2 sources, templates, workflows, indexes, or checks.\n\n"
            "## Forbidden outcome\n\n"
            "This proposal must not modify `AGENTS.md` automatically.\n",
            encoding="utf-8",
            newline="\n",
        )
        return target_event, proposal_path
    return target_event, None
