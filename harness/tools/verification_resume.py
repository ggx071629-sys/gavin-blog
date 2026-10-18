"""Plan/execution/attestation orchestration; only successful cleaned attempts resume."""

from __future__ import annotations

import copy
import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import isolated_verification, run_artifacts, validator
from . import product_verification as pv
from . import verification_inputs as inputs
from .run_store import RunStore, StoreError, digest, latest_attempts

_PROCESS_RECEIPTS = {}
_PROCESS_PREPARED = {}


def prepare(task_id, *, collect=True, cases=None, identify=True):
    from . import impact
    plan = impact.build_plan(task_id) if impact.enabled() else None
    with impact.activate(plan):
        prepared = _prepare(task_id, collect=collect, cases=cases, identify=identify)
    if plan is not None:
        prepared["impact"] = plan
        prepared["reuse_enabled"] = bool(prepared["snapshot"].get("reusable", False))
    return prepared


def _prepare(
    task_id: str,
    *,
    collect: bool = True,
    cases: dict[str, Any] | None = None,
    identify: bool = True,
) -> dict[str, Any]:
    from . import lifecycle, summarizer

    if lifecycle.task_status(task_id) == "frozen":
        raise StoreError(f"{task_id} is frozen; resume it before verification")
    summarizer.ensure_spec_in_git_history(summarizer.active_spec(task_id))
    criteria, mappings = pv.verification_contract(task_id)
    profile = pv.verification_profile(task_id)
    pv.validate_configured_gates(mappings, profile, task_id, criteria)
    documentation = pv.documentation_report(task_id)
    pv.ensure_source_clean(
        [
            *documentation["targets"],
            "package.json",
            "package-lock.json",
            ".npmrc",
            ".github",
            ".gitattributes",
            ".gitignore",
        ]
    )
    from . import impact
    if collect or impact.enabled():
        cases = pv.resolved_verification_cases(task_id, criteria, mappings)
    fingerprints = pv.evidence_fingerprints(
        task_id, criteria, mappings, profile, documentation, cases
    )
    snapshot = (
        inputs.input_snapshot(mappings, fingerprints)
        if identify
        else {"head": pv.head_commit()}
    )
    return {
        "task_id": task_id,
        "criteria": criteria,
        "mappings": mappings,
        "profile": profile,
        "documentation": documentation,
        "cases": cases or {},
        "fingerprints": fingerprints,
        "snapshot": snapshot,
        "identity": digest(snapshot),
    }


def gate_plan(
    prepared: dict[str, Any], ledger: dict[str, Any], *, fresh: bool = False
) -> list[dict[str, Any]]:
    fresh = (
        fresh or prepared.get("reuse_enabled") is False or "release" in prepared["mappings"] or prepared["profile"] == "release"
    )
    latest = latest_attempts(ledger, prepared["identity"])
    rows = []
    for gate in prepared["mappings"]:
        attempt = latest.get(gate)
        old = any(a["gate"] == gate for run in ledger["runs"] for a in run["attempts"])
        reusable = bool(attempt and attempt["reusable"] and not fresh)
        state = (
            "reusable"
            if reusable
            else "fresh-required"
            if fresh
            else "failed"
            if attempt and attempt.get("check", {}).get("status") == "failed"
            else "invalidated"
            if old
            else "not-run"
        )
        reason = (
            "authenticated successful attempt with matching inputs and cleanup"
            if reusable
            else "reuse disabled; execute selected scope"
            if prepared.get("reuse_enabled") is False and fresh
            else "fresh execution required by request or release policy"
            if fresh
            else "latest attempt failed, interrupted, or cleanup did not pass"
            if attempt
            else "HEAD, plan, toolchain, dependencies or controlled environment changed"
            if old
            else "no authenticated attempt for current inputs"
        )
        if old and not attempt and not fresh:
            previous_run = next(
                run
                for run in reversed(ledger["runs"])
                if any(a["gate"] == gate for a in run["attempts"])
            )
            changed = [
                key
                for key, value in prepared["snapshot"].items()
                if digest(previous_run.get("inputs", {}).get(key)) != digest(value)
            ]
            reason = "input identity changed: " + ", ".join(changed)
        rows.append(
            {
                "gate": gate,
                "action": "reuse" if reusable else "execute",
                "state": state,
                "reason": reason,
                "attempt_id": attempt["id"] if attempt else None,
            }
        )
    return rows


def preview(task_id: str, *, fresh: bool = False) -> dict[str, Any]:
    store = RunStore(task_id)
    error = None
    try:
        ledger = store.read()
    except StoreError as exception:
        error = str(exception)
        ledger = {"runs": [], "aggregate": None}
    # Use authenticated collector resolution only for identical source inputs.
    aggregate = ledger.get("aggregate")
    cases = (
        aggregate["cases"]
        if aggregate
        else ledger["runs"][-1].get("cases")
        if ledger["runs"]
        else None
    )
    prepared = prepare(
        task_id, collect=False, cases=cases, identify=bool(ledger["runs"])
    )
    rows = gate_plan(prepared, ledger, fresh=fresh)
    from .execution_contracts import prerequisites
    from .selected_tests import execution_batches
    refs = prepared.get("impact", {}).get("test_refs", [])
    return {
        "task_id": task_id,
        "source_commit": prepared["snapshot"]["head"],
        "identity": prepared["identity"],
        "gates": rows,
        "impact": prepared.get("impact"),
        "prerequisites": prerequisites(refs),
        "batches": [{"consumers": group, "data_policy": "per-identity unless explicitly shared",
                     "resolution": "planned; collector has not run"} for group in execution_batches(refs)],
        "last_run": ({"state": ledger["runs"][-1]["state"],
                      "failures": [a.get("check", {}).get("result", {}).get("failure") for a in ledger["runs"][-1]["attempts"]
                                   if a.get("check", {}).get("status") == "failed"],
                      "duration_ms": sum(a.get("check", {}).get("duration_ms", 0) for a in ledger["runs"][-1]["attempts"])} if ledger["runs"] else None),
        "blocker": error,
        "next": f"python -m tools.harness verify {task_id}"
        + (" --fresh" if error else ""),
    }


def print_plan(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        print(f"[PLAN] {row['gate']}: {row['action']} ({row['reason']})", flush=True)


def execute(prepared, *, fresh=False):
    from .impact import activate
    with activate(prepared.get("impact")):
        return _execute(prepared, fresh=fresh)


def _execute(
    prepared: dict[str, Any], *, fresh: bool = False
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    store = RunStore(prepared["task_id"])
    ledger = store.recover(fresh=fresh)
    plan = gate_plan(prepared, ledger, fresh=fresh)
    if prepared.get("impact"):
        scope = prepared["impact"]
        print(f"[SCOPE] {len(scope['selected_cases'])} cases, {len(scope['test_refs'])} exact refs; {len(scope['excluded_cases'])} excluded cases")
    print_plan(plan)
    latest = latest_attempts(ledger, prepared["identity"])
    run_id = secrets.token_hex(16)
    run = {
        "id": run_id,
        "identity": prepared["identity"],
        "inputs": prepared["snapshot"],
        "cases": prepared["cases"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "state": "running",
        "cleanup_status": "pending",
        "attempts": [],
        "plan": plan,
        "selected_refs": prepared.get("impact", {}).get("test_refs", []),
    }
    ledger["runs"].append(run)
    ledger["aggregate"] = None
    store.write(ledger)
    run_artifacts.prune()
    artifact_root = store.root / "artifacts" / run_id
    missing = {
        row["gate"]: prepared["mappings"][row["gate"]]
        for row in plan
        if row["action"] == "execute"
    }
    reused = []
    for row in plan:
        if row["action"] == "reuse":
            previous = latest[row["gate"]]
            check = copy.deepcopy(previous["check"])
            check["duration_ms"] = 0
            check["provenance"] = {
                "mode": "reused",
                "run_id": previous["run_id"],
                "attempt_id": previous["id"],
            }
            reused.append(check)

    def observe(gate: str, check: dict[str, Any] | None) -> None:
        if check is None:
            run["attempts"].append(
                {
                    "id": secrets.token_hex(16),
                    "gate": gate,
                    "retry_of": latest.get(gate, {}).get("id"),
                    "check": {"status": "running"},
                }
            )
        else:
            attempt = run["attempts"][-1]
            check["provenance"] = {
                "mode": "executed",
                **check.get("provenance", {}),
                "run_id": run_id,
                "attempt_id": attempt["id"],
            }
            attempt["check"] = copy.deepcopy(check)
            print(
                f"[GATE] {gate}: {check['status']} ({check['duration_ms']} ms)",
                flush=True,
            )
            if check["status"] != "passed":
                print(f"[LOG] {artifact_root / gate / 'output.log'}", flush=True)
        store.write(ledger)

    try:
        inputs.preflight(missing)
        if missing:
            results, context = isolated_verification.run_in_worktree(
                missing,
                prepared["snapshot"]["head"],
                gate_callback=observe,
                artifact_root=artifact_root,
            )
        else:
            results, context = (
                [{"name": "isolated-worktree", "kind": "isolation", "command": "authenticated prior isolation",
                  "status": "passed", "passed": True, "duration_ms": 0, "covers": [],
                  "details": ["all selected attempts have authenticated cleanup; no new worktree"],
                  "result": {"exit_code": 0}}],
                {
                    "mode": "git-worktree",
                    "source_commit": prepared["snapshot"]["head"],
                    "cleanup_status": "passed",
                },
            )
        run["cleanup_status"] = context["cleanup_status"]
        # Detect changes during execution before making any successful attempt reusable.
        pv.ensure_source_clean(
            [
                *prepared["documentation"]["targets"],
                "package.json",
                "package-lock.json",
                ".npmrc",
                ".github",
                ".gitattributes",
                ".gitignore",
            ]
        )
        if (
            inputs.input_snapshot(prepared["mappings"], prepared["fingerprints"])
            != prepared["snapshot"]
        ):
            raise StoreError("verification inputs changed during execution")
        results = [*reused, *results]
        if prepared.get("impact") is not None:
            context["impact"] = {"plan": "harness/verification/impact/" + prepared["task_id"] + ".json",
                                 "sha256": digest(prepared["impact"]),
                                 "selected_cases": prepared["impact"]["selected_cases"],
                                 "selected_refs": len(prepared["impact"]["test_refs"]),
                                 "excluded_cases": len(prepared["impact"]["excluded_cases"])}
        actual = [check["name"] for check in results if check.get("kind") == "product"]
        if set(actual) != set(prepared["mappings"]) and validator.passed(results):
            results.append(
                {
                    "name": "incomplete-gate-plan",
                    "status": "failed",
                    "duration_ms": 0,
                    "details": [
                        "runner stopped before completing the required gate plan"
                    ],
                }
            )
        if context["cleanup_status"] != "passed" and validator.passed(results):
            results.append(
                {
                    "name": "isolated-worktree-cleanup",
                    "status": "failed",
                    "duration_ms": 0,
                    "details": [
                        "cleanup did not pass; all current attempts are invalid"
                    ],
                }
            )
        run["state"] = (
            "passed"
            if validator.passed(results) and context["cleanup_status"] == "passed"
            else "failed"
        )
        run["checks"] = results
        context["receipt"] = {
            "run_id": run_id,
            "identity": prepared["identity"],
            "plan": plan,
        }
        store.write(ledger)
        return results, context
    except BaseException as error:
        run["failure"] = {
            "kind": "port-conflict"
            if "port-conflict" in str(error)
            else "interrupted"
            if isinstance(error, KeyboardInterrupt)
            else "precondition",
            "summary": str(error)[:300],
        }
        run["state"] = "interrupted" if isinstance(error, (KeyboardInterrupt, SystemExit)) else "failed"
        run["cleanup_status"] = "unknown"
        store.write(ledger)
        raise


def attest(task_id: str, path: Path, prepared: dict[str, Any]) -> None:
    store = RunStore(task_id)
    ledger = store.read()
    payload = json.loads(path.read_bytes())
    if (
        payload["status"] != "passed"
        or not ledger["runs"]
        or ledger["runs"][-1]["state"] != "passed"
    ):
        return
    ledger["aggregate"] = {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "identity": prepared["identity"],
        "cases": prepared["cases"],
        "run_id": ledger["runs"][-1]["id"],
    }
    store.write(ledger)
    _PROCESS_RECEIPTS[task_id] = ledger["aggregate"]["sha256"]
    if prepared.get('impact') is not None:
        _PROCESS_PREPARED[task_id] = copy.deepcopy(prepared)


def prepared_in_process(prepared):
    """Reuse immutable runner resolution, while rechecking every mutable input.

    The runner already checked source cleanliness and input identity after test
    execution. At close, the same HEAD plus clean tracked source/plan/contract
    paths pins that resolution; toolchain/dependency/environment inputs are still
    freshly checked. This is not a persistent cache or a user-supplied receipt.
    """
    from .impact import activate
    with activate(prepared['impact']):
        if pv.head_commit() != prepared['snapshot']['head']:
            raise StoreError('authenticated inputs are stale: HEAD changed before close')
        pv.ensure_source_clean([
            *prepared['documentation']['targets'], 'package.json', 'package-lock.json',
            '.npmrc', '.github', '.gitattributes', '.gitignore',
        ])
        if inputs.input_snapshot(prepared['mappings'], prepared['fingerprints']) != prepared['snapshot']:
            raise StoreError('authenticated inputs are stale: runtime inputs changed before close')
    return prepared


def authenticate(task_id: str, path: Path) -> dict[str, Any]:
    store = RunStore(task_id)
    ledger = store.read()
    aggregate = ledger.get("aggregate")
    if not aggregate or not ledger["runs"] or ledger["runs"][-1]["state"] != "passed":
        raise StoreError("no complete authenticated aggregate; run verify before close")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != aggregate["sha256"]:
        raise StoreError("evidence bytes do not match the authenticated runner receipt")
    if _PROCESS_RECEIPTS.get(task_id) == aggregate['sha256'] and task_id in _PROCESS_PREPARED:
        prepared = prepared_in_process(_PROCESS_PREPARED[task_id])
    else:
        prepared = prepare(task_id, collect=False, cases=aggregate["cases"])
    if prepared["snapshot"].get("persistent_close") is False and _PROCESS_RECEIPTS.get(task_id) != aggregate["sha256"]:
        raise StoreError("selected dependency closure is not registered for persistent close; use verify --close")
    if prepared["identity"] != aggregate["identity"]:
        raise StoreError(
            "authenticated inputs are stale: HEAD, plan, toolchain, dependencies or environment changed"
        )
    latest = latest_attempts(ledger, prepared["identity"])
    if any(not latest.get(gate, {}).get("reusable") for gate in prepared["mappings"]):
        raise StoreError(
            "latest gate attempt is failed, missing, interrupted or not cleaned"
        )
    return prepared


def authenticated_digest(task_id: str) -> str:
    aggregate = RunStore(task_id).read().get("aggregate")
    if not aggregate:
        raise StoreError("no authenticated aggregate remains for close")
    return str(aggregate["sha256"])
