"""Opt-in real-module CLI acceptance and before/after measurement, never a normal gate.

Run from harness: python -m tools.impact_acceptance --baseline <commit>.
Only local repositories and installed dependencies are used. Raw output stays local.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .config import project_root


def validate_comparison(payload):
    errors = []
    for workload in ("harness", "profile-api"):
        rows = [r for r in payload.get("samples", []) if r.get("workload") == workload]
        if {r.get("version") for r in rows} != {"before", "after"}:
            errors.append(f"{workload}: missing before/after sample")
        for row in rows:
            if (
                row.get("status") != "passed"
                or not row.get("closed")
                or not row.get("evidence_sha256")
            ):
                errors.append(f"{workload}: incomplete real CLI closure")
            if row.get("kind") != "real-module" or row.get("executed", 0) < 1:
                errors.append(f"{workload}: fixture-only or unexecuted sample")
            if not isinstance(row.get("wall_ms"), (float, int)) or row["wall_ms"] <= 0:
                errors.append(f"{workload}: missing wall measurement")
            if not isinstance(row.get("output_bytes"), int):
                errors.append(f"{workload}: missing output byte measurement")
        if len(rows) == 2 and all(r.get("status") == "passed" for r in rows):
            versions = {r["version"]: r for r in rows}
            if versions["after"]["wall_ms"] >= versions["before"]["wall_ms"]:
                errors.append(f"{workload}: total measured cost did not improve")
            if versions["after"]["output_bytes"] > versions["before"]["output_bytes"]:
                errors.append(f"{workload}: output volume increased")
    web = [r for r in payload.get("samples", []) if r.get("workload") == "profile-web"]
    if (
        len(web) != 1
        or web[0].get("status") != "passed"
        or not web[0].get("closed")
        or web[0].get("executed") != 3
        or set(web[0].get("kinds", [])) != {"pytest", "vitest", "playwright"}
    ):
        errors.append(
            "profile-web: missing complete real Pytest/Vitest/Playwright closure"
        )
    return errors


def paired_summary(samples, *, minimum_pairs=3):
    """Keep every sample; never promote failed or asymmetric data to a speedup."""
    report = {}
    workloads = sorted({r["workload"] for r in samples})
    for workload in workloads:
        rows = [r for r in samples if r["workload"] == workload]
        before = [r for r in rows if r["version"] == "before"]
        after = [r for r in rows if r["version"] == "after"]
        valid = (len(before) == len(after) and len(before) >= minimum_pairs
                 and all(r.get("status") == "passed" and r.get("closed") for r in rows)
                 and all(b.get("executed") == a.get("executed") for b, a in zip(before, after)))
        stats = {version: {"median_ms": statistics.median([r["wall_ms"] for r in group]),
                           "range_ms": [min(r["wall_ms"] for r in group), max(r["wall_ms"] for r in group)]}
                 for version, group in (("before", before), ("after", after)) if group}
        report[workload] = {"samples": len(rows), "eligible": valid, **stats,
                            "improved": valid and stats["after"]["median_ms"] < stats["before"]["median_ms"]}
    return report


def run(command, cwd, *, log=None):
    started = time.perf_counter()
    result = subprocess.run(command, cwd=cwd, capture_output=True, check=False)
    output = result.stdout + result.stderr
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_bytes(output)
    return result, round((time.perf_counter() - started) * 1000, 3), len(output)


def git(root, *args):
    result, _, _ = run(["git", *args], root)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace")[:500])
    return result.stdout.decode("utf-8").strip()


def workload_contract(workload):
    if workload == "harness":
        return (
            "harness/tools/result_reporting.py",
            "M08-ACCEPTANCE-REPORTING-01",
            "harness-tests",
            "harness/verification/tests/test_result_reporting.py",
            "test_test_count_parser_handles_project_frameworks_without_double_counting",
        )
    if workload in {"profile-api", "profile-web"}:
        return (
            "apps/api/app/profile_service.py",
            "M06-ACCEPTANCE-PROFILE-01",
            "api-tests",
            "apps/api/tests/test_profile.py",
            "test_public_profile_returns_defaults_when_unconfigured",
        )
    raise ValueError("unknown acceptance workload")


def bind_dependencies(root, source, *, web=False):
    """Own dependency roots in the disposable repo; link package content only.

    Isolation still rejects a dependency root outside its repository. No package
    tree is walked or copied: Python uses one site-packages link; Node needs only
    its immediate package entries. This setup is identical for both engines.
    """
    from .isolated_verification import _create_directory_link, _remove_directory_link

    relatives = ["apps/api/.venv", "node_modules", "apps/web/node_modules"]
    for relative in relatives:
        target = root / relative
        if target.is_symlink() or (
            target.exists() and target.resolve() != target.absolute()
        ):
            _remove_directory_link(target)
    environment = root / "apps/api/.venv"
    source_environment = source / "apps/api/.venv"
    environment.mkdir(exist_ok=True)
    shutil.copy2(source_environment / "pyvenv.cfg", environment / "pyvenv.cfg")
    if sys.platform == "win32":
        (environment / "Scripts").mkdir(exist_ok=True)
        # pytest's bounded RECORD also includes its installed console launchers.
        for executable in (source_environment / "Scripts").iterdir():
            if executable.is_file():
                shutil.copy2(executable, environment / "Scripts" / executable.name)
        destination = environment / "Lib/site-packages"
        if not destination.exists():
            _create_directory_link(
                source_environment / "Lib/site-packages", destination
            )
    else:
        (environment / "bin").mkdir(exist_ok=True)
        shutil.copy2(
            (source_environment / "bin/python").resolve(), environment / "bin/python"
        )
        for directory in (source_environment / "lib").iterdir():
            destination = environment / "lib" / directory.name / "site-packages"
            if not destination.exists():
                _create_directory_link(directory / "site-packages", destination)
    if web:
        for relative in relatives[1:]:
            target = root / relative
            target.mkdir(parents=True, exist_ok=True)
            for entry in (source / relative).iterdir():
                destination = target / entry.name
                if destination.exists():
                    continue
                if entry.is_dir():
                    _create_directory_link(entry, destination)
                elif entry.is_file():
                    shutil.copy2(entry, destination)


def prepare_repository(root, source, baseline, version, workload):

    result, _, _ = run(
        ["git", "clone", "--quiet", "--no-hardlinks", str(source), str(root)], source
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    git(root, "config", "user.name", "Harness Acceptance")
    git(root, "config", "user.email", "harness-acceptance@example.invalid")
    if version == "before":
        # Only the engine changes. Product code, docs, checks, toolchain and
        # workload are identical; preserve all original implementation in Git.
        # Keep newly added helpers present for the common current ownership manifest.
        # The baseline entrypoints do not import them; overwrite its existing engine files only.
        paths = git(root, "ls-tree", "-r", "--name-only", baseline, "--", "harness/tools").splitlines()
        git(root, "restore", "--source=" + baseline, "--", *paths)
    bind_dependencies(root, source, web=workload == "profile-web")
    task = "20260906-acceptance-" + workload
    changed, cid, gate, test_path, test_name = workload_contract(workload)
    file = root / "harness/verification/checks/module_coverage.contract.json"
    contract = json.loads(file.read_bytes())
    selected = {
        "id": cid,
        "priority": "P1",
        "scenario": "Controlled real module acceptance.",
        "expectations": [
            {
                "id": cid + "-E01",
                "surface": "response",
                "statement": "Valid inputs produce the expected module result.",
            },
            {
                "id": cid + "-E02",
                "surface": "forbidden",
                "statement": "Invalid or absent fields do not produce an incorrect result.",
            },
        ],
        "required_gates": [gate],
        "test_refs": [
            {
                "kind": "pytest",
                "path": test_path,
                "name": test_name,
                "gate": gate,
                "covers": [cid + "-E01", cid + "-E02"],
            }
        ],
    }
    next(m for m in contract["modules"] if m["id"] == cid[:3])["cases"].append(selected)
    if workload == "profile-web":
        selected["required_gates"] += ["web-quality", "e2e"]
        for kind, path, name, owner_gate in [
            (
                "vitest",
                "apps/web/tests/unit/profile.test.ts",
                "rejects empty, blank, and over-length values",
                "web-quality",
            ),
            (
                "playwright",
                "apps/web/tests/e2e/profile.spec.ts",
                "homepage shows the default profile card before configuration",
                "e2e",
            ),
        ]:
            selected["test_refs"].append(
                {
                    "kind": kind,
                    "path": path,
                    "name": name,
                    "gate": owner_gate,
                    "covers": [cid + "-E01", cid + "-E02"],
                }
            )
    file.write_text(
        json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # Same explicit minimal registry in both engines isolates engine cost from
    # the size of the migrated registry. Real product source/tests stay intact.
    registry = {
        "schema_version": 1,
        "units": {"workload": {"paths": [changed], "cases": [cid], "dependents": []}},
    }
    (root / "harness/verification/impact/ownership.json").write_text(
        json.dumps(registry), encoding="utf-8"
    )
    analysis = {
        "schema_version": 1,
        "task_id": task,
        "changes": [
            {
                "path": changed,
                "owner": "workload",
                "reason": "Equivalent implementation refactor at the selected module boundary.",
                "cases": [cid],
                "dependencies": [],
            }
        ],
    }
    (root / f"harness/verification/impact/{task}.json").write_text(
        json.dumps(analysis), encoding="utf-8"
    )
    spec = f"""---
id: spec-{task}
level: L1
summary: Controlled real module acceptance
load_when:
  - task:{task}
task_id: {task}
status: active
verification_profile: focused
documentation_impact: none
documentation_reason: Disposable equivalent refactor used only for controlled engine measurement.
---

# Context
Real module acceptance in an isolated local repository.

# Goal
Execute the selected existing test and close the real CLI task.

# Non-goals
No production data, provider calls or business changes.

# Acceptance criteria
- AC-1: Selected module behavior passes and its runner evidence closes the task.

# Risks
Local timing is a sample, not a statistical or token claim.

# Verification plan
## Verification cases
- AC-1 => {cid}
## Gates
- {gate} => AC-1
- harness-integrity => AC-1
"""
    if workload == "profile-web":
        spec += "- web-quality => AC-1\n- e2e => AC-1\n"
    (root / f"harness/specs/active/{task}.md").write_text(spec, encoding="utf-8")
    # Make selected API plugin policy explicit in both versions through runner;
    # all machine credentials remain outside the tracked tree.
    git(root, "add", "--", "harness")
    git(root, "commit", "-qm", "prepare identical acceptance workload")
    path = root / changed
    content = path.read_text(encoding="utf-8")
    if workload == "harness":
        content = content.replace(
            "return counts if matched else None",
            "return counts if matched is True else None",
        )
    else:
        # Equivalent serialization of the default skills is used by the selected
        # public API assertion and the rendered default profile card.
        content = content.replace('skills_json="[]",', "skills_json=json.dumps([]),")
    if content == path.read_text(encoding="utf-8"):
        raise ValueError("controlled implementation mutation did not match")
    path.write_text(content, encoding="utf-8")
    git(root, "add", "--", changed)
    git(root, "commit", "-qm", "controlled module implementation")
    result, _, _ = run(
        [sys.executable, "-m", "tools.harness", "index"], root / "harness"
    )
    if result.returncode:
        raise RuntimeError("acceptance index failed")
    git(root, "add", "--", "harness")
    git(root, "commit", "-qm", "prepare deterministic indexes")
    return task


def sample(root, source, baseline, version, workload, logs):
    task = prepare_repository(root, source, baseline, version, workload)
    return execute_sample(root, version, workload, logs, task)


def execute_sample(root, version, workload, logs, task):
    wall, output = 0, 0
    commands = []
    for args in [
        ("plan", task),
        ("status", task),
        ("verify", task, "--fresh", "--close"),
    ]:
        result, elapsed, size = run(
            [sys.executable, "-m", "tools.harness", *args],
            root / "harness",
            log=logs / ("-".join(args) + ".log"),
        )
        wall += elapsed
        output += size
        commands.append(
            {
                "command": args[0],
                "exit_code": result.returncode,
                "wall_ms": elapsed,
                "output_bytes": size,
            }
        )
        if result.returncode:
            break
    evidence = root / f"harness/verification/evidence/{task}.json"
    payload = json.loads(evidence.read_bytes()) if evidence.is_file() else {}
    counts = [
        c.get("result", {}).get("selection_counts", {})
        for c in payload.get("checks", [])
    ]
    closed = (root / f"harness/specs/archive/{task}.md").is_file()
    return {
        "version": version,
        "workload": workload,
        "kind": "real-module",
        "status": payload.get("status", "failed"),
        "closed": closed,
        "wall_ms": round(wall, 3),
        "output_bytes": output,
        "commands": commands,
        "executed": sum(c.get("executed", 0) for c in counts),
        "collected": sum(c.get("collected", 0) for c in counts),
        "kinds": sorted(
            {
                ref["kind"]
                for criterion in payload.get("verification_cases", {}).get(
                    "criteria", []
                )
                for case in criterion["cases"]
                for ref in case["test_refs"]
            }
        ),
        "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest()
        if evidence.is_file()
        else None,
        "source_commit": git(root, "rev-parse", "HEAD"),
        "logs": str(logs),
        "repository": str(root),
    }


def retain_and_cleanup_sample(row):
    """Export compact close assets before removing a disposable benchmark repo."""
    from .isolated_verification import _remove_directory_link

    root = Path(row["repository"])
    temporary = Path(tempfile.gettempdir()).resolve()
    if (
        root.name != "repository"
        or root.parent.resolve().parent != temporary
        or not root.parent.name.startswith("harness-acceptance-")
    ):
        raise ValueError(
            "acceptance cleanup target is not an owned temporary repository"
        )
    if not root.exists():
        return
    task = "20260906-acceptance-" + row["workload"]
    destination = Path(row["logs"]) / "close-assets"
    destination.mkdir(parents=True, exist_ok=True)
    for path in [
        root / f"harness/verification/evidence/{task}.json",
        root / f"harness/specs/archive/{task}.md",
        root / f"harness/evolution/events/{task}--spec-completed.json",
    ]:
        if path.is_file():
            shutil.copy2(path, destination / path.name)
    for relative in ["node_modules", "apps/web/node_modules", "apps/api/.venv"]:
        folder = root / relative
        if not folder.exists():
            continue
        if folder.resolve() != folder.absolute():
            _remove_directory_link(folder)
            continue
        entries = (
            list(folder.iterdir())
            if relative.endswith("node_modules")
            else list(folder.glob("Lib/site-packages"))
            + list(folder.glob("lib/*/site-packages"))
        )
        for path in entries:
            if path.is_dir() and path.resolve() != path.absolute():
                _remove_directory_link(path)

    def remove_readonly(function, path, _error):
        target = Path(path).resolve()
        if not target.is_relative_to(root.parent.resolve()):
            raise ValueError("acceptance cleanup escaped its temporary root")
        os.chmod(target, stat.S_IREAD | stat.S_IWRITE)
        function(path)

    shutil.rmtree(root.parent, onerror=remove_readonly)
    row["repository_removed"] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--pairs", type=int, default=3, help="alternating before/after pairs per workload (minimum 3)")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Retry failed local samples, preserving their histories and logs",
    )
    args = parser.parse_args()
    if args.pairs < 3:
        parser.error("--pairs must be at least 3")
    source = project_root()
    baseline = git(source, "rev-parse", args.baseline + "^{commit}")
    output = source / ".run/impact-acceptance"
    output.mkdir(parents=True, exist_ok=True)
    if not args.resume:
        output = output / ("run-" + str(time.time_ns()))
        output.mkdir()
        (output.parent / "latest.txt").write_text(output.name, encoding="utf-8")
    elif (output / "latest.txt").is_file():
        output = output / (output / "latest.txt").read_text(encoding="utf-8").strip()
    if args.resume:
        payload = json.loads((output / "comparison.json").read_bytes())
        samples = []
        for previous in payload["samples"]:
            if previous["status"] == "passed" and previous["closed"]:
                samples.append(previous)
                continue
            root = Path(previous["repository"])
            bind_dependencies(root, source, web=previous["workload"] == "profile-web")
            logs = output / (
                previous["workload"] + "-" + previous["version"] + "-retry"
            )
            print(
                "[ACCEPTANCE] retry "
                + previous["workload"]
                + " "
                + previous["version"],
                flush=True,
            )
            result = execute_sample(
                root,
                previous["version"],
                previous["workload"],
                logs,
                "20260906-acceptance-" + previous["workload"],
            )
            result["previous_attempt"] = previous
            samples.append(result)
            print(json.dumps(result), flush=True)
        payload["samples"] = samples
        payload["paired_summary"] = paired_summary(samples)
        payload["errors"] = validate_comparison(payload)
        for workload in ("harness", "profile-api"):
            if not payload["paired_summary"].get(workload, {}).get("improved"):
                payload["errors"].append(workload + ": paired cost threshold not met")
        (output / "comparison.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return bool(payload["errors"])
    samples = []
    for workload in ["harness", "profile-api"]:
        for pair in range(args.pairs):
            for version in (["before", "after"] if pair % 2 == 0 else ["after", "before"]):
                root = Path(tempfile.mkdtemp(prefix="harness-acceptance-")) / "repository"
                print(f"[ACCEPTANCE] {workload} pair {pair + 1} {version}", flush=True)
                row = sample(root, source, baseline, version, workload,
                             output / f"{workload}-{pair + 1}-{version}")
                row["pair"] = pair + 1
                samples.append(row)
                print(json.dumps(row), flush=True)
    root = Path(tempfile.mkdtemp(prefix="harness-acceptance-")) / "repository"
    print(
        "[ACCEPTANCE] profile-web after (real Pytest/Vitest/Playwright closure)",
        flush=True,
    )
    samples.append(
        sample(
            root, source, baseline, "after", "profile-web", output / "profile-web-after"
        )
    )
    print(json.dumps(samples[-1]), flush=True)
    payload = {
        "schema_version": 1,
        "baseline": baseline,
        "candidate": git(source, "rev-parse", "HEAD"),
        "method": "Same product tree, checks, workload, installed dependencies; only harness/tools engine differs. Alternating paired samples; setup excluded; profile-web is a separate integration sample.",
        "samples": samples,
    }
    payload["paired_summary"] = paired_summary(samples)
    payload["errors"] = validate_comparison(payload)
    for workload in ("harness", "profile-api"):
        if not payload["paired_summary"][workload]["improved"]:
            payload["errors"].append(workload + ": paired cost threshold not met")
    if not payload["errors"]:
        for row in samples:
            retain_and_cleanup_sample(row)
    (output / "comparison.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return bool(payload["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
