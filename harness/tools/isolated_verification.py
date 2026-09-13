from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from .config import load_config, project_root
from .product_verification import ProductVerificationError, run_gates


def snapshot_preflight(worktree, mappings):
    from . import impact, validator
    from . import product_verification as pv
    from .run_store import digest
    from .verification_inputs import controlled_environment

    plan = impact.current_plan.get()
    command = [sys.executable, "-m", "tools.snapshot_check"]
    if plan is not None:
        command.append(plan["task_id"])
    started = time.perf_counter()
    completed = subprocess.run(command, cwd=worktree / "harness", capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=120,
                               env=controlled_environment(), check=False)
    try:
        report = json.loads(completed.stdout)
        passed = completed.returncode == 0 and report["version"] == 1 and validator.passed(report["checks"])
        if plan is not None and report["plan_digest"] != digest(plan):
            passed = False
        details = [str(d) for c in report["checks"] if c["status"] != "passed" for d in c.get("details", [])]
    except (ValueError, KeyError, TypeError):
        passed, details = False, ["invalid snapshot preflight report: " + completed.stderr[-600:]]
    gate = "harness-integrity" if "harness-integrity" in mappings else "snapshot-preflight"
    result = {"name": gate, "kind": "product" if gate in mappings else "preflight",
              "command": pv._configured_command_text(pv._configured_gates()[gate]) if gate in mappings else "snapshot-check",
              "status": "passed" if passed else "failed", "passed": passed,
              "covers": mappings.get(gate, []), "duration_ms": round((time.perf_counter() - started) * 1000, 3),
              "details": details, "provenance": {"phase": "snapshot", "scope": "committed-snapshot"},
              "result": {"exit_code": 0 if passed else 1}}
    if not passed:
        result["result"]["failure"] = {"kind": "snapshot-input", "source": "snapshot-runner",
                                        "summary": ("; ".join(details) or "snapshot plan differs from workspace")[:300]}
    return result


def isolation_config() -> dict[str, Any]:
    raw = load_config().get("verification", {}).get("isolation", {})
    if not isinstance(raw, dict):
        raise ProductVerificationError("verification.isolation must be a table")
    mode = str(raw.get("mode", ""))
    if mode != "git-worktree":
        raise ProductVerificationError("verification.isolation.mode must be git-worktree")
    reuse_paths = raw.get("reuse_paths", [])
    if not isinstance(reuse_paths, list):
        raise ProductVerificationError("verification.isolation.reuse_paths must be an array")
    return {"mode": mode, "reuse_paths": [str(value) for value in reuse_paths]}


def _relative_path(value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ProductVerificationError(
            f"isolation reuse path must be project-relative: {value}"
        )
    return relative


def _run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=project_root(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _create_directory_link(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination.symlink_to(source, target_is_directory=True)
        return
    except OSError as symlink_error:
        if os.name != "nt":
            raise ProductVerificationError("dependency directory link failed") from symlink_error
    completed = subprocess.run(
        ["cmd", "/d", "/c", "mklink", "/J", str(destination), str(source)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise ProductVerificationError("dependency directory junction failed")


def _remove_directory_link(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if os.name == "nt":
        path.rmdir()
    else:
        path.unlink()


def _remove_temporary_root(path: Path) -> None:
    last_error: OSError | None = None
    for attempt in range(20):
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except OSError as error:
            last_error = error
            if attempt < 19:
                time.sleep(0.25)
    assert last_error is not None
    raise last_error


def _failure(
    name: str,
    duration_ms: float,
    detail: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "kind": "isolation",
        "command": "git worktree add --detach <temporary> HEAD",
        "status": "failed",
        "passed": False,
        "duration_ms": duration_ms,
        "covers": [],
        "details": [detail],
        "result": {
            "exit_code": None,
            "failure": {"kind": name, "summary": detail[:300]},
        },
    }


def run_in_worktree(
    mappings: dict[str, list[str]],
    source_commit: str,
    *,
    gate_callback: Any = None,
    artifact_root: Path | None = None,
    diagnostic_refs: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    started = time.perf_counter()
    context: dict[str, Any] = {
        "mode": "git-worktree",
        "source_commit": source_commit,
        "cleanup_status": "failed",
    }
    results: list[dict[str, Any]] = []
    temporary_root: Path | None = None
    worktree: Path | None = None
    registered = False
    links: list[Path] = []
    setup_error: str | None = None
    cleanup_errors: list[str] = []

    try:
        config = isolation_config()
        root = project_root().resolve()
        temporary_root = Path(
            tempfile.mkdtemp(
                prefix=f".{root.name}-task-verify-",
                dir=tempfile.gettempdir(),
            )
        )
        worktree = temporary_root / "worktree"
        added = _run_git("worktree", "add", "--detach", str(worktree), source_commit)
        if added.returncode != 0:
            raise ProductVerificationError("temporary Git worktree creation failed")
        registered = True

        snapshot = snapshot_preflight(worktree, mappings)
        results.append(snapshot)
        if snapshot["name"] in mappings and gate_callback is not None:
            gate_callback(snapshot["name"], None)
            gate_callback(snapshot["name"], snapshot)
        if not snapshot["passed"]:
            context["not_run"] = [gate for gate in mappings if gate != snapshot["name"]]
            raise ProductVerificationError("committed snapshot preflight failed; consumers not-run")
        remaining = {gate: covers for gate, covers in mappings.items() if gate != snapshot["name"]}

        from .impact import current_plan, dependency_paths
        reuse_paths = dependency_paths(mappings) if current_plan.get() is not None else config["reuse_paths"]
        for raw_path in reuse_paths:
            relative = _relative_path(raw_path)
            source = (root / relative).resolve()
            if not source.is_dir() or not source.is_relative_to(root):
                raise ProductVerificationError(
                    f"isolation dependency source is missing or outside project: {raw_path}"
                )
            destination = worktree / relative
            if destination.exists() or destination.is_symlink():
                raise ProductVerificationError(
                    f"isolation dependency target already exists: {raw_path}"
                )
            _create_directory_link(source, destination)
            links.append(destination)

        selection_options = {}
        if diagnostic_refs is not None:
            selection_file = worktree / ".run" / "harness-diagnostic-selection.json"
            selection_file.parent.mkdir(parents=True, exist_ok=True)
            selection_file.write_text(json.dumps(diagnostic_refs), encoding="utf-8")
            selection_options["selected_refs_file"] = selection_file
        if gate_callback is None and artifact_root is None and not selection_options:
            results.extend(run_gates(remaining, execution_root=worktree))
        else:
            results.extend(run_gates(remaining, execution_root=worktree, gate_callback=gate_callback, artifact_root=artifact_root, **selection_options))
    except Exception as error:  # noqa: BLE001 - cleanup must cover every gate failure
        setup_error = str(error)
    finally:
        if artifact_root is not None and worktree is not None:
            try:
                from .run_artifacts import retain
                retain(worktree, artifact_root)
            except OSError:
                cleanup_errors.append("diagnostic export failed; worktree retained")
        for link in reversed(links):
            try:
                _remove_directory_link(link)
            except OSError:
                cleanup_errors.append("dependency link removal failed")
        if registered and not cleanup_errors and worktree is not None:
            removed = _run_git("worktree", "remove", "--force", str(worktree))
            if removed.returncode != 0:
                cleanup_errors.append("Git worktree removal failed")
            else:
                _run_git("worktree", "prune")
        if temporary_root is not None and not cleanup_errors:
            try:
                _remove_temporary_root(temporary_root)
            except OSError:
                cleanup_errors.append("temporary verification root removal failed")

    total_duration_ms = round((time.perf_counter() - started) * 1000, 3)
    gate_duration_ms = sum(float(result.get("duration_ms", 0) or 0) for result in results)
    isolation_duration_ms = round(max(0.0, total_duration_ms - gate_duration_ms), 3)
    if not cleanup_errors:
        context["cleanup_status"] = "passed"
        context["reused_paths"] = len(links)
    if cleanup_errors:
        results.append(
            _failure(
                "isolated-worktree-cleanup",
                isolation_duration_ms,
                cleanup_errors[0],
            )
        )
    elif setup_error is not None:
        results.append(
            _failure("isolated-worktree-setup", isolation_duration_ms, setup_error)
        )
    else:
        results.append(
            {
                "name": "isolated-worktree",
                "kind": "isolation",
                "command": "git worktree add --detach <temporary> HEAD",
                "status": "passed",
                "passed": True,
                "duration_ms": isolation_duration_ms,
                "covers": [],
                "details": ["temporary worktree and dependency links were removed"],
                "result": {"exit_code": 0},
            }
        )
    return results, context
