from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from . import events, indexer, lifecycle, product_verification, summarizer, validator


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
                product_verification.ensure_source_clean()
                criteria, mappings = product_verification.verification_contract(args.task_id)
                product_verification.validate_configured_gates(mappings)
                results.extend(product_verification.run_gates(mappings))
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
            results,
        )
        print(f"evidence {evidence}")
    return 0 if validator.passed(results) else 1


def command_close(args: argparse.Namespace) -> int:
    summarizer.validate_task_id(args.task_id)
    if lifecycle.task_status(args.task_id) == "frozen":
        print(
            f"close aborted: {args.task_id} is frozen; resume it before closing",
            file=sys.stderr,
        )
        return 1
    evidence_path = validator.evidence_path(args.task_id)
    evidence_errors = product_verification.validate_evidence(args.task_id, evidence_path)
    if evidence_errors:
        print("close aborted: task evidence is not valid", file=sys.stderr)
        for error in evidence_errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    before = validator.run_checks()
    _print_results(before)
    if not validator.passed(before):
        print("close aborted: pre-close verification failed", file=sys.stderr)
        return 1

    archive: Path | None = None
    event_path: Path | None = None
    proposal_path: Path | None = None
    source_text = ""
    try:
        archive, source_text = summarizer.close_spec(args.task_id)
        event_path, proposal_path = events.emit_event(
            "spec.completed",
            args.task_id,
            "The active spec passed verification and was deterministically compressed.",
            "lifecycle",
            create_proposal=False,
        )
        indexer.write_indexes()
        after = validator.run_checks()
        if not validator.passed(after):
            raise RuntimeError("post-close verification failed")
        _print_results(after)
        print(f"archive {archive}")
        print(f"evidence {evidence_path}")
        print(f"event {event_path}")
        if proposal_path is not None:
            print(f"proposal {proposal_path}")
        return 0
    except Exception as error:
        if source_text:
            summarizer.restore_spec(args.task_id, source_text, archive)
        for path in (event_path, proposal_path):
            if path is not None and path.exists():
                path.unlink()
        indexer.write_indexes()
        print(f"close aborted and rolled back: {error}", file=sys.stderr)
        return 1


def command_emit_event(args: argparse.Namespace) -> int:
    event_path, proposal_path = events.emit_event(
        args.event_type,
        args.task_id,
        args.reason,
        args.source,
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
    emit.set_defaults(func=command_emit_event)
    return root


def main() -> int:
    args = parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
