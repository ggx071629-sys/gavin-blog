from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path

from . import (
    assurance,
    change_enforcement,
    close_transaction,
    events,
    indexer,
    isolated_verification,
    lifecycle,
    product_verification,
    qualification,
    qualification_runner,
    run_store,
    summarizer,
    task_reporting,
    telemetry,
    validator,
    verification_resume,
)


def _configure_console_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(errors="backslashreplace")


def _print_results(results: list[dict[str, object]]) -> None:
    if validator.passed(results):
        duration = round(sum(float(r.get("duration_ms", 0)) for r in results), 1)
        print(f"[PASSED] {len(results)} checks ({duration} ms)")
        return
    for result in results:
        details = result.get("details") or []
        print(f"[{result['status'].upper()}] {result['name']}")
        for detail in details:
            print(f"  - {detail}")


def command_index(_: argparse.Namespace) -> int:
    written = indexer.write_indexes()
    if written:
        for path in written:
            print(f"generated {path}")
    else:
        print("indexes are current")
    return 0


def _execute_verification(
    task_id: str | None,
    *,
    observe_telemetry: bool = True,
    fresh: bool = False,
) -> tuple[list[dict[str, object]], Path | None]:
    checks_started = time.perf_counter()
    results = validator.run_checks()
    if task_id:
        for result in results:
            result["provenance"] = {"scope": "workspace"}
    checks_ms = round((time.perf_counter() - checks_started) * 1000, 3)
    criteria: list[str] = []
    mappings: dict[str, list[str]] = {}
    profile = ""
    fingerprints: dict[str, str] = {}
    documentation: dict[str, object] = {}
    execution: dict[str, object] = {}
    verification_cases: dict[str, object] = {}
    prepared = None
    if task_id:
        if lifecycle.task_status(task_id) == "frozen":
            results.append(
                {
                    "name": "task-lifecycle",
                    "kind": "product",
                    "command": "",
                    "passed": False,
                    "status": "failed",
                    "duration_ms": 0,
                    "covers": [],
                    "details": [
                        f"{task_id} is frozen; resume it before task verification"
                    ],
                }
            )
        else:
            try:
                if not validator.passed(results):
                    raise product_verification.ProductVerificationError("global preflight failed; product gates were not started")
                plan_started = time.perf_counter()
                prepared = verification_resume.prepare(task_id)
                plan_ms = round((time.perf_counter() - plan_started) * 1000, 3)
                criteria, mappings = prepared["criteria"], prepared["mappings"]
                profile, documentation = prepared["profile"], prepared["documentation"]
                fingerprints, verification_cases = prepared["fingerprints"], prepared["cases"]
                execution_started = time.perf_counter()
                gate_results, execution = verification_resume.execute(prepared, fresh=fresh)
                execution["phase_durations_ms"] = {"preflight_checks": checks_ms, "plan_inputs": plan_ms,
                    "execute_cleanup_and_input_recheck": round((time.perf_counter() - execution_started) * 1000, 3)}
                print(f"[PHASES] {json.dumps(execution['phase_durations_ms'])}")
                results.extend(gate_results)
            except (OSError, RuntimeError, ValueError) as error:
                results.append(
                    {
                        "name": "task-verification-precondition",
                        "kind": "product",
                        "command": "",
                        "passed": False,
                        "status": "failed",
                        "duration_ms": 0,
                        "covers": [],
                        "details": [str(error)],
                    }
                )
    _print_results(results)
    evidence: Path | None = None
    if task_id:
        evidence = validator.write_task_evidence(
            task_id,
            f"python -m tools.harness verify {task_id}" + (" --fresh" if fresh else ""),
            criteria,
            mappings,
            profile,
            fingerprints,
            documentation,
            execution,
            results,
            verification_cases,
            **({"prepared": prepared} if prepared is not None else {}),
        )
        if prepared is not None and validator.passed(results):
            verification_resume.attest(task_id, evidence, prepared)
        print(f"evidence {evidence}")
        if (
            observe_telemetry
            and evidence.resolve() == validator.evidence_path(task_id).resolve()
        ):
            telemetry_error = telemetry.observe_task_verification_safely(
                task_id,
                profile,
                execution,
                results,
                product_verification.head_commit(),
            )
            if telemetry_error:
                print(
                    f"warning: telemetry observation failed: {telemetry_error}",
                    file=sys.stderr,
                )
        if lifecycle.task_status(task_id) == "frozen":
            print("task state frozen")
        else:
            state = "verified" if prepared is not None and validator.passed(results) else "active"
            print(f"task state {state}")
        if not validator.passed(results):
            hint = _repeated_failure_hint(task_id)
            if hint:
                print(hint, file=sys.stderr)
    return results, evidence


def command_verify(args: argparse.Namespace) -> int:
    if args.task_id:
        summarizer.validate_task_id(args.task_id)
    try:
        if not args.task_id:
            results, _ = _execute_verification(None)
        else:
            with run_store.repository_lock():
                close_transaction.recover()
                store = run_store.RunStore(args.task_id)
                ledger = store.recover(fresh=bool(getattr(args, "fresh", False)))
                ledger["aggregate"] = None
                store.write(ledger)
                results, _ = _execute_verification(args.task_id, fresh=bool(getattr(args, "fresh", False)))
                if validator.passed(results) and getattr(args, "close", False):
                    return _close_tasks_locked([args.task_id])
        return 0 if validator.passed(results) else 1
    except (OSError, RuntimeError, ValueError) as error:
        print(f"verify stopped: {error}", file=sys.stderr)
        return 1


def command_plan(args: argparse.Namespace) -> int:
    try:
        plan = verification_resume.preview(args.task_id, fresh=args.fresh)
        if args.json:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
        else:
            if plan.get("impact"):
                scope = plan["impact"]
                print(f"[SCOPE] {len(scope['selected_cases'])} cases, {len(scope['test_refs'])} exact refs, {len(scope['excluded_cases'])} excluded cases")
                print(f"[PREPARE] {', '.join(p['id'] for p in plan.get('prerequisites', [])) or 'none'}")
                print(f"[BATCHES] {len(plan.get('batches', []))} conservative batches; identities resolved at execution")
            verification_resume.print_plan(plan["gates"])
            if plan["blocker"]:
                print(f"blocked: {plan['blocker']}")
            print(f"next: {plan['next']}")
        return 1 if plan["blocker"] else 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"plan blocked: {error}", file=sys.stderr)
        return 1


def _repeated_failure_hint(task_id: str) -> str:
    try:
        run_ids = telemetry.failed_verification_run_ids(task_id)
    except (OSError, ValueError):
        return ""
    if len(run_ids) < 2:
        return ""
    return (
        "repeated failure: python -m tools.harness emit-event "
        f"verification.repeated_failure {task_id} "
        f"--run-id {run_ids[-2]} --run-id {run_ids[-1]} --reason \"...\""
    )


def command_spec_lint(args: argparse.Namespace) -> int:
    if args.task_id:
        summarizer.validate_task_id(args.task_id)
        task_ids = [args.task_id]
    else:
        task_ids = [
            path.stem
            for path in summarizer.active_specs()
            if lifecycle.task_status(path.stem) != "frozen"
        ]
    if not task_ids:
        print("no active specs to lint")
        return 0
    failed = False
    for task_id in task_ids:
        try:
            product_verification.lint_task_contract(task_id)
        except (OSError, RuntimeError, ValueError) as error:
            failed = True
            print(f"[FAILED] spec-lint {task_id}")
            print(f"  - {error}")
            continue
        print(f"[PASSED] spec-lint {task_id}")
    return 1 if failed else 0


def _evidence_sha256(task_id: str) -> str:
    return hashlib.sha256(validator.evidence_path(task_id).read_bytes()).hexdigest()


def _preflight_close(task_ids: list[str]) -> bool:
    valid = True
    for task_id in task_ids:
        try:
            prepared = verification_resume.authenticate(task_id, validator.evidence_path(task_id))
            evidence_errors = product_verification.validate_evidence(task_id, validator.evidence_path(task_id), prepared=prepared)
        except (OSError, RuntimeError, ValueError) as error:
            evidence_errors = [str(error)]
        if evidence_errors:
            valid = False
            print(f"close aborted: {task_id} evidence is not valid; run verify", file=sys.stderr)
            for error in evidence_errors:
                print(f"  - {error}", file=sys.stderr)
    return valid


def _close_preflight(
    task_ids: list[str],
) -> list[tuple[str, Path, str, Path, str]] | None:
    if not _preflight_close(task_ids):
        return None
    snapshots: list[tuple[str, Path, str, Path, str]] = []
    try:
        for task_id in task_ids:
            source = summarizer.active_spec(task_id)
            archive = summarizer.archive_spec(task_id)
            event_path = events.event_path("spec.completed", task_id)
            if archive.exists():
                raise FileExistsError(f"archive already exists: {archive}")
            if event_path.exists():
                raise FileExistsError(f"event already exists: {event_path}")
            evidence_sha256 = verification_resume.authenticated_digest(task_id)
            if _evidence_sha256(task_id) != evidence_sha256:
                raise RuntimeError(f"task evidence changed after authentication: {task_id}")
            snapshots.append(
                (
                    task_id,
                    archive,
                    source.read_text(encoding="utf-8"),
                    event_path,
                    evidence_sha256,
                )
            )
    except (OSError, ValueError) as error:
        print(f"close aborted: {error}", file=sys.stderr)
        return None
    before = validator.run_close_checks()
    _print_results(before)
    if not validator.passed(before):
        print("close aborted: pre-close verification failed", file=sys.stderr)
        return None
    return snapshots


def _close_tasks_locked(task_ids: list[str]) -> int:
    source_head = product_verification.head_commit()
    snapshots = _close_preflight(task_ids)
    if snapshots is None:
        return 1

    from . import impact
    guarded = any(impact.plan_path(task).is_file() for task in task_ids)
    allowed_close_paths = set()
    guard_plans = [impact.build_plan(task) for task in task_ids] if guarded else []
    if guarded:
        project = product_verification.project_root()
        allowed_close_paths.update(path.relative_to(project).as_posix() for path in indexer.expected_indexes())
        for task in task_ids:
            allowed_close_paths.add(summarizer.active_spec(task).relative_to(project).as_posix())

    close_transaction.begin(snapshots, source_head)
    attempted: list[tuple[str, Path, str, Path, str]] = []
    try:
        for task_id, expected_archive, source_text, expected_event, evidence_sha256 in snapshots:
            attempted.append(
                (task_id, expected_archive, source_text, expected_event, evidence_sha256)
            )
            if product_verification.head_commit() != source_head:
                raise RuntimeError("HEAD changed during close")
            if summarizer.active_spec(task_id).read_text(encoding="utf-8") != source_text:
                raise RuntimeError("active spec changed during close")
            if _evidence_sha256(task_id) != evidence_sha256:
                raise RuntimeError(f"task evidence changed during close: {task_id}")
            archive, source_text = summarizer.close_spec(
                task_id,
                evidence_sha256=evidence_sha256,
            )
            event_path, proposal_path = events.emit_event(
                "spec.completed",
                task_id,
                "The active spec passed verification and was deterministically compressed.",
                "lifecycle",
                create_proposal=False,
                evidence_sha256=evidence_sha256,
            )
            if proposal_path is not None:
                raise RuntimeError("spec.completed must not create a proposal")
            if archive != expected_archive or event_path != expected_event:
                raise RuntimeError("close artifacts did not match preflight targets")
        indexer.write_indexes()
        after = validator.run_close_checks()
        if not validator.passed(after):
            raise RuntimeError("post-close verification failed")
        _print_results(after)
        if product_verification.head_commit() != source_head:
            raise RuntimeError("HEAD changed during close")
        for task_id, _, _, _, expected_digest in snapshots:
            if _evidence_sha256(task_id) != expected_digest:
                raise RuntimeError(f"task evidence changed during close: {task_id}")
        if guarded:
            drift = []
            for guard_plan in guard_plans:
                with impact.activate(guard_plan):
                    drift.extend(row for row in product_verification.source_changes()
                                 if row[3:].strip('"').replace("\\", "/") not in allowed_close_paths)
            if drift:
                raise RuntimeError("source or impact plan changed during close: " + drift[0][3:])
        close_transaction.finish()
        for task_id, archive, _, event_path, _ in snapshots:
            print(f"archive {archive}")
            print(f"evidence {validator.evidence_path(task_id)}")
            print(f"event {event_path}")
        return 0
    except BaseException as error:
        rollback_errors: list[str] = []
        for task_id, archive, source_text, event_path, _ in reversed(attempted):
            try:
                summarizer.restore_spec(task_id, source_text, archive)
            except OSError as rollback_error:
                rollback_errors.append(f"restore {task_id}: {rollback_error}")
            try:
                event_path.unlink(missing_ok=True)
            except OSError as rollback_error:
                rollback_errors.append(f"remove {event_path}: {rollback_error}")
        try:
            indexer.write_indexes()
        except (OSError, ValueError) as rollback_error:
            rollback_errors.append(f"restore indexes: {rollback_error}")
        if not rollback_errors:
            close_transaction.finish()
        print(f"close aborted and rolled back: {error}", file=sys.stderr)
        for rollback_error in rollback_errors:
            print(f"  - rollback incomplete: {rollback_error}", file=sys.stderr)
        return 1


def _close_tasks(task_ids: list[str]) -> int:
    try:
        with run_store.repository_lock():
            close_transaction.recover()
            return _close_tasks_locked(task_ids)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"close aborted: {error}", file=sys.stderr)
        return 1


def command_close(args: argparse.Namespace) -> int:
    summarizer.validate_task_id(args.task_id)
    if lifecycle.task_status(args.task_id) == "frozen":
        print(
            f"close aborted: {args.task_id} is frozen; resume it before closing",
            file=sys.stderr,
        )
        return 1
    return _close_tasks([args.task_id])


def command_close_all(args: argparse.Namespace) -> int:
    active: list[str] = []
    frozen: list[str] = []
    for path in summarizer.active_specs():
        task_id = path.stem
        summarizer.validate_task_id(task_id)
        if lifecycle.task_status(task_id) == "frozen":
            frozen.append(task_id)
        else:
            active.append(task_id)
    for task_id in frozen:
        print(f"[SKIPPED] {task_id} is frozen")
    if not active:
        print("no active specs to close")
        return 0
    print(f"preflight {len(active)} active spec(s)")
    if bool(getattr(args, "dry_run", False)):
        snapshots = _close_preflight(active)
        if snapshots is None:
            return 1
        print(f"dry-run ready: {len(snapshots)} active spec(s) can close atomically")
        return 0
    return _close_tasks(active)


def command_status(args: argparse.Namespace) -> int:
    records = (
        [task_reporting.task_record(args.task_id)]
        if args.task_id
        else task_reporting.current_task_records()
    )
    if args.json:
        print(json.dumps({"schema_version": 1, "tasks": records}, ensure_ascii=False))
    else:
        for record in records:
            profile = record["verification_profile"] or "—"
            print(
                f"[{str(record['state']).upper()}] {record['task_id']} "
                f"profile={profile} evidence={record['evidence']}"
            )
            if record.get("plan"):
                verification_resume.print_plan(record["plan"]["gates"])
                print(f"next: {record['plan']['next']}")
            blockers = record.get("blockers") or []
            if blockers:
                print(f"  - {blockers[0]}")
    return 1 if any(record["state"] == "missing" for record in records) else 0


def command_change_check(args: argparse.Namespace) -> int:
    try:
        result = change_enforcement.inspect_change(args.base, args.head)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"[FAILED] change-coverage\n  - {error}", file=sys.stderr)
        return 1
    status = "PASSED" if result["passed"] else "FAILED"
    print(f"[{status}] change-coverage")
    print(f"  - base {result['base']}")
    print(f"  - head {result['head']}")
    print(f"  - {len(result['risk_paths'])} risk path(s)")
    for detail in result["details"]:
        print(f"  - {detail}")
    return 0 if result["passed"] else 1


def command_telemetry_summary(args: argparse.Namespace) -> int:
    try:
        events, source_files = telemetry.load_events()
        summary = telemetry.summarize(events, source_files)
    except (OSError, ValueError) as error:
        print(f"telemetry summary failed: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        print(
            f"telemetry events={summary['events']} files={summary['source_files']} "
            f"passed={summary['status']['passed']} failed={summary['status']['failed']}"
        )
        duration = summary["duration_ms"]
        print(
            f"duration count={duration['count']} p50={duration['p50']} "
            f"p95={duration['p95']} max={duration['max']}"
        )
    return 0


def command_telemetry_health(args: argparse.Namespace) -> int:
    try:
        events, source_files = telemetry.load_events()
        assessment = telemetry.assess_health(events, source_files)
    except (OSError, ValueError) as error:
        print(f"telemetry health failed: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(assessment, ensure_ascii=False, sort_keys=True))
    else:
        counts = assessment["series_status"]
        print(
            f"telemetry health={assessment['status']} "
            f"events={assessment['events']} evaluated={assessment['evaluated_events']}"
        )
        print(
            f"series stable={counts['stable']} signal={counts['signal']} "
            f"insufficient={counts['insufficient-data']}"
        )
        for key, item in assessment["series"].items():
            print(
                f"  - {key}: {item['status']} "
                f"samples={item['status_samples']} signals={len(item['signals'])}"
            )
    return 0


def command_evidence_inventory(args: argparse.Namespace) -> int:
    result = assurance.inventory()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(
            f"evidence tasks={result['tasks']} auxiliary={result['auxiliary_files']}"
        )
        for level in assurance.LEVELS:
            print(f"  - {level}: {result['assurance'][level]}")
    return 0


def command_emit_event(args: argparse.Namespace) -> int:
    run_ids = list(getattr(args, "run_id", []) or [])
    evidence_runs: list[dict[str, object]] = []
    if args.event_type == "verification.repeated_failure":
        evidence_runs = telemetry.failure_run_references(args.task_id, run_ids)
    elif run_ids:
        raise ValueError(
            "--run-id is only valid for verification.repeated_failure"
        )
    event_path, proposal_path = events.emit_event(
        args.event_type,
        args.task_id,
        args.reason,
        args.source,
        evidence_runs=evidence_runs,
    )
    indexer.write_indexes()
    print(f"event {event_path}")
    if proposal_path is not None:
        print(f"proposal {proposal_path}")
    return 0


def _command_transition(
    args: argparse.Namespace,
    transition: Callable[[str, str], Path],
    action: str,
) -> int:
    summarizer.validate_task_id(args.task_id)
    path = summarizer.active_spec(args.task_id)
    original = path.read_bytes() if path.is_file() else None
    try:
        transition(args.task_id, args.reason)
        errors = lifecycle.validate_active_spec(path)
        if errors:
            raise lifecycle.LifecycleError(errors[0])
        indexer.write_indexes()
        print(f"{action} {path}")
        return 0
    except Exception as error:
        if original is not None:
            path.write_bytes(original)
        indexer.write_indexes()
        print(f"{action} aborted and rolled back: {error}", file=sys.stderr)
        return 1


def command_freeze(args: argparse.Namespace) -> int:
    return _command_transition(args, lifecycle.freeze_spec, "frozen")


def command_resume(args: argparse.Namespace) -> int:
    return _command_transition(args, lifecycle.resume_spec, "resumed")


def command_qualification_sign(args: argparse.Namespace) -> int:
    try:
        qualification.sign_manifest_file(args.input, args.private_key, args.output)
    except (OSError, ValueError) as error:
        print(f"qualification signing failed: {error}", file=sys.stderr)
        return 1
    print(f"signed qualification manifest {args.output}")
    return 0


def command_qualification_verify(args: argparse.Namespace) -> int:
    summarizer.validate_task_id(args.task_id)
    errors, binding = qualification.validate_task_qualification(
        args.task_id,
        active=not args.historical,
    )
    if errors:
        print(f"[FAILED] qualification {args.task_id}")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"[PASSED] qualification {args.task_id}")
    print(json.dumps(binding, ensure_ascii=False, sort_keys=True))
    return 0


def command_qualification_run_init(args: argparse.Namespace) -> int:
    summarizer.validate_task_id(args.task_id)
    try:
        path = qualification_runner.initialize_run(
            task_id=args.task_id,
            artifact_path=args.artifact,
            workspace=args.workspace,
        )
    except (OSError, ValueError) as error:
        print(f"qualification run initialization failed: {error}", file=sys.stderr)
        return 1
    print(f"qualification run {path}")
    print("provider calls 0; deployment mutations 0; public switches unchanged")
    return 0


def command_qualification_run_record(args: argparse.Namespace) -> int:
    try:
        path = qualification_runner.record_case(
            workspace=args.workspace,
            observation_path=args.observation,
        )
    except (OSError, ValueError) as error:
        print(f"qualification case recording failed: {error}", file=sys.stderr)
        return 1
    print(f"qualification case {path}")
    return 0


def command_qualification_run_assemble(args: argparse.Namespace) -> int:
    try:
        path = qualification_runner.assemble_manifest(
            workspace=args.workspace,
            summary_path=args.summary,
            output_path=args.output,
        )
    except (OSError, ValueError) as error:
        print(f"qualification manifest assembly failed: {error}", file=sys.stderr)
        return 1
    print(f"unsigned qualification manifest {path}")
    print("review and sign separately; no public switch was enabled")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Gavin project harness")
    commands = root.add_subparsers(dest="command", required=True)

    index = commands.add_parser("index", help="regenerate metadata indexes")
    index.set_defaults(func=command_index)

    verify = commands.add_parser("verify", help="run all deterministic checks")
    verify.add_argument("task_id", nargs="?")
    verify.add_argument("--fresh", action="store_true", help="execute all task gates without reuse")
    verify.add_argument("--close", action="store_true", help="consume this run and close in the same process")
    verify.set_defaults(func=command_verify)

    plan = commands.add_parser("plan", help="explain gate execution/reuse without product tests")
    plan.add_argument("task_id")
    plan.add_argument("--fresh", action="store_true")
    plan.add_argument("--json", action="store_true")
    plan.set_defaults(func=command_plan)

    from .diagnostics import command as command_diagnose
    diagnose = commands.add_parser("diagnose", help="run a fixed-HEAD exact subset without certification")
    diagnose.add_argument("task_id")
    selection = diagnose.add_mutually_exclusive_group(required=True)
    selection.add_argument("--case")
    selection.add_argument("--failed", action="store_true")
    diagnose.set_defaults(func=command_diagnose)

    spec_lint = commands.add_parser(
        "spec-lint",
        help="check the active spec verification contract without product gates",
    )
    spec_lint.add_argument("task_id", nargs="?")
    spec_lint.set_defaults(func=command_spec_lint)

    qualification_sign = commands.add_parser(
        "qualification-sign",
        help="sign a canonical target qualification manifest with an approved private key",
    )
    qualification_sign.add_argument("--input", type=Path, required=True)
    qualification_sign.add_argument("--private-key", type=Path, required=True)
    qualification_sign.add_argument("--output", type=Path, required=True)
    qualification_sign.set_defaults(func=command_qualification_sign)

    qualification_verify = commands.add_parser(
        "qualification-verify",
        help="verify the configured signed target qualification manifest",
    )
    qualification_verify.add_argument("task_id")
    qualification_verify.add_argument("--historical", action="store_true")
    qualification_verify.set_defaults(func=command_qualification_verify)

    qualification_init = commands.add_parser(
        "qualification-run-init",
        help="initialize a zero-call evidence run on the approved real target",
    )
    qualification_init.add_argument("task_id")
    qualification_init.add_argument("--artifact", type=Path, required=True)
    qualification_init.add_argument("--workspace", type=Path, required=True)
    qualification_init.set_defaults(func=command_qualification_run_init)

    qualification_record = commands.add_parser(
        "qualification-run-record",
        help="record one reviewed case and its off-host artifact hashes",
    )
    qualification_record.add_argument("--workspace", type=Path, required=True)
    qualification_record.add_argument("--observation", type=Path, required=True)
    qualification_record.set_defaults(func=command_qualification_run_record)

    qualification_assemble = commands.add_parser(
        "qualification-run-assemble",
        help="assemble a complete unsigned compact target manifest",
    )
    qualification_assemble.add_argument("--workspace", type=Path, required=True)
    qualification_assemble.add_argument("--summary", type=Path, required=True)
    qualification_assemble.add_argument("--output", type=Path, required=True)
    qualification_assemble.set_defaults(func=command_qualification_run_assemble)

    close = commands.add_parser("close", help="authenticate existing evidence and atomically compress an active spec")
    close.add_argument("task_id")
    close.set_defaults(func=command_close)

    close_all = commands.add_parser(
        "close-all",
        help="preflight and atomically close all non-frozen active specs",
    )
    close_all.add_argument(
        "--dry-run",
        action="store_true",
        help="run the complete close preflight without writing files",
    )
    close_all.set_defaults(func=command_close_all)

    status = commands.add_parser("status", help="report derived task lifecycle state")
    status.add_argument("task_id", nargs="?")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=command_status)

    change_check = commands.add_parser(
        "change-check",
        help="require current task evidence for configured risk changes",
    )
    change_check.add_argument("--base", required=True)
    change_check.add_argument("--head", default="HEAD")
    change_check.set_defaults(func=command_change_check)

    telemetry_summary = commands.add_parser(
        "telemetry-summary",
        help="validate and deterministically summarize local telemetry",
    )
    telemetry_summary.add_argument("--json", action="store_true")
    telemetry_summary.set_defaults(func=command_telemetry_summary)

    telemetry_health = commands.add_parser(
        "telemetry-health",
        help="assess local telemetry without changing gates or evolution state",
    )
    telemetry_health.add_argument("--json", action="store_true")
    telemetry_health.set_defaults(func=command_telemetry_health)

    evidence_inventory = commands.add_parser(
        "evidence-inventory",
        help="classify historical evidence assurance without re-verifying it",
    )
    evidence_inventory.add_argument("--json", action="store_true")
    evidence_inventory.set_defaults(func=command_evidence_inventory)

    freeze = commands.add_parser("freeze", help="freeze an active spec")
    freeze.add_argument("task_id")
    freeze.add_argument("--reason", required=True)
    freeze.set_defaults(func=command_freeze)

    resume = commands.add_parser("resume", help="resume a frozen spec")
    resume.add_argument("task_id")
    resume.add_argument("--reason", required=True)
    resume.set_defaults(func=command_resume)

    emit = commands.add_parser("emit-event", help="emit an explicit evolution event")
    emit.add_argument("event_type")
    emit.add_argument("task_id")
    emit.add_argument("--reason", required=True)
    emit.add_argument("--source", choices=["manual", "lifecycle"], default="manual")
    emit.add_argument("--run-id", action="append", default=[])
    emit.set_defaults(func=command_emit_event)
    return root


def main() -> int:
    _configure_console_streams()
    args = parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
