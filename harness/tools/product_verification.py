from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .config import load_config, project_root
from .metadata import parse_front_matter
from .summarizer import active_spec

CRITERION_PATTERN = re.compile(r"^-\s+(AC-[1-9][0-9]*):\s+\S", re.MULTILINE)
GATE_PATTERN = re.compile(
    r"^-\s+([a-z0-9]+(?:-[a-z0-9]+)*)\s+=>\s+(AC-[1-9][0-9]*(?:\s*,\s*AC-[1-9][0-9]*)*)\s*$",
    re.MULTILINE,
)


class ProductVerificationError(ValueError):
    pass


def _section(body: str, heading: str) -> str:
    match = re.search(
        rf"^(?P<marks>#{{1,2}})[ \t]+{re.escape(heading)}[ \t]*$",
        body,
        re.MULTILINE,
    )
    if match is None:
        raise ProductVerificationError(f"required section missing: {heading}")
    level = len(match.group("marks"))
    boundary = re.search(rf"^#{{1,{level}}}[ \t]+", body[match.end() :], re.MULTILINE)
    end = match.end() + boundary.start() if boundary else len(body)
    content = body[match.end() : end].strip()
    if not content:
        raise ProductVerificationError(f"required section empty: {heading}")
    return content


def verification_contract(task_id: str) -> tuple[list[str], dict[str, list[str]]]:
    path = active_spec(task_id)
    if not path.is_file():
        raise ProductVerificationError(f"active spec not found: {path}")
    _, body = parse_front_matter(path)
    acceptance = _section(body, "Acceptance criteria")
    verification = _section(body, "Verification plan")

    criteria = CRITERION_PATTERN.findall(acceptance)
    if not criteria:
        raise ProductVerificationError(
            "Acceptance criteria must use '- AC-N: observable outcome' entries"
        )
    if len(criteria) != len(set(criteria)):
        raise ProductVerificationError("Acceptance criteria IDs must be unique")

    mappings: dict[str, list[str]] = {}
    for match in GATE_PATTERN.finditer(verification):
        gate = match.group(1)
        if gate in mappings:
            raise ProductVerificationError(f"verification gate mapped more than once: {gate}")
        mappings[gate] = [item.strip() for item in match.group(2).split(",")]
    if not mappings:
        raise ProductVerificationError(
            "Verification plan must use '- gate-name => AC-1, AC-2' entries"
        )

    known = set(criteria)
    referenced = {criterion for covered in mappings.values() for criterion in covered}
    unknown = sorted(referenced - known)
    missing = sorted(known - referenced)
    if unknown:
        raise ProductVerificationError(
            f"Verification plan references unknown criteria: {', '.join(unknown)}"
        )
    if missing:
        raise ProductVerificationError(
            f"Acceptance criteria lack a verification gate: {', '.join(missing)}"
        )
    return criteria, mappings


def _configured_gates() -> dict[str, Any]:
    verification = load_config().get("verification", {})
    gates = verification.get("gates", {})
    return dict(gates) if isinstance(gates, dict) else {}


def _configured_profiles() -> dict[str, Any]:
    verification = load_config().get("verification", {})
    profiles = verification.get("profiles", {})
    return dict(profiles) if isinstance(profiles, dict) else {}


def verification_profile(task_id: str) -> str:
    path = active_spec(task_id)
    if not path.is_file():
        raise ProductVerificationError(f"active spec not found: {path}")
    metadata, _ = parse_front_matter(path)
    profile = str(metadata.get("verification_profile", "")).strip()
    if not profile:
        raise ProductVerificationError("active spec must declare verification_profile")
    if profile not in _configured_profiles():
        raise ProductVerificationError(f"unknown verification_profile: {profile}")
    return profile


def validate_configured_gates(
    mappings: dict[str, list[str]],
    profile: str | None = None,
) -> None:
    unknown = sorted(set(mappings) - set(_configured_gates()))
    if unknown:
        raise ProductVerificationError(
            f"Verification plan uses unregistered gates: {', '.join(unknown)}"
        )
    if profile is None:
        return
    profiles = _configured_profiles()
    definition = profiles.get(profile)
    if not isinstance(definition, dict):
        raise ProductVerificationError(f"unknown verification_profile: {profile}")
    raw_required = definition.get("required_gates", [])
    if not isinstance(raw_required, list):
        raise ProductVerificationError(
            f"verification profile {profile} required_gates must be an array"
        )
    required = {str(value) for value in raw_required}
    unknown_required = sorted(required - set(_configured_gates()))
    if unknown_required:
        raise ProductVerificationError(
            f"verification profile {profile} uses unregistered gates: "
            + ", ".join(unknown_required)
        )
    missing = sorted(required - set(mappings))
    if missing:
        raise ProductVerificationError(
            f"verification profile {profile} requires gates: {', '.join(missing)}"
        )


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=project_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ProductVerificationError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def evidence_fingerprints(
    task_id: str,
    criteria: list[str],
    mappings: dict[str, list[str]],
    profile: str,
) -> dict[str, str]:
    path = active_spec(task_id)
    gates = _configured_gates()
    profiles = _configured_profiles()
    gate_contract = {
        "profile": {profile: profiles[profile]},
        "gates": {gate: gates[gate] for gate in mappings},
        "isolation": load_config().get("verification", {}).get("isolation", {}),
    }
    verification_contract = {
        "profile": profile,
        "acceptance_criteria": criteria,
        "mappings": mappings,
    }
    return {
        "source_tree": _git_value("rev-parse", "HEAD^{tree}"),
        "active_spec_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "verification_contract_sha256": _canonical_hash(verification_contract),
        "gate_config_sha256": _canonical_hash(gate_contract),
    }


def source_changes() -> list[str]:
    config = load_config()
    raw_paths = config.get("verification", {}).get("source_paths", [])
    paths = [str(value) for value in raw_paths]
    if not paths:
        raise ProductVerificationError("verification.source_paths must not be empty")
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", *paths],
        cwd=project_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "git status failed"
        raise ProductVerificationError(detail)
    return [line for line in result.stdout.splitlines() if line.strip()]


def ensure_source_clean() -> None:
    changes = source_changes()
    if changes:
        shown = ", ".join(line[3:] for line in changes[:5])
        suffix = " ..." if len(changes) > 5 else ""
        raise ProductVerificationError(
            f"verification source has uncommitted changes: {shown}{suffix}"
        )


def _command(
    gate: str,
    definition: dict[str, Any],
    execution_root: Path | None = None,
) -> tuple[list[str], Path, int]:
    raw_command = definition.get("command")
    if not isinstance(raw_command, list) or not raw_command:
        raise ProductVerificationError(f"gate {gate} command must be a non-empty array")
    command = [str(value) for value in raw_command]
    if command[0] == "{python}":
        command[0] = sys.executable
    else:
        executable = shutil.which(command[0])
        if executable is None:
            raise ProductVerificationError(
                f"gate {gate} executable was not found: {command[0]}"
            )
        command[0] = executable

    root = (execution_root or project_root()).resolve()
    cwd = (root / str(definition.get("cwd", "."))).resolve()
    if not cwd.is_relative_to(root) or not cwd.is_dir():
        raise ProductVerificationError(f"gate {gate} cwd must be inside the project")
    timeout_seconds = definition.get("timeout_seconds", 900)
    if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
        raise ProductVerificationError(
            f"gate {gate} timeout_seconds must be a positive integer"
        )
    return command, cwd, timeout_seconds


def _tail(output: str, limit: int = 2000) -> list[str]:
    compact = output.strip()
    if not compact:
        return []
    return compact[-limit:].splitlines()[-12:]


def run_gates(
    mappings: dict[str, list[str]],
    *,
    execution_root: Path | None = None,
) -> list[dict[str, Any]]:
    configured = _configured_gates()
    results: list[dict[str, Any]] = []
    for gate, covered in mappings.items():
        started = time.perf_counter()
        try:
            command, cwd, timeout_seconds = _command(
                gate,
                dict(configured[gate]),
                execution_root,
            )
            completed = subprocess.run(
                command,
                cwd=cwd,
                env={**os.environ, "CI": "1"},
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_seconds,
            )
            passed = completed.returncode == 0
            details = [] if passed else _tail(completed.stdout + "\n" + completed.stderr)
            result = {
                "name": gate,
                "kind": "product",
                "command": subprocess.list2cmdline(command),
                "status": "passed" if passed else "failed",
                "passed": passed,
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "covers": covered,
                "details": details,
            }
        except (OSError, ProductVerificationError, subprocess.TimeoutExpired) as error:
            result = {
                "name": gate,
                "kind": "product",
                "command": "",
                "status": "failed",
                "passed": False,
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "covers": covered,
                "details": [str(error)],
            }
        results.append(result)
        if not result["passed"]:
            break
    return results


def validate_evidence(task_id: str, path: Path) -> list[str]:
    errors: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"task evidence missing: {path}"]
    except (json.JSONDecodeError, OSError) as error:
        return [f"task evidence is unreadable: {error}"]
    if not isinstance(payload, dict):
        return ["task evidence must be a JSON object"]

    try:
        criteria, mappings = verification_contract(task_id)
        profile = verification_profile(task_id)
        validate_configured_gates(mappings, profile)
        fingerprints = evidence_fingerprints(task_id, criteria, mappings, profile)
    except (ProductVerificationError, OSError, ValueError) as error:
        errors.append(str(error))
        return errors

    if payload.get("schema_version") != 2:
        errors.append("task evidence schema_version must be 2")
    if payload.get("task_id") != task_id:
        errors.append("task evidence task_id does not match")
    if payload.get("status") != "passed":
        errors.append("task evidence status must be passed")
    head = head_commit()
    if payload.get("source_commit") != head:
        errors.append("task evidence source_commit does not match HEAD")
    if payload.get("acceptance_criteria") != criteria:
        errors.append("task evidence acceptance criteria do not match the active spec")
    if payload.get("verification_profile") != profile:
        errors.append("task evidence verification_profile does not match the active spec")
    if payload.get("fingerprints") != fingerprints:
        errors.append("task evidence fingerprints do not match current verification inputs")
    execution = payload.get("execution")
    if not isinstance(execution, dict):
        errors.append("task evidence execution context must be an object")
    else:
        if execution.get("mode") != "git-worktree":
            errors.append("task evidence execution mode must be git-worktree")
        if execution.get("source_commit") != head:
            errors.append("task evidence execution commit does not match HEAD")
        if execution.get("cleanup_status") != "passed":
            errors.append("task evidence isolated worktree cleanup must be passed")

    checks = payload.get("checks")
    if not isinstance(checks, list) or not checks:
        errors.append("task evidence checks must be a non-empty array")
    else:
        if any(not isinstance(check, dict) or check.get("status") != "passed" for check in checks):
            errors.append("every task evidence check must be passed")
        isolation = [
            check
            for check in checks
            if isinstance(check, dict) and check.get("kind") == "isolation"
        ]
        if len(isolation) != 1 or isolation[0].get("name") != "isolated-worktree":
            errors.append("task evidence must contain one passed isolated-worktree check")
        product = {
            str(check.get("name")): check
            for check in checks
            if isinstance(check, dict) and check.get("kind") == "product"
        }
        if set(product) != set(mappings):
            errors.append("task evidence product gates do not match the verification plan")
        elif len(product) != sum(
            1
            for check in checks
            if isinstance(check, dict) and check.get("kind") == "product"
        ):
            errors.append("task evidence contains duplicate product gates")
        else:
            for gate, covered in mappings.items():
                check = product[gate]
                if check.get("covers") != covered:
                    errors.append(f"task evidence coverage does not match for gate {gate}")
                if not check.get("command"):
                    errors.append(f"task evidence command missing for gate {gate}")
    try:
        ensure_source_clean()
    except ProductVerificationError as error:
        errors.append(str(error))
    return errors


def head_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def derived_task_state(task_id: str, path: Path) -> str:
    return "verified" if not validate_evidence(task_id, path) else "active"
