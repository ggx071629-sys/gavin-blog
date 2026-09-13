"""Fixed-HEAD, non-certifying diagnostics. Never write the formal ledger/evidence."""

from __future__ import annotations

import json
import secrets

from . import impact, isolated_verification, verification_inputs, verification_resume
from .config import project_root
from .module_verification import case_index, load_module_contract
from .run_store import RunStore, StoreError, repository_lock


def match_current(selected, current):
    if not selected:
        raise StoreError("diagnostic gap: no recoverable failed consumers")
    result = []
    for ref in selected:
        matches = [
            r
            for r in current
            if all(r.get(k) == ref.get(k) for k in ("kind", "gate", "path", "name"))
            and all(
                k not in r or r[k] == ref.get(k)
                for k in ("config", "project", "title_path")
            )
        ]
        if len(matches) != 1:
            raise StoreError(
                "diagnostic gap: removed or ambiguous reference " + str(ref.get("path"))
            )
        if matches[0] not in result:
            result.append(matches[0])
    return result


def select(plan, *, case=None, ledger=None):
    if case:
        if case not in plan["selected_cases"]:
            raise StoreError("diagnostic case is outside the complete current plan")
        refs = case_index(load_module_contract(project_root()))[case]["test_refs"]
        return match_current(
            [r for r in refs if r["kind"] != "harness-check"], plan["test_refs"]
        )
    runs = (ledger or {}).get("runs", [])
    if not runs or runs[-1]["state"] not in {"failed", "interrupted"}:
        raise StoreError("diagnostic gap: the latest formal run has no failure")
    run = runs[-1]
    selected = []
    for attempt in run["attempts"]:
        for stage in attempt.get("check", {}).get("result", {}).get("stages", []):
            if (
                stage.get("source") == "selected-runner"
                and stage.get("version") == 3
                and stage.get("status") == "failed"
            ):
                selected.extend(stage["consumers"])
    # A snapshot failure affects the complete plan before any consumers start.
    if any(
        c.get("result", {}).get("failure", {}).get("kind") == "snapshot-input"
        for c in run.get("checks", [])
    ):
        selected = run.get("selected_refs", [])
    return match_current(selected, plan["test_refs"])


def command(args):
    try:
        with repository_lock():
            prepared = verification_resume.prepare(args.task_id)
            plan = prepared.get("impact")
            if plan is None or plan.get("release"):
                raise StoreError("diagnosis requires a focused exact impact plan")
            refs = select(
                plan,
                case=args.case,
                ledger=RunStore(args.task_id).read() if args.failed else None,
            )
            mappings = {
                g: c
                for g, c in prepared["mappings"].items()
                if g in {r["gate"] for r in refs}
            }
            store = RunStore(args.task_id)
            store.root = store.root / "diagnostics"
            store.path = store.root / f"{args.task_id}.json"
            ledger = store.read()
            run_id = secrets.token_hex(16)
            from .run_artifacts import prune

            prune()
            artifacts = store.root / "artifacts" / run_id
            run = {
                "id": run_id,
                "state": "running",
                "attempts": [],
                "selected_refs": refs,
                "mode": "diagnostic",
                "certifying": False,
                "source_commit": prepared["snapshot"]["head"],
            }
            ledger["runs"].append(run)
            store.write(ledger)
            try:
                with impact.activate(plan):
                    verification_inputs.preflight(mappings, selected_refs=refs)
                    checks, context = isolated_verification.run_in_worktree(
                        mappings,
                        prepared["snapshot"]["head"],
                        artifact_root=artifacts,
                        diagnostic_refs=refs,
                    )
                    verification_resume.prepared_in_process(prepared)
                run.update(
                    checks=checks,
                    execution=context,
                    state="passed"
                    if all(c["status"] == "passed" for c in checks)
                    else "failed",
                )
            except BaseException as error:
                run.update(state="failed", failure=str(error)[:300])
                raise
            finally:
                ledger["aggregate"] = None
                store.write(ledger)
            print(
                json.dumps(
                    {
                        "mode": "diagnostic",
                        "certifying": False,
                        "status": run["state"],
                        "selected_refs": len(refs),
                        "artifacts": str(artifacts),
                    },
                    ensure_ascii=True,
                )
            )
            return 0 if run["state"] == "passed" else 1
    except (OSError, RuntimeError, ValueError) as error:
        print(f"diagnose stopped: {error}")
        return 1
