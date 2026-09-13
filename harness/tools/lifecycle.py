from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .config import harness_root, load_config, project_root
from .metadata import FrontMatterError, parse_front_matter, values_as_list


class LifecycleError(ValueError):
    pass


PROTECTED_SECTIONS = (
    "Goal",
    "Non-goals",
    "Acceptance criteria",
    "Verification plan",
)
FROZEN_FIELDS = ("frozen_at", "freeze_reason", "frozen_scope_sha256")
MANAGED_FIELDS = {"status", "state_history", *FROZEN_FIELDS}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
DOCUMENTATION_IMPACTS = {"none", "required"}
DOCUMENTATION_FORBIDDEN_PREFIXES = (
    "harness/specs/active/",
    "harness/verification/evidence/",
    "harness/evolution/events/",
    "harness/evolution/proposals/",
)


def _active_spec(task_id: str) -> Path:
    from .summarizer import validate_task_id

    validate_task_id(task_id)
    return harness_root() / str(load_config()["specs"]["active"]) / f"{task_id}.md"


def _reason(value: str) -> str:
    reason = value.strip()
    if not reason:
        raise LifecycleError("reason must be non-empty")
    if "\n" in reason or "\r" in reason:
        raise LifecycleError("reason must be a single line")
    return reason


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise LifecycleError("timestamp must be an ISO-8601 datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise LifecycleError("timestamp must use UTC")
    return value


def _validate_event_time(value: str, *, migrated: bool) -> None:
    if migrated:
        try:
            date.fromisoformat(value)
            return
        except ValueError:
            pass
    _timestamp(value)


def _section(body: str, heading: str) -> str:
    match = re.search(
        rf"^(?P<marks>#{{1,2}})[ \t]+{re.escape(heading)}[ \t]*$",
        body,
        re.MULTILINE,
    )
    if match is None:
        raise LifecycleError(f"protected section missing or empty: {heading}")
    level = len(match.group("marks"))
    boundary = re.search(rf"^#{{1,{level}}}[ \t]+", body[match.end() :], re.MULTILINE)
    end = match.end() + boundary.start() if boundary else len(body)
    content = body[match.end() : end].strip()
    if not content:
        raise LifecycleError(f"protected section missing or empty: {heading}")
    return content


def core_contract_digest(body: str) -> str:
    contract = {heading: _section(body, heading) for heading in PROTECTED_SECTIONS}
    canonical = json.dumps(
        contract,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def parse_state_history(metadata: dict[str, Any]) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    for index, raw in enumerate(values_as_list(metadata.get("state_history"))):
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as error:
            raise LifecycleError(f"state_history item {index + 1} is not valid JSON") from error
        if not isinstance(event, dict):
            raise LifecycleError(f"state_history item {index + 1} must be an object")
        normalized = {str(key): str(value) for key, value in event.items()}
        if normalized.get("action") not in {"freeze", "resume"}:
            raise LifecycleError(f"state_history item {index + 1} has invalid action")
        if not normalized.get("at") or not normalized.get("reason"):
            raise LifecycleError(f"state_history item {index + 1} is incomplete")
        if "\n" in normalized["reason"] or "\r" in normalized["reason"]:
            raise LifecycleError(f"state_history item {index + 1} reason must be one line")
        if normalized["action"] == "freeze":
            digest = normalized.get("scope_sha256", "")
            if SHA256_PATTERN.fullmatch(digest) is None:
                raise LifecycleError(
                    f"state_history item {index + 1} has invalid scope_sha256"
                )
        if "baseline" in normalized and normalized["baseline"] != "migration":
            raise LifecycleError(f"state_history item {index + 1} has invalid baseline")
        try:
            _validate_event_time(
                normalized["at"], migrated=normalized.get("baseline") == "migration"
            )
        except LifecycleError as error:
            raise LifecycleError(
                f"state_history item {index + 1} has invalid timestamp: {error}"
            ) from error
        events.append(normalized)

    for index, event in enumerate(events):
        expected = "freeze" if index % 2 == 0 else "resume"
        if event["action"] != expected:
            raise LifecycleError("state_history actions must alternate freeze and resume")
    return events


def documentation_contract(metadata: dict[str, Any]) -> dict[str, Any]:
    impact = str(metadata.get("documentation_impact", "")).strip()
    if impact not in DOCUMENTATION_IMPACTS:
        raise LifecycleError("documentation_impact must be required or none")

    reason = str(metadata.get("documentation_reason", "")).strip()
    if not reason:
        raise LifecycleError("documentation_reason must be non-empty")
    if "\n" in reason or "\r" in reason:
        raise LifecycleError("documentation_reason must be a single line")

    targets = values_as_list(metadata.get("documentation_targets"))
    if impact == "none" and targets:
        raise LifecycleError("documentation_impact none must not declare targets")
    if impact == "required" and not targets:
        raise LifecycleError("documentation_impact required must declare targets")

    normalized: list[str] = []
    forbidden_targets = {
        (harness_root() / str(value)).resolve()
        for value in load_config().get("evolution", {}).get("forbidden_targets", [])
    }
    root = project_root().resolve()
    for raw_target in targets:
        target = raw_target.strip()
        if not target or "\\" in target:
            raise LifecycleError(
                "documentation_targets must use non-empty project-relative POSIX paths"
            )
        parts = target.split("/")
        if target.startswith("/") or any(part in {"", ".", ".."} for part in parts):
            raise LifecycleError(
                "documentation_targets must use safe project-relative paths"
            )
        resolved = (root / target).resolve()
        if not resolved.is_relative_to(root):
            raise LifecycleError("documentation_targets must stay inside the project")
        if resolved in forbidden_targets:
            raise LifecycleError(f"documentation target is forbidden: {target}")
        normalized_target = "/".join(parts)
        normalized_lower = normalized_target.lower()
        if not normalized_lower.endswith(".md"):
            raise LifecycleError(
                f"documentation target must be a Markdown file: {normalized_target}"
            )
        if normalized_lower.endswith("/index.md") or normalized_lower == "index.md":
            raise LifecycleError(
                f"documentation target must not be a generated index: {normalized_target}"
            )
        if any(
            normalized_lower.startswith(prefix)
            for prefix in DOCUMENTATION_FORBIDDEN_PREFIXES
        ):
            raise LifecycleError(
                f"documentation target is a generated or transient artifact: {normalized_target}"
            )
        if normalized_target in normalized:
            raise LifecycleError(f"duplicate documentation target: {normalized_target}")
        normalized.append(normalized_target)

    return {"impact": impact, "reason": reason, "targets": normalized}


def _managed_lines(
    status: str,
    history: list[dict[str, str]],
    *,
    frozen_at: str | None = None,
    freeze_reason: str | None = None,
    frozen_scope_sha256: str | None = None,
) -> list[str]:
    lines = [f"status: {status}"]
    if status == "frozen":
        lines.extend(
            [
                f"frozen_at: {frozen_at}",
                f"freeze_reason: {freeze_reason}",
                f"frozen_scope_sha256: {frozen_scope_sha256}",
            ]
        )
    lines.append("state_history:")
    lines.extend(
        "  - "
        + json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for event in history
    )
    return lines


def _rewrite_spec(path: Path, managed_lines: list[str]) -> None:
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines()
    if not lines or lines[0].strip() != "---":
        raise LifecycleError("missing opening front matter delimiter")
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration as error:
        raise LifecycleError("missing closing front matter delimiter") from error

    kept: list[str] = []
    index = 1
    while index < end:
        line = lines[index]
        top_level = bool(line) and not line[0].isspace() and ":" in line
        key = line.split(":", 1)[0].strip() if top_level else ""
        if key in MANAGED_FIELDS:
            index += 1
            while index < end and (not lines[index] or lines[index][0].isspace()):
                index += 1
            continue
        kept.append(line)
        index += 1

    body_lines = lines[end + 1 :]
    content = "\n".join(["---", *kept, *managed_lines, "---", *body_lines])
    if original.endswith("\n"):
        content += "\n"

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_active_spec(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        metadata, body = parse_front_matter(path)
    except (FrontMatterError, OSError) as error:
        return [str(error)]

    status = str(metadata.get("status", ""))
    if status not in {"active", "frozen"}:
        errors.append("status must be active or frozen")
    task_id = str(metadata.get("task_id", ""))
    if task_id != path.stem:
        errors.append("task_id must match the active spec filename")
    try:
        history = parse_state_history(metadata)
    except LifecycleError as error:
        errors.append(str(error))
        history = []

    if status == "active":
        for field in FROZEN_FIELDS:
            if metadata.get(field) not in (None, "", []):
                errors.append(f"active spec must not contain {field}")
        if history and history[-1].get("action") != "resume":
            errors.append("active spec state_history must end with resume")
        if bool(load_config().get("specs", {}).get("require_documentation_impact")):
            try:
                documentation_contract(metadata)
            except LifecycleError as error:
                errors.append(str(error))
        return errors

    if status != "frozen":
        return errors
    for field in FROZEN_FIELDS:
        if metadata.get(field) in (None, "", []):
            errors.append(f"frozen spec missing {field}")
    if not history or history[-1].get("action") != "freeze":
        errors.append("frozen spec state_history must end with freeze")
        return errors

    latest = history[-1]
    comparisons = {
        "frozen_at": latest.get("at"),
        "freeze_reason": latest.get("reason"),
        "frozen_scope_sha256": latest.get("scope_sha256"),
    }
    for field, expected in comparisons.items():
        if str(metadata.get(field, "")) != str(expected or ""):
            errors.append(f"{field} must match the latest freeze event")
    try:
        actual_digest = core_contract_digest(body)
    except LifecycleError as error:
        errors.append(str(error))
    else:
        if actual_digest != str(metadata.get("frozen_scope_sha256", "")):
            errors.append("frozen core contract digest does not match")
    return errors


def task_status(task_id: str) -> str | None:
    path = _active_spec(task_id)
    if not path.is_file():
        return None
    metadata, _ = parse_front_matter(path)
    return str(metadata.get("status", "")) or None


def freeze_spec(task_id: str, reason: str, *, at: str | None = None) -> Path:
    path = _active_spec(task_id)
    if not path.is_file():
        raise FileNotFoundError(f"active spec not found: {path}")
    metadata, body = parse_front_matter(path)
    status = str(metadata.get("status", ""))
    if status != "active":
        raise LifecycleError(f"freeze requires status active; found {status or 'missing'}")
    existing_errors = validate_active_spec(path)
    if existing_errors:
        raise LifecycleError(existing_errors[0])
    normalized_reason = _reason(reason)
    timestamp = _timestamp(at)
    digest = core_contract_digest(body)
    history = parse_state_history(metadata)
    history.append(
        {
            "action": "freeze",
            "at": timestamp,
            "reason": normalized_reason,
            "scope_sha256": digest,
        }
    )
    _rewrite_spec(
        path,
        _managed_lines(
            "frozen",
            history,
            frozen_at=timestamp,
            freeze_reason=normalized_reason,
            frozen_scope_sha256=digest,
        ),
    )
    return path


def resume_spec(task_id: str, reason: str, *, at: str | None = None) -> Path:
    path = _active_spec(task_id)
    if not path.is_file():
        raise FileNotFoundError(f"active spec not found: {path}")
    metadata, _ = parse_front_matter(path)
    status = str(metadata.get("status", ""))
    if status != "frozen":
        raise LifecycleError(f"resume requires status frozen; found {status or 'missing'}")
    existing_errors = validate_active_spec(path)
    if existing_errors:
        raise LifecycleError(existing_errors[0])
    normalized_reason = _reason(reason)
    history = parse_state_history(metadata)
    history.append(
        {
            "action": "resume",
            "at": _timestamp(at),
            "reason": normalized_reason,
        }
    )
    _rewrite_spec(path, _managed_lines("active", history))
    return path


def migrate_legacy_frozen_spec(task_id: str) -> Path:
    path = _active_spec(task_id)
    if not path.is_file():
        raise FileNotFoundError(f"active spec not found: {path}")
    metadata, body = parse_front_matter(path)
    if str(metadata.get("status", "")) != "frozen":
        raise LifecycleError("legacy migration requires status frozen")
    if values_as_list(metadata.get("state_history")):
        raise LifecycleError("legacy frozen spec already has state_history")
    frozen_at = str(metadata.get("frozen_at", "")).strip()
    freeze_reason = _reason(str(metadata.get("freeze_reason", "")))
    if not frozen_at:
        raise LifecycleError("legacy frozen spec missing frozen_at")
    digest = core_contract_digest(body)
    history = [
        {
            "action": "freeze",
            "at": frozen_at,
            "baseline": "migration",
            "reason": freeze_reason,
            "scope_sha256": digest,
        }
    ]
    _rewrite_spec(
        path,
        _managed_lines(
            "frozen",
            history,
            frozen_at=frozen_at,
            freeze_reason=freeze_reason,
            frozen_scope_sha256=digest,
        ),
    )
    return path
