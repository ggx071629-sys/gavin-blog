from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

from .config import harness_root, load_config, project_root
from .result_reporting import summarize_checks, summarize_criteria
from .verification_config import required_check_names


def _load_check(path: Path) -> ModuleType:
    name = f"_harness_check_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load check: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_checks(*, close_assets: bool = False) -> list[dict[str, Any]]:
    config = load_config()
    root = harness_root()
    context = {
        "config": config,
        "harness_root": root,
        "project_root": project_root(),
    }
    results: list[dict[str, Any]] = []
    checks_dir = root / str(config["verification"]["checks"])
    for path in sorted(checks_dir.glob("*.py")):
        if close_assets and path.stem == "module_coverage":
            continue  # Collector proof is authenticated against unchanged inputs at close.
        started = time.perf_counter()
        try:
            module = _load_check(path)
            result = dict(module.run(context))
            result.setdefault("name", path.stem)
            result.setdefault("details", [])
            result["status"] = "passed" if bool(result.get("passed")) else "failed"
        except Exception as error:  # noqa: BLE001 - each plugin check must fail closed
            result = {
                "name": path.stem,
                "passed": False,
                "status": "failed",
                "details": [f"{type(error).__name__}: {error}"],
            }
        result["duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
        results.append(result)
    registration_errors: list[str] = []
    try:
        required = required_check_names(config)
    except ValueError as error:
        registration_errors.append(str(error))
    else:
        counts = Counter(str(result.get("name", "")) for result in results)
        for name in required:
            if close_assets and name == "module-coverage":
                continue
            if counts[name] == 0:
                registration_errors.append(f"required check is not registered: {name}")
            elif counts[name] != 1:
                registration_errors.append(
                    f"required check must be registered exactly once: {name}"
                )
    if registration_errors:
        results.append(
            {
                "name": "required-check-registration",
                "passed": False,
                "status": "failed",
                "duration_ms": 0,
                "details": registration_errors,
            }
        )
    return results


def run_close_checks() -> list[dict[str, Any]]:
    return run_checks(close_assets=True)


def passed(results: list[dict[str, Any]]) -> bool:
    return bool(results) and all(result.get("status") == "passed" for result in results)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def evidence_path(task_id: str) -> Path:
    config = load_config()
    return harness_root() / str(config["verification"]["evidence"]) / f"{task_id}.json"


def write_evidence(task_id: str, command: str, results: list[dict[str, Any]]) -> Path:
    root = harness_root()
    artifacts: dict[str, str] = {}
    candidates = [
        project_root() / "AGENTS.md",
        root / "config.toml",
        *sorted(root.rglob("INDEX.md")),
    ]
    for path in candidates:
        if path.is_file():
            artifacts[path.relative_to(project_root()).as_posix()] = _hash(path)

    manifest = {
        "schema_version": 1,
        "task_id": task_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "status": "passed" if passed(results) else "failed",
        "checks": [
            {
                "name": result["name"],
                "status": result["status"],
                "duration_ms": result["duration_ms"],
                "details": result.get("details", []),
            }
            for result in results
        ],
        "artifact_hashes": artifacts,
        "source_commit": _source_commit(),
    }
    path = evidence_path(task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def write_task_evidence(
    task_id: str,
    command: str,
    acceptance_criteria: list[str],
    mappings: dict[str, list[str]],
    verification_profile: str,
    fingerprints: dict[str, str],
    documentation: dict[str, Any],
    execution: dict[str, Any],
    results: list[dict[str, Any]],
    verification_cases: dict[str, Any] | None = None,
    *, prepared: dict[str, Any] | None = None,
) -> Path:
    manifest = {
        "schema_version": 2,
        "task_id": task_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "status": "passed" if passed(results) else "failed",
        "acceptance_criteria": acceptance_criteria,
        "criteria_results": summarize_criteria(acceptance_criteria, mappings, results),
        "verification_profile": verification_profile,
        "fingerprints": fingerprints,
        "documentation": documentation,
        "execution": execution,
        "verification_cases": verification_cases or {},
        "checks": [
            {
                key: value
                for key, value in result.items()
                if key not in {"passed"}
            }
            for result in results
        ],
        "summary": summarize_checks(results),
        "source_commit": _source_commit(),
    }
    path = evidence_path(task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if prepared is not None and manifest["status"] == "passed":
        import tempfile
        from .product_verification import validate_evidence
        with tempfile.TemporaryDirectory(prefix="harness-evidence-candidate-") as temporary:
            candidate = Path(temporary) / "candidate.json"
            candidate.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            errors = validate_evidence(task_id, candidate, prepared=prepared)
        if errors:
            results.append({"name": "close-readiness", "status": "failed", "passed": False,
                            "duration_ms": 0, "details": errors[:12]})
            return write_task_evidence(task_id, command, acceptance_criteria, mappings,
                                       verification_profile, fingerprints, documentation,
                                       execution, results, verification_cases)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path
