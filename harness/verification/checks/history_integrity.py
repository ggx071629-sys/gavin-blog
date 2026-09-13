from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

MAX_FAILURES = 20
COMPLETION_SUFFIX = "--spec-completed.json"
DIGEST_REQUIRED_FROM = "20260901-"
REQUIRED_EVIDENCE_FIELDS = {
    "schema_version",
    "task_id",
    "created_at",
    "command",
    "status",
    "acceptance_criteria",
    "criteria_results",
    "verification_profile",
    "fingerprints",
    "documentation",
    "execution",
    "verification_cases",
    "checks",
    "summary",
    "source_commit",
}


def _json_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _front_matter_scalars(path: Path) -> dict[str, str] | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return values
        if line and not line.startswith((" ", "-")) and ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return None


def _historical_active_paths(project_root: Path) -> set[str]:
    result = subprocess.run(
        [
            "git",
            "log",
            "--full-history",
            "--format=",
            "--name-only",
            "HEAD",
            "--",
            "harness/specs/active",
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Git history query failed")
    return {line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()}


def _failures(context: dict[str, Any]) -> tuple[list[str], int]:
    root: Path = context["harness_root"]
    project_root: Path = context["project_root"]
    config = context["config"]
    archive_root = root / str(config["specs"]["archive"])
    active_root = root / str(config["specs"]["active"])
    evidence_root = root / str(config["verification"]["evidence"])
    event_root = root / str(config["evolution"]["events"])

    archives = {path.stem: path for path in sorted(archive_root.glob("*.md"))}
    active = {path.stem for path in active_root.glob("*.md")}
    events = {
        path.name[: -len(COMPLETION_SUFFIX)]: path
        for path in sorted(event_root.glob(f"*{COMPLETION_SUFFIX}"))
    }
    failures: list[str] = []

    for task_id in sorted(active & (set(archives) | set(events))):
        failures.append(f"{task_id}: active task overlaps deterministic close assets")
    for task_id in sorted(set(archives) - set(events)):
        failures.append(f"{task_id}: compressed archive lacks spec.completed event")
    for task_id in sorted(set(events) - set(archives)):
        failures.append(f"{task_id}: spec.completed event lacks compressed archive")

    try:
        history = _historical_active_paths(project_root)
    except RuntimeError as error:
        failures.append(str(error))
        history = None

    for task_id, archive in archives.items():
        expected_history = f"harness/specs/active/{task_id}.md"
        if history is not None and expected_history not in history:
            failures.append(f"{task_id}: original active spec is absent from Git history")

        metadata = _front_matter_scalars(archive)
        archive_digest: str | None = None
        if metadata is None:
            failures.append(f"{task_id}: compressed archive metadata is unreadable")
        else:
            if (
                metadata.get("id") != f"archive-{task_id}"
                or metadata.get("task_id") != task_id
                or metadata.get("status") != "compressed"
            ):
                failures.append(f"{task_id}: compressed archive metadata is inconsistent")
            raw_digest = metadata.get("evidence_sha256")
            archive_digest = raw_digest if raw_digest else None
        expected_link = f"../../verification/evidence/{task_id}.json"
        try:
            if expected_link not in archive.read_text(encoding="utf-8"):
                failures.append(f"{task_id}: compressed archive evidence link is inconsistent")
        except OSError:
            pass

        evidence = evidence_root / f"{task_id}.json"
        evidence_payload = _json_object(evidence)
        if evidence_payload is None:
            failures.append(f"{task_id}: main evidence is missing or unreadable")
        elif (
            evidence_payload.get("task_id") != task_id
            or evidence_payload.get("status") != "passed"
            or type(evidence_payload.get("schema_version")) is not int
            or evidence_payload.get("schema_version") not in {1, 2}
        ):
            failures.append(f"{task_id}: main evidence identity or status is inconsistent")
        evidence_digest = (
            hashlib.sha256(evidence.read_bytes()).hexdigest()
            if evidence_payload is not None
            else None
        )

        event = events.get(task_id)
        if event is None:
            continue
        event_payload = _json_object(event)
        if event_payload is None:
            failures.append(f"{task_id}: spec.completed event is unreadable")
        elif (
            type(event_payload.get("schema_version")) is not int
            or event_payload.get("schema_version") not in {1, 2}
            or event_payload.get("event_type") != "spec.completed"
            or event_payload.get("task_id") != task_id
            or event_payload.get("source") != "lifecycle"
            or event_payload.get("may_modify_agents_md") is not False
        ):
            failures.append(f"{task_id}: spec.completed event contract is inconsistent")
        elif event_payload.get("schema_version") == 2:
            event_digest = event_payload.get("evidence_sha256")
            if (
                not isinstance(event_digest, str)
                or len(event_digest) != 64
                or any(character not in "0123456789abcdef" for character in event_digest)
                or archive_digest != event_digest
                or evidence_digest != event_digest
            ):
                failures.append(f"{task_id}: evidence digest binding is inconsistent")
            if evidence_payload is not None and (
                evidence_payload.get("schema_version") != 2
                or set(evidence_payload) != REQUIRED_EVIDENCE_FIELDS
            ):
                failures.append(f"{task_id}: bound task evidence contract is incomplete")
        elif task_id >= DIGEST_REQUIRED_FROM or archive_digest is not None:
            failures.append(f"{task_id}: digest-bound close contract is required")

    return failures[:MAX_FAILURES], len(archives)


def run(context: dict[str, Any]) -> dict[str, Any]:
    failures, archive_count = _failures(context)
    details = failures or [
        f"{archive_count} deterministic closes retain archive, evidence, event, and active-spec history"
    ]
    return {"name": "history-integrity", "passed": not failures, "details": details}
