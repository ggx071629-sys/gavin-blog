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
from .lifecycle import LifecycleError
from .lifecycle import documentation_contract as parse_documentation_contract
from .metadata import parse_front_matter
from .result_reporting import failure_summary, parse_test_counts, summarize_checks
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


def _configured_risk_routes() -> list[dict[str, Any]]:
    verification = load_config().get("verification", {})
    raw_routes = verification.get("risk_routes", [])
    if not isinstance(raw_routes, list):
        raise ProductVerificationError("verification.risk_routes must be an array")
    registered = set(_configured_gates())
    seen: set[str] = set()
    routes: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_routes, start=1):
        if not isinstance(raw, dict):
            raise ProductVerificationError(f"risk route {index} must be a table")
        route_id = str(raw.get("id", "")).strip()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", route_id):
            raise ProductVerificationError(f"risk route {index} has invalid id")
        if route_id in seen:
            raise ProductVerificationError(f"duplicate risk route id: {route_id}")
        seen.add(route_id)
        prefixes = raw.get("prefixes", [])
        files = raw.get("files", [])
        required_gates = raw.get("required_gates", [])
        if not all(isinstance(value, list) for value in (prefixes, files, required_gates)):
            raise ProductVerificationError(
                f"risk route {route_id} prefixes, files, and required_gates must be arrays"
            )
        normalized_prefixes = [str(value) for value in prefixes]
        normalized_files = [str(value) for value in files]
        normalized_gates = [str(value) for value in required_gates]
        if not normalized_prefixes and not normalized_files:
            raise ProductVerificationError(
                f"risk route {route_id} must declare prefixes or files"
            )
        if not normalized_gates:
            raise ProductVerificationError(
                f"risk route {route_id} must declare required_gates"
            )
        for prefix in normalized_prefixes:
            if (
                not prefix
                or not prefix.endswith("/")
                or prefix.startswith("/")
                or "\\" in prefix
                or any(part in {"", ".", ".."} for part in prefix[:-1].split("/"))
            ):
                raise ProductVerificationError(
                    f"risk route {route_id} has invalid project-relative prefix: {prefix}"
                )
        for file in normalized_files:
            if (
                not file
                or file.startswith("/")
                or file.endswith("/")
                or "\\" in file
                or any(part in {"", ".", ".."} for part in file.split("/"))
            ):
                raise ProductVerificationError(
                    f"risk route {route_id} has invalid project-relative file: {file}"
                )
        unknown = sorted(set(normalized_gates) - registered)
        if unknown:
            raise ProductVerificationError(
                f"risk route {route_id} uses unregistered gates: {', '.join(unknown)}"
            )
        routes.append(
            {
                "id": route_id,
                "prefixes": normalized_prefixes,
                "files": normalized_files,
                "required_gates": list(dict.fromkeys(normalized_gates)),
            }
        )
    return routes


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


def documentation_contract(task_id: str) -> dict[str, Any]:
    path = active_spec(task_id)
    if not path.is_file():
        raise ProductVerificationError(f"active spec not found: {path}")
    metadata, _ = parse_front_matter(path)
    try:
        return parse_documentation_contract(metadata)
    except LifecycleError as error:
        raise ProductVerificationError(str(error)) from error


def validate_configured_gates(
    mappings: dict[str, list[str]],
    profile: str | None = None,
    task_id: str | None = None,
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
    if task_id is None:
        return
    derived = derived_gate_requirements(task_id)
    missing_derived = sorted(set(derived["required_gates"]) - set(mappings))
    if missing_derived:
        triggers = []
        for route in derived["routes"]:
            if set(route["required_gates"]) & set(missing_derived):
                triggers.extend(route["matched_paths"])
        shown = ", ".join(sorted(set(triggers))[:5])
        suffix = " ..." if len(set(triggers)) > 5 else ""
        raise ProductVerificationError(
            "risk-derived verification requires gates: "
            f"{', '.join(missing_derived)}; triggered by {shown}{suffix}"
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
    documentation: dict[str, Any] | None = None,
) -> dict[str, str]:
    path = active_spec(task_id)
    gates = _configured_gates()
    profiles = _configured_profiles()
    gate_contract = {
        "profile": {profile: profiles[profile]},
        "gates": {gate: gates[gate] for gate in mappings},
        "isolation": load_config().get("verification", {}).get("isolation", {}),
        "risk_derivation": derived_gate_requirements(task_id),
    }
    verification_contract = {
        "profile": profile,
        "acceptance_criteria": criteria,
        "mappings": mappings,
    }
    documentation = documentation or documentation_report(task_id)
    documentation_input = {
        "impact": documentation["impact"],
        "reason": documentation["reason"],
        "targets": documentation["targets"],
    }
    return {
        "source_tree": _git_value("rev-parse", "HEAD^{tree}"),
        "active_spec_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "verification_contract_sha256": _canonical_hash(verification_contract),
        "gate_config_sha256": _canonical_hash(gate_contract),
        "documentation_contract_sha256": _canonical_hash(documentation_input),
        "documentation_targets_sha256": _canonical_hash(
            documentation.get("target_blobs", {})
        ),
    }


def source_changes(extra_paths: list[str] | None = None) -> list[str]:
    config = load_config()
    raw_paths = config.get("verification", {}).get("source_paths", [])
    paths = [str(value) for value in raw_paths]
    paths.extend(extra_paths or [])
    paths = list(dict.fromkeys(paths))
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


def ensure_source_clean(extra_paths: list[str] | None = None) -> None:
    changes = source_changes(extra_paths)
    if changes:
        shown = ", ".join(line[3:] for line in changes[:5])
        suffix = " ..." if len(changes) > 5 else ""
        raise ProductVerificationError(
            f"verification source has uncommitted changes: {shown}{suffix}"
        )


def _spec_introduction_commit(task_id: str) -> str:
    relative = active_spec(task_id).relative_to(project_root()).as_posix()
    commits = _git_value("log", "--diff-filter=A", "--format=%H", "--", relative)
    values = [line.strip() for line in commits.splitlines() if line.strip()]
    if not values:
        raise ProductVerificationError(
            "active spec introduction commit is unavailable in current Git history"
        )
    return values[-1]


def implementation_paths(task_id: str) -> list[str]:
    baseline = _spec_introduction_commit(task_id)
    changed = _git_value("diff", "--name-only", "-z", f"{baseline}..HEAD")
    return sorted(value for value in changed.split("\0") if value)


def derived_gate_requirements(task_id: str) -> dict[str, Any]:
    paths = implementation_paths(task_id)
    matched_routes: list[dict[str, Any]] = []
    required_gates: list[str] = []
    for route in _configured_risk_routes():
        prefixes = tuple(route["prefixes"])
        files = set(route["files"])
        matched = sorted(
            path for path in paths if path in files or path.startswith(prefixes)
        )
        if not matched:
            continue
        matched_routes.append(
            {
                "id": route["id"],
                "matched_paths": matched,
                "required_gates": route["required_gates"],
            }
        )
        required_gates.extend(route["required_gates"])
    return {
        "paths": paths,
        "routes": matched_routes,
        "required_gates": list(dict.fromkeys(required_gates)),
    }


def documentation_report(task_id: str) -> dict[str, Any]:
    contract = documentation_contract(task_id)
    targets = list(contract["targets"])
    ensure_source_clean(targets)
    report: dict[str, Any] = {
        "impact": contract["impact"],
        "reason": contract["reason"],
        "targets": targets,
        "baseline_commit": None,
        "target_blobs": {},
    }
    if contract["impact"] == "none":
        return report

    baseline = _spec_introduction_commit(task_id)
    report["baseline_commit"] = baseline
    blobs: dict[str, str] = {}
    for target in targets:
        try:
            blob = _git_value("rev-parse", f"HEAD:{target}")
        except ProductVerificationError as error:
            raise ProductVerificationError(
                f"documentation target must exist in HEAD: {target}"
            ) from error
        changed = _git_value(
            "diff", "--name-only", "-z", f"{baseline}..HEAD", "--", target
        )
        if target not in {value for value in changed.split("\0") if value}:
            raise ProductVerificationError(
                "documentation target has no committed change after the active spec "
                f"baseline: {target}"
            )
        blobs[target] = blob
    report["target_blobs"] = blobs
    return report


def _command(
    gate: str,
    definition: dict[str, Any],
    execution_root: Path | None = None,
) -> tuple[list[str], Path, int]:
    raw_command = definition.get("command")
    if not isinstance(raw_command, list) or not raw_command:
        raise ProductVerificationError(f"gate {gate} command must be a non-empty array")
    command = [str(value) for value in raw_command]
    root = (execution_root or project_root()).resolve()
    if command[0] == "{api_python}":
        candidates = [
            root / "apps" / "api" / ".venv" / "Scripts" / "python.exe",
            root / "apps" / "api" / ".venv" / "bin" / "python",
        ]
        interpreter = next((path for path in candidates if path.is_file()), None)
        if interpreter is None:
            raise ProductVerificationError(
                f"gate {gate} API virtual environment Python was not found"
            )
        command[0] = str(interpreter)
    elif command[0] == "{python}":
        command[0] = sys.executable
    else:
        executable = shutil.which(command[0])
        if executable is None:
            raise ProductVerificationError(
                f"gate {gate} executable was not found: {command[0]}"
            )
        command[0] = executable

    cwd = (root / str(definition.get("cwd", "."))).resolve()
    if not cwd.is_relative_to(root) or not cwd.is_dir():
        raise ProductVerificationError(f"gate {gate} cwd must be inside the project")
    timeout_seconds = definition.get("timeout_seconds", 900)
    if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
        raise ProductVerificationError(
            f"gate {gate} timeout_seconds must be a positive integer"
        )
    return command, cwd, timeout_seconds


def _tail(
    output: str,
    limit: int = 2000,
    *,
    redactions: list[str] | None = None,
) -> list[str]:
    from .result_reporting import clean_output

    output = clean_output(output, redactions=redactions)
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
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=timeout_seconds,
            )
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            passed = completed.returncode == 0
            redactions = [str(execution_root)] if execution_root is not None else []
            details = (
                []
                if passed
                else _tail(
                    completed.stdout + "\n" + completed.stderr,
                    redactions=redactions,
                )
            )
            test_counts = parse_test_counts(completed.stdout, completed.stderr)
            structured_result: dict[str, Any] = {"exit_code": completed.returncode}
            if test_counts is not None:
                structured_result["test_counts"] = test_counts
            if not passed:
                structured_result["failure"] = {
                    "kind": "nonzero-exit",
                    "summary": failure_summary(
                        completed.stdout,
                        completed.stderr,
                        redactions=redactions,
                    ),
                }
            result = {
                "name": gate,
                "kind": "product",
                "command": subprocess.list2cmdline(command),
                "status": "passed" if passed else "failed",
                "passed": passed,
                "duration_ms": duration_ms,
                "covers": covered,
                "details": details,
                "result": structured_result,
            }
        except subprocess.TimeoutExpired:
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            result = {
                "name": gate,
                "kind": "product",
                "command": "",
                "status": "failed",
                "passed": False,
                "duration_ms": duration_ms,
                "covers": covered,
                "details": ["gate timed out"],
                "result": {
                    "exit_code": None,
                    "failure": {
                        "kind": "timeout",
                        "summary": "gate exceeded its configured timeout",
                    },
                },
            }
        except (OSError, ProductVerificationError) as error:
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            result = {
                "name": gate,
                "kind": "product",
                "command": "",
                "status": "failed",
                "passed": False,
                "duration_ms": duration_ms,
                "covers": covered,
                "details": [str(error)],
                "result": {
                    "exit_code": None,
                    "failure": {
                        "kind": "execution-error",
                        "summary": str(error)[:300],
                    },
                },
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
        validate_configured_gates(mappings, profile, task_id)
        documentation = documentation_report(task_id)
        fingerprints = evidence_fingerprints(
            task_id, criteria, mappings, profile, documentation
        )
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
    if payload.get("documentation") != documentation:
        errors.append("task evidence documentation does not match current documentation inputs")
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
        checks_are_objects = all(isinstance(check, dict) for check in checks)
        if not checks_are_objects:
            errors.append("every task evidence check must be an object")
        else:
            try:
                expected_summary = summarize_checks(checks)
            except (TypeError, ValueError):
                errors.append("task evidence checks contain invalid summary values")
            else:
                if payload.get("summary") != expected_summary:
                    errors.append("task evidence summary does not match checks")
        if any(
            not isinstance(check, dict) or check.get("status") != "passed"
            for check in checks
        ):
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
        ensure_source_clean(list(documentation["targets"]))
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
