from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .config import harness_root, load_config, project_root
from .metadata import FrontMatterError, parse_front_matter
from .product_verification import ProductVerificationError, ensure_source_clean


class ChangeEnforcementError(ValueError):
    pass


TASK_ID = re.compile(r"^[0-9]{8}-[a-z0-9]+(?:-[a-z0-9]+)*$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
FAILURE_DETAIL_LIMIT = 20


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=project_root(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise ChangeEnforcementError(detail)
    return result.stdout.strip()


def _commit(ref: str) -> str:
    try:
        value = _git("rev-parse", "--verify", f"{ref}^{{commit}}")
    except ChangeEnforcementError as error:
        raise ChangeEnforcementError(f"Git ref is unavailable: {ref}") from error
    if COMMIT.fullmatch(value) is None:
        raise ChangeEnforcementError(f"Git ref does not resolve to one commit: {ref}")
    return value


def _is_ancestor(ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=project_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in {0, 1}:
        raise ChangeEnforcementError(result.stderr.strip() or "Git ancestry check failed")
    return result.returncode == 0


def changed_paths(base: str, head: str) -> list[str]:
    output = _git("diff", "--name-only", "-z", base, head)
    return sorted(path for path in output.split("\0") if path)


def risk_paths(paths: list[str], config: dict[str, Any]) -> list[str]:
    raw = config.get("change_enforcement", {})
    if not isinstance(raw, dict):
        raise ChangeEnforcementError("change_enforcement must be a table")
    prefixes = tuple(str(value) for value in raw.get("risk_prefixes", []))
    files = {str(value) for value in raw.get("risk_files", [])}
    if not prefixes and not files:
        raise ChangeEnforcementError("change_enforcement risk paths must not be empty")
    return sorted(path for path in paths if path in files or path.startswith(prefixes))


def _artifact_tasks(paths: list[str], config: dict[str, Any]) -> list[str]:
    archive_root = f"harness/{str(config['specs']['archive']).strip('/')}/"
    evidence_root = f"harness/{str(config['verification']['evidence']).strip('/')}/"
    archives: set[str] = set()
    evidence: set[str] = set()
    for path in paths:
        if path.startswith(archive_root) and path.endswith(".md"):
            task_id = Path(path).stem
            if TASK_ID.fullmatch(task_id):
                archives.add(task_id)
        if path.startswith(evidence_root) and path.endswith(".json"):
            task_id = Path(path).stem
            if TASK_ID.fullmatch(task_id):
                evidence.add(task_id)
    return sorted(archives & evidence, reverse=True)


def _generated_index_paths(config: dict[str, Any]) -> set[str]:
    paths = {"harness/INDEX.md"}
    for section in ("indexes", "nested_indexes"):
        definitions = config.get(section, {})
        if not isinstance(definitions, dict):
            continue
        for definition in definitions.values():
            if not isinstance(definition, dict):
                continue
            root = str(definition.get("path", "")).strip("/")
            if root:
                paths.add(f"harness/{root}/INDEX.md")
    return paths


def _allowed_post_evidence_paths(task_id: str, config: dict[str, Any]) -> set[str]:
    specs = config["specs"]
    verification = config["verification"]
    evolution = config["evolution"]
    return {
        *_generated_index_paths(config),
        f"harness/{str(specs['active']).strip('/')}/{task_id}.md",
        f"harness/{str(specs['archive']).strip('/')}/{task_id}.md",
        f"harness/{str(verification['evidence']).strip('/')}/{task_id}.json",
        f"harness/{str(evolution['events']).strip('/')}/{task_id}--spec-completed.json",
    }


def _validate_task(
    task_id: str,
    base: str,
    head: str,
    config: dict[str, Any],
) -> tuple[list[str], str | None]:
    errors: list[str] = []
    archive = harness_root() / str(config["specs"]["archive"]) / f"{task_id}.md"
    evidence = harness_root() / str(config["verification"]["evidence"]) / f"{task_id}.json"
    try:
        metadata, _ = parse_front_matter(archive)
        if metadata.get("task_id") != task_id or metadata.get("status") != "compressed":
            errors.append("archive must be compressed and match the task ID")
    except (OSError, FrontMatterError) as error:
        errors.append(f"archive is unreadable: {error}")

    try:
        payload = json.loads(evidence.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [*errors, f"evidence is unreadable: {error}"], None
    if not isinstance(payload, dict):
        return [*errors, "evidence must be a JSON object"], None
    if payload.get("schema_version") != 2:
        errors.append("evidence schema_version must be 2")
    if payload.get("task_id") != task_id:
        errors.append("evidence task_id does not match")
    if payload.get("status") != "passed":
        errors.append("evidence status must be passed")

    source = str(payload.get("source_commit", ""))
    if COMMIT.fullmatch(source) is None:
        errors.append("evidence source_commit must be a full commit SHA")
        return errors, None
    try:
        if source == base or not _is_ancestor(base, source):
            errors.append("evidence source_commit must be after the change base")
        if not _is_ancestor(source, head):
            errors.append("evidence source_commit must be reachable from change head")
        source_tree = _git("rev-parse", f"{source}^{{tree}}")
    except ChangeEnforcementError as error:
        errors.append(f"evidence source_commit is unavailable: {error}")
        return errors, None
    fingerprints = payload.get("fingerprints")
    if not isinstance(fingerprints, dict) or fingerprints.get("source_tree") != source_tree:
        errors.append("evidence source_tree fingerprint does not match source_commit")

    execution = payload.get("execution")
    if not isinstance(execution, dict):
        errors.append("evidence execution context must be present")
    elif execution.get("mode") != "git-worktree" or execution.get("source_commit") != source or execution.get("cleanup_status") != "passed":
        errors.append("evidence must record a cleaned isolated Git worktree")

    checks = payload.get("checks")
    if not isinstance(checks, list) or not checks:
        errors.append("evidence checks must be non-empty")
    elif any(not isinstance(check, dict) or check.get("status") != "passed" for check in checks):
        errors.append("every evidence check must be passed")
    elif not any(check.get("kind") == "product" for check in checks):
        errors.append("evidence must contain at least one product gate")
    if not errors:
        allowed = _allowed_post_evidence_paths(task_id, config)
        later_risk = [
            path
            for path in risk_paths(changed_paths(source, head), config)
            if path not in allowed
        ]
        if later_risk:
            shown = ", ".join(later_risk[:5])
            suffix = " ..." if len(later_risk) > 5 else ""
            errors.append(
                "evidence does not cover risk changes after source_commit: "
                f"{shown}{suffix}"
            )
    return errors, source


def inspect_change(base_ref: str, head_ref: str = "HEAD") -> dict[str, Any]:
    try:
        ensure_source_clean()
    except ProductVerificationError as error:
        raise ChangeEnforcementError(str(error)) from error
    base = _commit(base_ref)
    head = _commit(head_ref)
    if base == head:
        raise ChangeEnforcementError("change base and head must be different commits")
    if not _is_ancestor(base, head):
        raise ChangeEnforcementError("change base must be an ancestor of change head")
    config = load_config()
    paths = changed_paths(base, head)
    risky = risk_paths(paths, config)
    if not risky:
        return {"passed": True, "base": base, "head": head, "changed_paths": paths, "risk_paths": [], "tasks": [], "details": ["no configured risk paths changed; task coverage is not required"]}

    tasks = _artifact_tasks(paths, config)
    if not tasks:
        return {"passed": False, "base": base, "head": head, "changed_paths": paths, "risk_paths": risky, "tasks": [], "details": ["risk changes require a task archive and schema v2 evidence changed in the same diff"]}
    failures: list[str] = []
    valid: list[str] = []
    for task_id in tasks:
        errors, _source = _validate_task(task_id, base, head, config)
        if errors:
            failures.extend(f"{task_id}: {error}" for error in errors)
        else:
            valid.append(task_id)
    if valid:
        details = [f"risk changes are covered by task evidence: {', '.join(valid)}"]
    else:
        details = failures[:FAILURE_DETAIL_LIMIT]
        omitted = len(failures) - len(details)
        if omitted:
            details.append(f"{omitted} additional task validation error(s) omitted")
    return {
        "passed": bool(valid),
        "base": base,
        "head": head,
        "changed_paths": paths,
        "risk_paths": risky,
        "tasks": valid,
        "details": details,
    }
