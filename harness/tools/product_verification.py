from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from .config import load_config, project_root
from .lifecycle import LifecycleError
from .lifecycle import documentation_contract as parse_documentation_contract
from .metadata import parse_front_matter, values_as_list
from .module_verification import (
    EXPECTED_MODULE_IDS,
    ModuleVerificationError,
    resolve_module_contract,
)
from .qualification import validate_task_qualification
from .result_reporting import (
    failure_details,
    failure_summary,
    parse_test_counts,
    summarize_checks,
    summarize_criteria,
)
from .summarizer import active_spec
from .verification_config import TOKEN_PATTERN, required_check_names

CRITERION_PATTERN = re.compile(r"^-\s+(AC-[1-9][0-9]*):\s+\S", re.MULTILINE)
GATE_PATTERN = re.compile(
    r"^-\s+([a-z0-9]+(?:-[a-z0-9]+)*)\s+=>\s+(AC-[1-9][0-9]*(?:\s*,\s*AC-[1-9][0-9]*)*)\s*$",
    re.MULTILINE,
)
MODULE_ID_PATTERN = re.compile(r"^M(?:0[1-9]|[1-9][0-9]+)$")
CASE_ID_PATTERN = re.compile(r"^M(?:0[1-9]|[1-9][0-9]+)-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
CASE_MAPPING_PATTERN = re.compile(
    r"^-\s+(AC-[1-9][0-9]*)\s+=>\s+"
    r"(M(?:0[1-9]|[1-9][0-9]+)-[A-Z0-9]+(?:-[A-Z0-9]+)*"
    r"(?:\s*,\s*M(?:0[1-9]|[1-9][0-9]+)-[A-Z0-9]+(?:-[A-Z0-9]+)*)*)\s*$"
)
SUBSUMPTION_PROOF_PREFIX = "HARNESS_RELEASE_PROOF "
TASK_EVIDENCE_FIELDS = frozenset(
    {
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


def _verification_plan_sections(body: str) -> tuple[str, str]:
    plan_matches = list(
        re.finditer(r"^# Verification plan[ \t]*$", body, re.MULTILINE)
    )
    if len(plan_matches) != 1:
        raise ProductVerificationError(
            "Verification plan must occur exactly once as a level-1 section"
        )
    plan_match = plan_matches[0]
    next_h1 = re.search(r"^# [^#]", body[plan_match.end() :], re.MULTILINE)
    plan_end = (
        plan_match.end() + next_h1.start() if next_h1 is not None else len(body)
    )
    plan = body[plan_match.end() : plan_end]
    headings = list(re.finditer(r"^## ([^#\r\n]+?)[ \t]*$", plan, re.MULTILINE))
    names = [match.group(1).strip() for match in headings]
    if names != ["Verification cases", "Gates"]:
        raise ProductVerificationError(
            "Verification plan must contain exactly '## Verification cases' then '## Gates'"
        )
    cases = plan[headings[0].end() : headings[1].start()].strip()
    gates = plan[headings[1].end() :].strip()
    if not cases or not gates:
        raise ProductVerificationError(
            "Verification cases and Gates must both be non-empty"
        )
    return cases, gates


def verification_contract(task_id: str) -> tuple[list[str], dict[str, list[str]]]:
    path = active_spec(task_id)
    if not path.is_file():
        raise ProductVerificationError(f"active spec not found: {path}")
    _, body = parse_front_matter(path)
    acceptance = _section(body, "Acceptance criteria")
    _, verification = _verification_plan_sections(body)

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


def verification_case_plan(
    task_id: str,
    criteria: list[str] | None = None,
) -> dict[str, list[str]]:
    """Parse the structural AC-to-module-case mapping without resolving case IDs."""
    path = active_spec(task_id)
    if not path.is_file():
        raise ProductVerificationError(f"active spec not found: {path}")
    metadata, body = parse_front_matter(path)
    case_section, _ = _verification_plan_sections(body)
    planned_modules = values_as_list(metadata.get("planned_modules"))
    if any(not MODULE_ID_PATTERN.fullmatch(value) for value in planned_modules):
        raise ProductVerificationError("planned_modules must contain stable module IDs")
    if len(planned_modules) != len(set(planned_modules)):
        raise ProductVerificationError("planned_modules must not contain duplicates")
    allowed_modules = set(EXPECTED_MODULE_IDS) | set(planned_modules)
    known = set(criteria if criteria is not None else verification_contract(task_id)[0])
    mappings: dict[str, list[str]] = {}
    for line in case_section.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = CASE_MAPPING_PATTERN.fullmatch(stripped)
        if match is None:
            raise ProductVerificationError(
                "Verification cases must use '- AC-N => M01-CASE-ID, M02-CASE-ID' entries"
            )
        criterion = match.group(1)
        if criterion in mappings:
            raise ProductVerificationError(
                f"acceptance criterion mapped more than once in Verification cases: {criterion}"
            )
        case_ids = [value.strip() for value in match.group(2).split(",")]
        if len(case_ids) != len(set(case_ids)):
            raise ProductVerificationError(
                f"Verification cases contains duplicate case IDs for {criterion}"
            )
        if not all(CASE_ID_PATTERN.fullmatch(case_id) for case_id in case_ids):
            raise ProductVerificationError(
                f"Verification cases contains an invalid case ID for {criterion}"
            )
        case_modules = {case_id.split("-", 1)[0] for case_id in case_ids}
        unknown_modules = sorted(case_modules - allowed_modules)
        if unknown_modules:
            raise ProductVerificationError(
                "Verification cases references modules that are neither current nor planned: "
                + ", ".join(unknown_modules)
            )
        mappings[criterion] = case_ids
    if not mappings:
        raise ProductVerificationError(
            "Verification cases must map every acceptance criterion to a module case"
        )
    unknown = sorted(set(mappings) - known)
    missing = sorted(known - set(mappings))
    if unknown:
        raise ProductVerificationError(
            f"Verification cases references unknown criteria: {', '.join(unknown)}"
        )
    if missing:
        raise ProductVerificationError(
            f"Acceptance criteria lack a Verification cases mapping: {', '.join(missing)}"
        )
    return mappings


def resolved_verification_cases(
    task_id: str,
    criteria: list[str],
    gate_mappings: dict[str, list[str]],
) -> dict[str, Any]:
    """Resolve AC case IDs against the current module contract and gate plan."""
    planned = verification_case_plan(task_id, criteria)
    from . import impact
    from .module_verification import STRUCTURE_ONLY
    try:
        contract = resolve_module_contract(
            project_root(),
            registered_gates=set(_configured_gates()),
            **({"collected_tests": STRUCTURE_ONLY} if impact.enabled() else {}),
        )
    except ModuleVerificationError as error:
        raise ProductVerificationError(
            "module verification contract is invalid: " + "; ".join(error.details)
        ) from error
    indexed = contract["case_index"]
    resolved_criteria: list[dict[str, Any]] = []
    for criterion in criteria:
        selected_gates = [
            gate for gate, covered in gate_mappings.items() if criterion in covered
        ]
        resolved_cases: list[dict[str, Any]] = []
        for case_id in planned[criterion]:
            case = indexed.get(case_id)
            if not isinstance(case, dict):
                raise ProductVerificationError(
                    f"Verification cases references an unresolved module case: {case_id}"
                )
            required_gates = [str(value) for value in case["required_gates"]]
            satisfaction = _requirement_report(required_gates, selected_gates)
            if satisfaction["missing"]:
                raise ProductVerificationError(
                    f"{criterion} gate plan does not cover {case_id} required gates: "
                    + ", ".join(satisfaction["missing"])
                )
            resolved_cases.append(
                {
                    "id": case_id,
                    "module_id": case["module_id"],
                    "module_name": case["module_name"],
                    "priority": case["priority"],
                    "scenario": case["scenario"],
                    "expectations": case["expectations"],
                    "required_gates": required_gates,
                    "test_refs": case["test_refs"],
                    "gate_satisfaction": satisfaction["satisfied"],
                }
            )
        resolved_criteria.append(
            {
                "criterion": criterion,
                "selected_gates": selected_gates,
                "cases": resolved_cases,
            }
        )
    return {
        "schema_version": 1,
        "contract_id": contract["contract"]["contract_id"],
        "contract_sha256": contract["digest"],
        "criteria": resolved_criteria,
    }


def _configured_gates() -> dict[str, Any]:
    verification = load_config().get("verification", {})
    gates = verification.get("gates", {})
    from .impact import definitions
    return definitions(dict(gates)) if isinstance(gates, dict) else {}


def required_task_checks() -> list[str]:
    try:
        return required_check_names(load_config())
    except ValueError as error:
        raise ProductVerificationError(str(error)) from error


def _load_subsumption_contract(
    owner_gate: str,
    configured: dict[str, Any] | None = None,
    execution_root: Path | None = None,
) -> dict[str, Any] | None:
    if configured is None:
        configured = _configured_gates()
    definition = configured.get(owner_gate)
    if not isinstance(definition, dict):
        raise ProductVerificationError(f"gate {owner_gate} definition must be a table")
    raw_path = definition.get("subsumption_contract")
    if raw_path is None:
        return None
    if not isinstance(raw_path, str) or not raw_path.endswith(".json"):
        raise ProductVerificationError(
            f"gate {owner_gate} subsumption_contract must be a project-relative JSON path"
        )
    if (
        not raw_path
        or raw_path.startswith("/")
        or "\\" in raw_path
        or any(part in {"", ".", ".."} for part in raw_path.split("/"))
    ):
        raise ProductVerificationError(
            f"gate {owner_gate} has unsafe subsumption contract path: {raw_path}"
        )
    root = (execution_root or project_root()).resolve()
    path = root.joinpath(*raw_path.split("/")).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ProductVerificationError(
            f"gate {owner_gate} subsumption contract is missing or outside the project"
        )
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProductVerificationError(
            f"gate {owner_gate} subsumption contract is unreadable: {error}"
        ) from error
    if not isinstance(payload, dict):
        raise ProductVerificationError(
            f"gate {owner_gate} subsumption contract must be an object"
        )
    if payload.get("schema_version") != 1 or payload.get("owner_gate") != owner_gate:
        raise ProductVerificationError(
            f"gate {owner_gate} subsumption contract identity is invalid"
        )
    raw_stages = payload.get("stages")
    if not isinstance(raw_stages, list) or not raw_stages:
        raise ProductVerificationError(
            f"gate {owner_gate} subsumption contract stages must be a non-empty array"
        )

    stages: list[dict[str, Any]] = []
    seen_gates: set[str] = set()
    seen_stages: set[str] = set()
    for index, item in enumerate(raw_stages, start=1):
        if not isinstance(item, dict) or set(item) != {"gate", "stage", "cwd", "command"}:
            raise ProductVerificationError(
                f"gate {owner_gate} subsumption stage {index} has invalid fields"
            )
        gate = item.get("gate")
        stage = item.get("stage")
        cwd = item.get("cwd")
        command = item.get("command")
        if not isinstance(gate, str) or TOKEN_PATTERN.fullmatch(gate) is None:
            raise ProductVerificationError(
                f"gate {owner_gate} subsumption stage {index} has invalid gate"
            )
        if not isinstance(stage, str) or TOKEN_PATTERN.fullmatch(stage) is None:
            raise ProductVerificationError(
                f"gate {owner_gate} subsumption stage {index} has invalid stage"
            )
        if gate == owner_gate:
            raise ProductVerificationError(f"gate {owner_gate} cannot subsume itself")
        if gate in seen_gates or stage in seen_stages:
            raise ProductVerificationError(
                f"gate {owner_gate} subsumption contract has duplicate gate or stage"
            )
        if (
            not isinstance(cwd, str)
            or not cwd
            or "\\" in cwd
            or cwd.startswith("/")
            or (cwd != "." and any(part in {"", ".", ".."} for part in cwd.split("/")))
        ):
            raise ProductVerificationError(
                f"gate {owner_gate} subsumption stage {stage} has unsafe cwd"
            )
        if (
            not isinstance(command, list)
            or not command
            or not all(isinstance(value, str) and value for value in command)
        ):
            raise ProductVerificationError(
                f"gate {owner_gate} subsumption stage {stage} has invalid command"
            )
        child = configured.get(gate)
        if not isinstance(child, dict):
            raise ProductVerificationError(
                f"gate {owner_gate} subsumes unregistered gate: {gate}"
            )
        if child.get("command") != command or str(child.get("cwd", ".")) != cwd:
            raise ProductVerificationError(
                f"gate {owner_gate} subsumption stage {stage} does not match registered gate {gate}"
            )
        seen_gates.add(gate)
        seen_stages.add(stage)
        stages.append({"gate": gate, "stage": stage, "cwd": cwd, "command": command})
    return {
        "path": raw_path,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "stages": stages,
    }


def _selected_subsumption_contracts(
    selected_gates: list[str] | dict[str, Any],
    *,
    execution_root: Path | None = None,
) -> dict[str, dict[str, Any]]:
    configured = _configured_gates()
    contracts: dict[str, dict[str, Any]] = {}
    for gate in selected_gates:
        contract = _load_subsumption_contract(gate, configured, execution_root)
        if contract is not None:
            contracts[gate] = contract
    return contracts


def configured_subsumption_contracts(
    execution_root: Path | None = None,
) -> dict[str, dict[str, Any]]:
    configured = _configured_gates()
    return _selected_subsumption_contracts(
        list(configured),
        execution_root=execution_root,
    )


def _requirement_report(
    required_gates: list[str] | set[str],
    selected_gates: list[str] | dict[str, Any],
) -> dict[str, Any]:
    selected = list(selected_gates)
    contracts = _selected_subsumption_contracts(selected)
    satisfied: list[dict[str, str]] = []
    missing: list[str] = []
    for required in sorted(set(required_gates)):
        if required in selected:
            satisfied.append(
                {"gate": required, "satisfied_by": required, "mode": "direct"}
            )
            continue
        owner = next(
            (
                gate
                for gate in selected
                if any(
                    item["gate"] == required
                    for item in contracts.get(gate, {}).get("stages", [])
                )
            ),
            None,
        )
        if owner is None:
            missing.append(required)
        else:
            satisfied.append(
                {"gate": required, "satisfied_by": owner, "mode": "subsumed"}
            )
    return {"satisfied": satisfied, "missing": missing}


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


def verification_escalation(task_id: str) -> str:
    path = active_spec(task_id)
    if not path.is_file():
        raise ProductVerificationError(f"active spec not found: {path}")
    metadata, _ = parse_front_matter(path)
    raw = metadata.get("verification_escalation")
    if raw in (None, "", []):
        return ""
    reason = str(raw).strip()
    if not reason or "\n" in reason or "\r" in reason:
        raise ProductVerificationError("verification_escalation must be a single line")
    return reason


def _bundle_gates(configured: dict[str, Any] | None = None) -> set[str]:
    if configured is None:
        configured = _configured_gates()
    bundles: set[str] = set()
    for name, definition in configured.items():
        if isinstance(definition, dict) and definition.get("subsumption_contract"):
            bundles.add(name)
    return bundles


def _criteria_from_mappings(mappings: dict[str, list[str]]) -> list[str]:
    seen: list[str] = []
    for covered in mappings.values():
        for item in covered:
            if item not in seen:
                seen.append(item)
    return seen


def validate_mapping_policy(
    criteria: list[str],
    mappings: dict[str, list[str]],
    *,
    task_id: str | None = None,
) -> None:
    bundles = _bundle_gates()
    selected_bundles = [gate for gate in mappings if gate in bundles]
    if len(criteria) > 1 and selected_bundles:
        missing: list[str] = []
        for criterion in criteria:
            leaf = [
                gate
                for gate, covered in mappings.items()
                if criterion in covered and gate not in bundles
            ]
            if not leaf:
                missing.append(criterion)
        if missing:
            raise ProductVerificationError(
                "bundle gates cannot be the only mapping for "
                f"{', '.join(missing)} when multiple acceptance criteria exist"
            )
    if task_id is None:
        return
    required = set(derived_gate_requirements(task_id)["required_gates"])
    extra_bundles = [gate for gate in selected_bundles if gate not in required]
    if extra_bundles and not verification_escalation(task_id):
        raise ProductVerificationError(
            "selecting bundle gates above the risk floor requires "
            f"verification_escalation: {', '.join(extra_bundles)}"
        )


def lint_task_contract(task_id: str) -> tuple[list[str], dict[str, list[str]], str]:
    from . import summarizer

    path = active_spec(task_id)
    summarizer.ensure_spec_in_git_history(path)
    criteria, mappings = verification_contract(task_id)
    verification_case_plan(task_id, criteria)
    profile = verification_profile(task_id)
    # Specify precedes implementation: planned cases and an impact plan may not
    # exist yet. Execution still resolves and enforces the complete impact plan.
    from . import impact
    validate_configured_gates(mappings, profile, None if impact.enabled() else task_id, criteria)
    if impact.enabled() and profile != "release" and _bundle_gates() & set(mappings):
        raise ProductVerificationError("bundle gates require an explicit release task")
    return criteria, mappings, profile


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
    criteria: list[str] | None = None,
) -> None:
    unknown = sorted(set(mappings) - set(_configured_gates()))
    if unknown:
        raise ProductVerificationError(
            f"Verification plan uses unregistered gates: {', '.join(unknown)}"
        )
    _selected_subsumption_contracts(mappings)
    validate_mapping_policy(
        criteria or _criteria_from_mappings(mappings),
        mappings,
        task_id=task_id,
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
    profile_report = _requirement_report(required, mappings)
    missing = profile_report["missing"]
    if missing:
        raise ProductVerificationError(
            f"verification profile {profile} requires gates: {', '.join(missing)}"
        )
    if task_id is None:
        return
    derived = derived_gate_requirements(task_id)
    derived_report = _requirement_report(derived["required_gates"], mappings)
    missing_derived = derived_report["missing"]
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
    verification_cases: dict[str, Any] | None = None,
) -> dict[str, str]:
    path = active_spec(task_id)
    gates = _configured_gates()
    profiles = _configured_profiles()
    derived = derived_gate_requirements(task_id)
    gate_contract = {
        "profile": {profile: profiles[profile]},
        "gates": {gate: gates[gate] for gate in mappings},
        "isolation": load_config().get("verification", {}).get("isolation", {}),
        "risk_derivation": derived,
        "requirement_satisfaction": {
            "profile": _requirement_report(
                {str(value) for value in profiles[profile].get("required_gates", [])},
                mappings,
            ),
            "risk": _requirement_report(derived["required_gates"], mappings),
        },
        "subsumption_contracts": _selected_subsumption_contracts(mappings),
        "required_task_checks": required_task_checks(),
    }
    verification_contract = {
        "profile": profile,
        "acceptance_criteria": criteria,
        "mappings": mappings,
        "verification_escalation": verification_escalation(task_id),
    }
    if verification_cases is not None:
        verification_contract["verification_cases"] = verification_cases
    documentation = documentation or documentation_report(task_id)
    qualification_errors, qualification_binding = validate_task_qualification(task_id)
    if qualification_errors:
        raise ProductVerificationError(
            "qualification manifest is not valid: " + "; ".join(qualification_errors)
        )
    documentation_input = {
        "impact": documentation["impact"],
        "reason": documentation["reason"],
        "targets": documentation["targets"],
    }
    fingerprints = {
        "source_tree": _git_value("rev-parse", "HEAD^{tree}"),
        "active_spec_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "verification_contract_sha256": _canonical_hash(verification_contract),
        "gate_config_sha256": _canonical_hash(gate_contract),
        "documentation_contract_sha256": _canonical_hash(documentation_input),
        "documentation_targets_sha256": _canonical_hash(
            documentation.get("target_blobs", {})
        ),
    }
    if verification_cases is not None:
        contract_sha256 = verification_cases.get("contract_sha256")
        if not isinstance(contract_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", contract_sha256
        ):
            raise ProductVerificationError(
                "resolved verification cases have an invalid contract digest"
            )
        fingerprints["module_contract_sha256"] = contract_sha256
    if qualification_binding is not None:
        fingerprints["qualification_manifest_sha256"] = _canonical_hash(
            qualification_binding
        )
    return fingerprints


def source_changes(extra_paths: list[str] | None = None) -> list[str]:
    config = load_config()
    raw_paths = config.get("verification", {}).get("source_paths", [])
    from .impact import current_plan, source_inputs
    plan = current_plan.get()
    paths = source_inputs(plan) if plan is not None and not plan.get("release") else [str(value) for value in raw_paths]
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
    from . import impact
    if impact.enabled():
        plan = impact.current_plan.get() or impact.build_plan(task_id)
        return {"paths": plan["paths"], "routes": [], "required_gates": plan["required_gates"], "impact_sha256": _canonical_hash(plan)}
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


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        completed = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            creationflags=subprocess.CREATE_NO_WINDOW,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        output = f"{completed.stdout}\n{completed.stderr}"
        return str(pid) in output and "No tasks" not in output
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def kill_process_tree(pid: int) -> None:
    if pid <= 0:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            creationflags=subprocess.CREATE_NO_WINDOW,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return
    try:
        os.killpg(pid, signal.SIGKILL)
    except OSError:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            return


def _run_supervised_command(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    from .run_artifacts import LOG_LIMIT, log_path
    from .verification_inputs import controlled_environment
    merged_env = controlled_environment()
    if env:
        merged_env.update(env)
    popen_kwargs: dict[str, Any] = {
        "args": command,
        "cwd": cwd,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "env": merged_env,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    else:
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen(**popen_kwargs)
    chunks: list[str] = []
    diagnostic_path = log_path.get()
    if diagnostic_path is not None:
        diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
    diagnostic = diagnostic_path.open("wb") if diagnostic_path is not None else None
    logged = 0

    def read_stdout() -> None:
        nonlocal logged
        stream = proc.stdout
        if stream is None:
            return
        try:
            for line in iter(stream.readline, ""):
                chunks.append(line)
                if diagnostic is not None and logged < LOG_LIMIT:
                    data = line.encode("utf-8")[:LOG_LIMIT - logged]
                    diagnostic.write(data)
                    diagnostic.flush()
                    logged += len(data)
                if diagnostic_path is not None:
                    continue
                try:
                    sys.stdout.write(line)
                except UnicodeEncodeError:
                    encoding = sys.stdout.encoding or "utf-8"
                    safe = line.encode(encoding, errors="backslashreplace")
                    output_buffer = getattr(sys.stdout, "buffer", None)
                    if output_buffer is not None:
                        output_buffer.write(safe)
                    else:  # pragma: no cover - StringIO-style fallback
                        sys.stdout.write(safe.decode(encoding))
                sys.stdout.flush()
        finally:
            stream.close()

    reader = threading.Thread(target=read_stdout, name="harness-gate-stdout", daemon=True)
    reader.start()
    timed_out = False
    try:
        proc.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_process_tree(proc.pid)
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    except BaseException:
        kill_process_tree(proc.pid)
        proc.wait(timeout=15)
        reader.join(timeout=5)
        if diagnostic is not None:
            diagnostic.close()
        raise
    reader.join(timeout=5)
    if diagnostic is not None:
        diagnostic.close()
    output = "".join(chunks)
    if timed_out:
        raise subprocess.TimeoutExpired(command, timeout_seconds, output=output)
    return subprocess.CompletedProcess(
        command,
        proc.returncode if proc.returncode is not None else 1,
        output,
        "",
    )


def _verified_subsumption(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_sha256": contract["sha256"],
        "verified": [
            {"gate": item["gate"], "stage": item["stage"]}
            for item in contract["stages"]
        ],
    }


def _configured_command_text(definition: dict[str, Any]) -> str:
    raw = definition.get("command")
    if not isinstance(raw, list) or not raw or not all(
        isinstance(value, str) and value for value in raw
    ):
        raise ProductVerificationError("gate command must be a non-empty argv array")
    return subprocess.list2cmdline(raw)


def _parse_subsumption_proof(
    stdout: str,
    contract: dict[str, Any],
    owner_gate: str,
) -> dict[str, Any]:
    lines = [
        line[len(SUBSUMPTION_PROOF_PREFIX) :]
        for line in stdout.splitlines()
        if line.startswith(SUBSUMPTION_PROOF_PREFIX)
    ]
    if len(lines) != 1:
        raise ProductVerificationError(
            f"gate {owner_gate} must emit exactly one terminal subsumption proof"
        )
    try:
        payload = json.loads(lines[0])
    except json.JSONDecodeError as error:
        raise ProductVerificationError(
            f"gate {owner_gate} emitted malformed subsumption proof"
        ) from error
    expected_completed = [
        {"gate": item["gate"], "stage": item["stage"]}
        for item in contract["stages"]
    ]
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "owner_gate",
        "contract_sha256",
        "completed",
    }:
        raise ProductVerificationError(
            f"gate {owner_gate} subsumption proof fields are invalid"
        )
    if (
        payload.get("schema_version") != 1
        or payload.get("owner_gate") != owner_gate
        or payload.get("contract_sha256") != contract["sha256"]
        or payload.get("completed") != expected_completed
    ):
        raise ProductVerificationError(
            f"gate {owner_gate} subsumption proof does not match its stage contract"
        )
    return _verified_subsumption(contract)


def classify_failure(output: str) -> str:
    lowered = output.lower()
    if "eaddrinuse" in lowered or "already used" in lowered:
        return "port-conflict"
    if "error collecting" in lowered or "no tests collected" in lowered:
        return "collection"
    if "assertionerror" in lowered or "assert " in lowered:
        return "assertion"
    if "failed to start" in lowered or "cannot find module" in lowered:
        return "startup"
    return "nonzero-exit"


def run_gates(
    mappings: dict[str, list[str]],
    *,
    execution_root: Path | None = None,
    gate_callback: Any = None,
    artifact_root: Path | None = None,
    selected_refs_file: Path | None = None,
) -> list[dict[str, Any]]:
    from .run_artifacts import log_path
    configured = _configured_gates()
    results: list[dict[str, Any]] = []
    # Execute bundle owners before explicit children; skip only after a real proof.
    ordered = sorted(mappings, key=lambda gate: 0 if configured[gate].get("subsumption_contract") else 1)
    proven_children: dict[str, str] = {}
    for gate in ordered:
        covered = mappings[gate]
        if gate in proven_children:
            if gate_callback is not None:
                gate_callback(gate, None)
            result = {"name": gate, "kind": "product", "command": _configured_command_text(configured[gate]),
                      "status": "passed", "passed": True, "duration_ms": 0, "covers": covered,
                      "details": [], "result": {"exit_code": 0},
                      "provenance": {"mode": "subsumed", "parent_gate": proven_children[gate]}}
            if gate_callback is not None:
                gate_callback(gate, result)
            results.append(result)
            continue
        if gate_callback is not None:
            gate_callback(gate, None)
        log_token = log_path.set(artifact_root / gate / "output.log" if artifact_root else None)
        started = time.perf_counter()
        try:
            contract = _load_subsumption_contract(
                gate,
                configured,
                execution_root,
            )
            command, cwd, timeout_seconds = _command(
                gate,
                dict(configured[gate]),
                execution_root,
            )
            if selected_refs_file is not None:
                if "harness.tools.selected_tests" not in command:
                    raise ProductVerificationError("diagnosis requires an exact selected runner")
                command.extend(["--selection", str(selected_refs_file)])
            completed = _run_supervised_command(
                command,
                cwd=cwd,
                timeout_seconds=timeout_seconds,
            )
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            passed = completed.returncode == 0
            redactions = [str(execution_root)] if execution_root is not None else []
            test_counts = parse_test_counts(completed.stdout, completed.stderr)
            structured_result: dict[str, Any] = {"exit_code": completed.returncode, "output_bytes": len((completed.stdout + completed.stderr).encode("utf-8"))}
            if test_counts is not None:
                structured_result["test_counts"] = test_counts
            selection_rows = [json.loads(line.removeprefix("HARNESS_SELECTION "))
                              for line in completed.stdout.splitlines() if line.startswith("HARNESS_SELECTION ")]
            if selection_rows:
                structured_result["selection_counts"] = {
                    key: sum(row[key] for row in selection_rows) for key in ("collected", "executed")}
            stages = [json.loads(line.removeprefix("HARNESS_STAGE ")) for line in completed.stdout.splitlines()
                      if line.startswith("HARNESS_STAGE ")]
            if stages:
                structured_result["stages"] = stages
            if artifact_root is not None:
                structured_result["log"] = str(artifact_root / gate / "output.log")
            proof_error: ProductVerificationError | None = None
            if passed and contract is not None:
                try:
                    structured_result["subsumption"] = _parse_subsumption_proof(
                        completed.stdout,
                        contract,
                        gate,
                    )
                except ProductVerificationError as error:
                    proof_error = error
                    passed = False
            if proof_error is not None:
                details = [str(proof_error)]
                structured_result["failure"] = {
                    "kind": "subsumption-proof",
                    "summary": str(proof_error)[:300],
                }
            elif not passed:
                details = failure_details(
                    completed.stdout,
                    completed.stderr,
                    redactions=redactions,
                )
                structured_result["failure"] = {
                    "kind": next((row["phase"] for row in reversed(stages) if row["status"] == "failed"), "nonzero-exit"),
                    "source": "selected-runner" if stages else "gate-runner",
                    "hint": classify_failure(completed.stdout + completed.stderr),
                    "summary": failure_summary(
                        completed.stdout,
                        completed.stderr,
                        redactions=redactions,
                    ),
                }
            else:
                details = []
            result = {
                "name": gate,
                "kind": "product",
                "command": _configured_command_text(dict(configured[gate])),
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
                        "kind": "startup",
                        "summary": str(error)[:300],
                    },
                },
            }
        log_path.reset(log_token)
        if result["passed"] and result.get("result", {}).get("subsumption"):
            for child in result["result"]["subsumption"]["verified"]:
                proven_children[child["gate"]] = gate
        if gate_callback is not None:
            gate_callback(gate, result)
        results.append(result)
        if not result["passed"]:
            break
    return results


def validate_evidence(task_id: str, path: Path, *, prepared: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"task evidence missing: {path}"]
    except (json.JSONDecodeError, OSError) as error:
        return [f"task evidence is unreadable: {error}"]
    if not isinstance(payload, dict):
        return ["task evidence must be a JSON object"]
    missing_fields = sorted(TASK_EVIDENCE_FIELDS - set(payload))
    unexpected_fields = sorted(set(payload) - TASK_EVIDENCE_FIELDS)
    if missing_fields:
        errors.append("task evidence missing fields: " + ", ".join(missing_fields))
    if unexpected_fields:
        errors.append(
            "task evidence contains unexpected fields: "
            + ", ".join(unexpected_fields)
        )

    try:
        if prepared is None and isinstance(payload.get("execution"), dict) and "receipt" in payload["execution"]:
            from .verification_resume import authenticate
            prepared = authenticate(task_id, path)
        if prepared is not None:
            criteria, mappings = prepared["criteria"], prepared["mappings"]
            profile, documentation = prepared["profile"], prepared["documentation"]
            verification_cases, fingerprints = prepared["cases"], prepared["fingerprints"]
        else:
            criteria, mappings = verification_contract(task_id)
            profile = verification_profile(task_id)
            validate_configured_gates(mappings, profile, task_id, criteria)
            documentation = documentation_report(task_id)
            verification_cases = resolved_verification_cases(task_id, criteria, mappings)
            fingerprints = evidence_fingerprints(
                task_id,
                criteria,
                mappings,
                profile,
                documentation,
                verification_cases,
            )
    except (ProductVerificationError, OSError, ValueError) as error:
        errors.append(str(error))
        return errors

    if type(payload.get("schema_version")) is not int or payload.get("schema_version") != 2:
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
    if payload.get("verification_cases") != verification_cases:
        errors.append(
            "task evidence verification cases do not match the current module contract"
        )
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
            expected_criteria = summarize_criteria(criteria, mappings, checks)
            if payload.get("criteria_results") != expected_criteria:
                errors.append("task evidence criteria results do not match checks")
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
        elif isolation[0].get("result") != {"exit_code": 0}:
            errors.append("task evidence isolated-worktree result must have exit_code 0")
        for required_name in required_task_checks():
            required_matches = [
                check
                for check in checks
                if isinstance(check, dict)
                and check.get("name") == required_name
                and check.get("kind") not in {"product", "isolation"}
            ]
            if len(required_matches) != 1:
                errors.append(
                    "task evidence must contain exactly one global required check: "
                    f"{required_name}"
                )
            elif required_matches[0].get("status") != "passed":
                errors.append(
                    f"task evidence required check must be passed: {required_name}"
                )
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
                from .impact import definitions
                configured = definitions(_configured_gates(), prepared.get("impact") if prepared else None)
                expected_command = _configured_command_text(dict(configured[gate]))
                if check.get("command") != expected_command:
                    errors.append(f"task evidence command does not match for gate {gate}")
                contract = _load_subsumption_contract(gate, configured)
                result = check.get("result")
                if not isinstance(result, dict):
                    errors.append(f"task evidence result missing for gate {gate}")
                elif (
                    type(result.get("exit_code")) is not int
                    or result.get("exit_code") != 0
                    or "failure" in result
                ):
                    errors.append(
                        f"task evidence result must record zero exit for gate {gate}"
                    )
                actual_subsumption = (
                    result.get("subsumption") if isinstance(result, dict) else None
                )
                expected_subsumption = (
                    _verified_subsumption(contract) if contract is not None else None
                )
                if actual_subsumption != expected_subsumption:
                    errors.append(
                        f"task evidence subsumption proof does not match for gate {gate}"
                    )
    try:
        from .impact import activate
        with activate(prepared.get("impact") if prepared else None):
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
