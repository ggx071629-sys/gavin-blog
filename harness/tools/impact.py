"""Explicit change impact, independent of directory-based release policy.

Ownership is a reviewable registry; decisions are task inputs, never shell commands.
Neither an ownership match nor a dependency edge selects tests by itself.
"""

from __future__ import annotations

import contextlib
import contextvars
import fnmatch
import json
from pathlib import PurePosixPath

from .config import load_config, project_root
from .module_verification import case_index, contract_digest, load_module_contract

current_plan = contextvars.ContextVar("impact_plan", default=None)


def enabled():
    return bool(load_config().get("verification", {}).get("impact"))


def safe_path(value):
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or ":" in value
        or PurePosixPath(value).is_absolute()
        or any(p in {"", ".", ".."} for p in value.split("/"))
    ):
        raise ValueError(f"unsafe impact path: {value!r}")
    return value


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate impact field: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def plan_path(task_id):
    from .summarizer import validate_task_id

    validate_task_id(task_id)
    return project_root() / "harness/verification/impact" / f"{task_id}.json"


def structural_path(path, task_id):
    """Only deterministic lifecycle assets are exempt from human impact review."""
    return (
        path.startswith("harness/") and path.endswith("/INDEX.md")
        or path == "harness/INDEX.md"
        or path == f"harness/specs/active/{task_id}.md"
        or path == f"harness/verification/impact/{task_id}.json"
        or path in {
            f"harness/verification/evidence/{task_id}.json",
            f"harness/verification/evidence/{task_id}.benchmark.json",
            f"harness/evolution/events/{task_id}--spec-completed.json",
        }
    )


def reviewed_dependencies(owner, decision, units):
    """Walk only affected edges; one flat decision per reachable consumer, including cycles."""
    dependencies = decision.get("dependencies", [])
    if not isinstance(dependencies, list):
        raise ValueError(f"impact gap: invalid dependent decisions for {owner}")  # noqa: TRY004 - CLI input contract
    by_unit = {}
    for dep in dependencies:
        if not isinstance(dep, dict) or dep.get("unit") in by_unit:
            raise ValueError(f"impact gap: duplicate/invalid dependent decision for {owner}")
        by_unit[dep.get("unit")] = dep
    pending, seen, entries = [owner], {owner}, []
    while pending:
        parent = pending.pop(0)
        for unit in units[parent].get("dependents", []):
            if unit in seen:
                continue
            seen.add(unit)
            dep = by_unit.get(unit)
            if dep is None:
                raise ValueError(f"impact gap: review every dependent of {parent}: {unit}")
            if type(dep.get("affected")) is not bool or not str(dep.get("reason", "")).strip():
                raise ValueError(f"impact gap: dependent decision requires affected and reason: {unit}")
            if not dep["affected"] and dep.get("cases"):
                raise ValueError("unaffected dependency cannot select cases")
            if dep["affected"]:
                entries.append((unit, dep))
                pending.append(unit)
    extra = set(by_unit) - (seen - {owner})
    if extra:
        raise ValueError(f"impact gap: unreachable dependent decisions: {sorted(extra)}")
    return entries


def build_plan(task_id, *, paths=None, root=None):
    from . import product_verification as pv

    root = root or project_root()
    registry = read_json(root / "harness/verification/impact/ownership.json")
    analysis = read_json(root / "harness/verification/impact" / f"{task_id}.json")
    if analysis.get("schema_version") != 1 or analysis.get("task_id") != task_id:
        raise ValueError("impact plan schema/task identity mismatch")
    units = registry["units"]
    indexed = case_index(load_module_contract(root))
    if not isinstance(units, dict) or not units:
        raise ValueError("impact ownership registry has no units")
    for unit_id, unit in units.items():
        if (
            not isinstance(unit, dict)
            or not unit.get("paths")
            or not isinstance(unit.get("cases"), list)
        ):
            raise ValueError(f"impact gap: invalid unit {unit_id}")
        if any(case not in indexed for case in unit["cases"]):
            raise ValueError(f"impact gap: unresolved cases in {unit_id}")
        dependents = unit.get("dependents", [])
        if (
            not isinstance(dependents, list)
            or len(dependents) != len(set(dependents))
            or any(d not in units for d in dependents)
        ):
            raise ValueError(f"impact gap: invalid dependent registry for {unit_id}")
    changes = analysis.get("changes", [])
    if not isinstance(changes, list):
        raise ValueError("invalid impact changes array")  # noqa: TRY004 - CLI input errors share one contract
    decisions = {}
    for change in changes:
        path = safe_path(change["path"])
        if path in decisions:
            raise ValueError(f"duplicate impact decision: {path}")
        decisions[path] = change
    actual = sorted(
        set(paths if paths is not None else pv.implementation_paths(task_id))
    )
    selected, reasons, reviewed = set(), {}, []
    for path in actual:
        safe_path(path)
        structural = structural_path(path, task_id)
        decision = decisions.get(path)
        if decision is None:
            if structural:
                reviewed.append(
                    {
                        "path": path,
                        "owner": "documentation",
                        "cases": [],
                        "reason": "deterministic lifecycle asset; metadata, links and indexes checked",
                    }
                )
                continue
            raise ValueError(f"impact gap: missing analysis for {path}")
        owner = decision.get("owner")
        owners = [u for u, value in units.items() if any(path == p or fnmatch.fnmatchcase(path, p) for p in value["paths"])]
        if len(owners) > 1:
            raise ValueError(f"impact gap: ambiguous ownership for {path}: {owners}")
        if owners != [owner]:
            raise ValueError(
                f"impact gap: unknown/mismatched ownership {owner!r} for {path}"
            )
        if not str(decision.get("reason", "")).strip():
            raise ValueError(f"impact gap: missing change rationale for {path}")
        entries = [(owner, decision), *reviewed_dependencies(owner, decision, units)]
        for unit, entry in entries:
            cases = entry.get("cases")
            if not isinstance(cases, list) or len(cases) != len(set(cases)):
                raise ValueError(f"invalid case selection for {path}")
            if not cases and not entry.get("no_test_reason"):
                raise ValueError(
                    f"impact gap: empty selection needs no_test_reason: {path}"
                )
            for case in cases:
                if case not in indexed or case not in units[unit]["cases"]:
                    raise ValueError(
                        f"impact gap: case {case} does not belong to {unit}"
                    )
                selected.add(case)
                reasons.setdefault(case, []).append(
                    {"path": path, "unit": unit, "reason": entry["reason"]}
                )
        reviewed.append(decision)
    criteria, mappings = pv.verification_contract(task_id)
    declared = {
        c
        for values in pv.verification_case_plan(task_id, criteria).values()
        for c in values
    }
    if declared != selected:
        raise ValueError(
            f"impact/spec case mismatch: missing={sorted(selected - declared)}, unexplained={sorted(declared - selected)}"
        )
    refs = {}
    for case in sorted(selected):
        for ref in indexed[case]["test_refs"]:
            key = (ref["kind"], ref["path"], ref["name"], ref["gate"], ref.get("config"), ref.get("project"), tuple(ref.get("title_path", [])))
            refs[key] = {k: ref[k] for k in ("kind", "path", "name", "gate", "config", "project", "title_path") if k in ref}
    gates = sorted({r["gate"] for r in refs.values()} | {"harness-integrity"})
    profile = pv.verification_profile(task_id)
    if profile != "release" and set(mappings) != set(gates):
        raise ValueError(
            f"ordinary impact plan requires exactly {gates}; release is a separate explicit profile"
        )
    return {
        "schema_version": 1,
        "task_id": task_id,
        "paths": actual,
        "changes": reviewed,
        "selected_cases": sorted(selected),
        "reasons": reasons,
        "excluded_cases": [
            {"case": c, "reason": "not affected by reviewed changes"}
            for c in sorted(set(indexed) - selected)
        ],
        "test_refs": [r for r in refs.values() if r["kind"] != "harness-check"],
        "check_refs": [r for r in refs.values() if r["kind"] == "harness-check"],
        "required_gates": gates,
        "contract_sha256": contract_digest(load_module_contract(root)),
        "analysis": analysis,
        "ownership": registry,
        "release": profile == "release",
    }


@contextlib.contextmanager
def activate(plan):
    token = current_plan.set(plan)
    try:
        yield
    finally:
        current_plan.reset(token)


def definitions(gates, plan=None):
    plan = plan if plan is not None else current_plan.get()
    if not plan or plan.get("release"):
        return gates
    result = dict(gates)
    for gate in plan["required_gates"]:
        if gate == "harness-integrity":
            result[gate] = {
                **gates[gate],
                "command": ["{python}", "-m", "tools.harness", "verify"],
            }
            continue
        result[gate] = {
            "cwd": ".",
            "command": [
                "{api_python}",
                "-m",
                "harness.tools.selected_tests",
                "--task",
                plan["task_id"],
                "--gate",
                gate,
            ],
            "timeout_seconds": gates[gate]["timeout_seconds"],
        }
    return result


def dependency_paths(mappings):
    plan = current_plan.get()
    if plan is None or plan.get("release"):
        return load_config()["verification"]["isolation"]["reuse_paths"]
    refs = [r for r in plan["test_refs"] if r["gate"] in mappings]
    paths = []
    if refs:
        paths.append("apps/api/.venv")
    if any(r["kind"] in {"vitest", "playwright"} for r in refs):
        paths.extend(["node_modules", "apps/web/node_modules"])
    return paths


def source_inputs(plan):
    """Inputs read by the control plane plus the selected runtime, not every app."""
    paths = [
        "AGENTS.md", "README.md", "harness/config.toml", "harness/tools",
        "harness/docs", "harness/workflows", "harness/specs/_sdd", "harness/specs/active",
        "harness/verification/checks", "harness/verification/impact",
        "harness/verification/qualifications", "harness/verification/qualification-cases",
        "harness/verification/README.md", "harness/verification/vdd",
        "apps/api/README.md", "apps/web/README.md", "packages/contracts/README.md",
        ".github", "package-lock.json", "apps/api/uv.lock",
    ]
    paths.extend(p for p in plan["paths"] if not p.startswith("harness/verification/evidence/"))
    paths.extend(r["path"] for r in plan["test_refs"])
    if any(r["path"].startswith("apps/api/") for r in plan["test_refs"]):
        paths.extend(["apps/api/app", "apps/api/tests/conftest.py", "apps/api/pyproject.toml"])
    if any(r["kind"] in {"vitest", "playwright"} for r in plan["test_refs"]):
        paths.extend(["apps/web", "packages", "package.json"])
    return list(dict.fromkeys(paths))
