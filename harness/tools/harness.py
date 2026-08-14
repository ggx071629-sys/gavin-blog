from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from . import (
    assurance,
    change_enforcement,
    events,
    indexer,
    isolated_verification,
    lifecycle,
    product_verification,
    summarizer,
    task_reporting,
    telemetry,
    validator,
)


def _configure_console_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(errors="backslashreplace")


def _print_results(results: list[dict[str, object]]) -> None:
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


def command_verify(args: argparse.Namespace) -> int:
    if args.task_id:
        summarizer.validate_task_id(args.task_id)
    results = validator.run_checks()
    criteria: list[str] = []
    mappings: dict[str, list[str]] = {}
    profile = ""
    fingerprints: dict[str, str] = {}
    documentation: dict[str, object] = {}
    execution: dict[str, object] = {}
    if args.task_id:
        if lifecycle.task_status(args.task_id) == "frozen":
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
                        f"{args.task_id} is frozen; resume it before task verification"
                    ],
                }
            )
        else:
            try:
                summarizer.ensure_spec_in_git_history(summarizer.active_spec(args.task_id))
                criteria, mappings = product_verification.verification_contract(args.task_id)
                profile = product_verification.verification_profile(args.task_id)
                product_verification.validate_configured_gates(
                    mappings,
                    profile,
                    args.task_id,
                )
                documentation = product_verification.documentation_report(args.task_id)
                fingerprints = product_verification.evidence_fingerprints(
                    args.task_id,
                    criteria,
                    mappings,
                    profile,
                    documentation,
                )
                source_commit = product_verification.head_commit()
                if source_commit is None:
                    raise product_verification.ProductVerificationError(
                        "current Git HEAD is unavailable"
                    )
                gate_results, execution = isolated_verification.run_in_worktree(
                    mappings,
                    source_commit,
                )
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
    if args.task_id:
        evidence = validator.write_task_evidence(
            args.task_id,
            f"python -m tools.harness verify {args.task_id}",
            criteria,
            mappings,
            profile,
            fingerprints,
            documentation,
            execution,
            results,
        )
        print(f"evidence {evidence}")
        if evidence.resolve() == validator.evidence_path(args.task_id).resolve():
            telemetry_error = telemetry.observe_task_verification_safely(
                args.task_id,
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
        if lifecycle.task_status(args.task_id) == "frozen":
            print("task state frozen")
        else:
            state = product_verification.derived_task_state(args.task_id, evidence)
            print(f"task state {state}")
    return 0 if validator.passed(results) else 1


def _preflight_close(task_ids: list[str]) -> bool:
    valid = True
    for task_id in task_ids:
        evidence_errors = product_verification.validate_evidence(
            task_id,
            validator.evidence_path(task_id),
        )
        if evidence_errors:
            valid = False
            print(f"close aborted: {task_id} evidence is not valid", file=sys.stderr)
            for error in evidence_errors:
                print(f"  - {error}", file=sys.stderr)
    return valid


def _close_preflight(task_ids: list[str]) -> list[tuple[str, Path, str, Path]] | None:
    if not _preflight_close(task_ids):
        return None
    snapshots: list[tuple[str, Path, str, Path]] = []
    try:
        for task_id in task_ids:
            source = summarizer.active_spec(task_id)
            archive = summarizer.archive_spec(task_id)
            event_path = events.event_path("spec.completed", task_id)
            if archive.exists():
                raise FileExistsError(f"archive already exists: {archive}")
            if event_path.exists():
                raise FileExistsError(f"event already exists: {event_path}")
            snapshots.append(
                (task_id, archive, source.read_text(encoding="utf-8"), event_path)
            )
    except (OSError, ValueError) as error:
        print(f"close aborted: {error}", file=sys.stderr)
        return None
    before = validator.run_checks()
    _print_results(before)
    if not validator.passed(before):
        print("close aborted: pre-close verification failed", file=sys.stderr)
        return None
    return snapshots


def _close_tasks(task_ids: list[str]) -> int:
    snapshots = _close_preflight(task_ids)
    if snapshots is None:
        return 1

    attempted: list[tuple[str, Path, str, Path]] = []
    try:
        for task_id, expected_archive, source_text, expected_event in snapshots:
            attempted.append((task_id, expected_archive, source_text, expected_event))
            archive, source_text = summarizer.close_spec(task_id)
            event_path, proposal_path = events.emit_event(
                "spec.completed",
                task_id,
                "The active spec passed verification and was deterministically compressed.",
                "lifecycle",
                create_proposal=False,
            )
            if proposal_path is not None:
                raise RuntimeError("spec.completed must not create a proposal")
            if archive != expected_archive or event_path != expected_event:
                raise RuntimeError("close artifacts did not match preflight targets")
        indexer.write_indexes()
        after = validator.run_checks()
        if not validator.passed(after):
            raise RuntimeError("post-close verification failed")
        _print_results(after)
        for task_id, archive, _, event_path in snapshots:
            print(f"archive {archive}")
            print(f"evidence {validator.evidence_path(task_id)}")
            print(f"event {event_path}")
        return 0
    except Exception as error:
        rollback_errors: list[str] = []
        for task_id, archive, source_text, event_path in reversed(attempted):
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
        print(f"close aborted and rolled back: {error}", file=sys.stderr)
        for rollback_error in rollback_errors:
            print(f"  - rollback incomplete: {rollback_error}", file=sys.stderr)
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


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Gavin project harness")
    commands = root.add_subparsers(dest="command", required=True)

    index = commands.add_parser("index", help="regenerate metadata indexes")
    index.set_defaults(func=command_index)

    verify = commands.add_parser("verify", help="run all deterministic checks")
    verify.add_argument("task_id", nargs="?")
    verify.set_defaults(func=command_verify)

    close = commands.add_parser("close", help="verify and compress an active spec")
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
