"""Small real repositories exercise CLI, worktree, receipts and close as one contract."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import venv
from pathlib import Path

from harness.verification.tests.test_module_coverage import _write_project

TASK = "20260905-impact-cli"
REPO = Path(__file__).resolve().parents[3]


def fixture_repository(tmp_path, *, reuse=True, fault=None, docs=False):
    root = tmp_path / "repository"
    root.mkdir()
    _write_project(root)
    shutil.copytree(
        REPO / "harness/tools",
        root / "harness/tools",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    shutil.copy2(REPO / "harness/config.toml", root / "harness/config.toml")
    for name in ("module_coverage.py", "history_integrity.py"):
        shutil.copy2(
            REPO / "harness/verification/checks" / name,
            root / "harness/verification/checks" / name,
        )
    if fault == "late-gate":
        marker = tmp_path / "fault"
        marker.touch()
        (root / "harness/verification/checks/injected.py").write_text(
            "from pathlib import Path\ndef run(context):\n"
            f"    failed = Path({str(marker)!r}).exists() and (context['project_root'] / '.git').is_file()\n"
            "    return {'name': 'injected', 'passed': not failed, 'details': ['injected gate fault'] if failed else []}\n"
        )
    if fault in {"cleanup", "interrupt"}:
        marker = tmp_path / "fault"
        marker.touch()
        isolation = root / "harness/tools/isolated_verification.py"
        isolation.write_text(
            isolation.read_text()
            + f"""
_fixture_run = run_in_worktree
def run_in_worktree(*args, **kwargs):
    if Path({str(marker)!r}).exists() and {fault!r} == 'interrupt':
        raise KeyboardInterrupt('injected interruption')
    results, context = _fixture_run(*args, **kwargs)
    if Path({str(marker)!r}).exists():
        context['cleanup_status'] = 'failed'
        results.append(_failure('isolated-worktree-cleanup', 0, 'injected cleanup failure'))
    return results, context
"""
        )
    if fault == "close-source":
        (root / "harness/verification/checks/injected.py").write_text(
            "def run(context):\n"
            f"    if (context['harness_root'] / 'specs/archive/{TASK}.md').exists():\n"
            "        (context['harness_root'] / 'tools/fixture.py').write_text('changed during close')\n"
            "    return {'name': 'injected', 'passed': True, 'details': []}\n"
        )
    if fault == 'readonly':
        marker = tmp_path / 'readonly'
        for filename, function in [('product_verification.py', 'run_gates'), ('test_collection.py', '_run')]:
            path = root/'harness/tools'/filename
            path.write_text(path.read_text()+f'''
_readonly_original_{function} = {function}
def {function}(*args, **kwargs):
    from pathlib import Path
    if Path({str(marker)!r}).exists():
        raise RuntimeError('readonly command attempted tests, build or collection')
    return _readonly_original_{function}(*args, **kwargs)
''')
    config = root / "harness/config.toml"
    config.write_text(
        config.read_text().replace("reuse = false", f"reuse = {str(reuse).lower()}")
    )
    venv.EnvBuilder(system_site_packages=True).create(root / "apps/api/.venv")
    (root / ".gitignore").write_text(
        ".venv/\n__pycache__/\n.pytest_cache/\nharness/telemetry/local/\n"
    )
    spec = root / "harness/specs/active" / f"{TASK}.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(f"""---
id: spec-{TASK}
level: L1
summary: CLI impact fixture
load_when:
  - task:{TASK}
task_id: {TASK}
status: active
verification_profile: focused
documentation_impact: none
documentation_reason: Disposable integration fixture.
---

# Context

Real CLI fixture.

# Goal

Execute one exact test and close using its receipt.

# Acceptance criteria

- AC-1: Selected test passes; unrelated tests do not run.

# Verification plan

## Verification cases

- AC-1 => M08-TRACE-P0

## Gates

- harness-tests => AC-1
- harness-integrity => AC-1
""")
    folder = root / "harness/verification/impact"
    folder.mkdir()
    (folder / "ownership.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "units": {
                    "M08.fixture": {
                        "paths": ["harness/tools/fixture.py"],
                        "cases": ["M08-TRACE-P0"],
                        "dependents": [],
                    }
                },
            }
        )
    )
    (folder / f"{TASK}.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "task_id": TASK,
                "changes": [
                    {
                        "path": "harness/tools/fixture.py",
                        "owner": "M08.fixture",
                        "reason": "behavior fixture",
                        "cases": ["M08-TRACE-P0"],
                        "dependencies": [],
                    }
                ],
            }
        )
    )
    # Fail if unselected definitions are accidentally executed.
    tests = root / "harness/verification/tests/contract_fixture.py"
    tests.write_text(
        tests.read_text().replace(
            "    pass", "    assert False, 'unselected test executed'"
        )
    )
    tests.write_text(
        tests.read_text().replace(
            "def test_m08_p0():\n    assert False, 'unselected test executed'",
            "def test_m08_p0():\n    print('SELECTED-ONLY')\n    assert True",
        )
    )
    implementation = "harness/tools/fixture.py"
    if docs:
        implementation = "README.md"
        spec.write_text(spec.read_text().replace("- harness-tests => AC-1\n", ""))
        for name in ("ownership.json", f"{TASK}.json"):
            path = folder / name
            path.write_text(
                path.read_text().replace("harness/tools/fixture.py", "README.md")
            )
        path = root / "harness/verification/checks/module_coverage.contract.json"
        contract = json.loads(path.read_bytes())
        case = next(
            c
            for m in contract["modules"]
            for c in m["cases"]
            if c["id"] == "M08-TRACE-P0"
        )
        case["required_gates"] = ["harness-integrity"]
        case["test_refs"] = [
            {
                "kind": "harness-check",
                "path": "harness/verification/checks/module_coverage.py",
                "name": "module-coverage",
                "gate": "harness-integrity",
                "covers": [e["id"] for e in case["expectations"]],
            }
        ]
        path.write_text(json.dumps(contract))
    for command in (
        ["init"],
        ["config", "user.name", "Harness Fixture"],
        ["config", "user.email", "fixture@example.invalid"],
        ["add", "."],
        ["commit", "-qm", "spec fixture"],
    ):
        git(root, *command)
    (root / implementation).write_text("VALUE = 1\n")
    git(root, "add", implementation)
    git(root, "commit", "-qm", "selected implementation")
    return root


def git(root, *args):
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def cli(root, *args):
    result = subprocess.run(
        [sys.executable, "-m", "tools.harness", *args],
        cwd=root / "harness",
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    return result


def test_real_cli_all_reuse_and_close_have_complete_isolation(tmp_path):
    root = fixture_repository(tmp_path)
    first = cli(root, "verify", TASK)
    assert first.returncode == 0, first.stdout + first.stderr
    second = cli(root, "verify", TASK)
    assert second.returncode == 0, second.stdout + second.stderr
    evidence_path = root / "harness/verification/evidence" / f"{TASK}.json"
    evidence = json.loads(evidence_path.read_bytes())
    assert [
        c["provenance"]["mode"]
        for c in evidence["checks"]
        if c.get("kind") == "product"
    ] == ["reused", "reused"]
    assert len([c for c in evidence["checks"] if c.get("kind") == "isolation"]) == 1
    for command in ("plan", "status"):
        read = cli(root, command, TASK)
        assert read.returncode == 0, read.stdout + read.stderr
        assert "SELECTED-ONLY" not in read.stdout
    expected = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    close = cli(root, "close", TASK)
    assert close.returncode == 0, close.stdout + close.stderr
    archive = root / "harness/specs/archive" / f"{TASK}.md"
    assert expected in archive.read_text()
    events = list((root / "harness/evolution/events").glob("*spec*json"))
    assert len(events) == 1 and expected in events[0].read_text()
    assert not (root / "harness/specs/active" / f"{TASK}.md").exists()
    assert "SELECTED-ONLY" not in close.stdout
    assert len(git(root, "worktree", "list", "--porcelain").split("worktree ")) == 2


def test_real_cli_same_process_fresh_close_and_tamper_rejection(tmp_path):
    root = fixture_repository(tmp_path, reuse=False)
    verify = cli(root, "verify", TASK)
    assert verify.returncode == 0, verify.stdout + verify.stderr
    evidence = root / "harness/verification/evidence" / f"{TASK}.json"
    evidence.write_bytes(evidence.read_bytes() + b" ")
    close = cli(root, "close", TASK)
    assert close.returncode != 0 and "evidence bytes" in close.stdout + close.stderr
    fresh = cli(root, "verify", TASK, "--fresh", "--close")
    assert fresh.returncode == 0, fresh.stdout + fresh.stderr


def test_real_cli_partial_reuse_preserves_failed_attempt(tmp_path):
    root = fixture_repository(tmp_path, fault="late-gate")
    first = cli(root, "verify", TASK)
    assert first.returncode != 0, first.stdout
    (tmp_path / "fault").unlink()
    second = cli(root, "verify", TASK, "--close")
    assert second.returncode == 0, second.stdout + second.stderr
    evidence = json.loads(
        (root / "harness/verification/evidence" / f"{TASK}.json").read_bytes()
    )
    modes = {
        c["name"]: c["provenance"]["mode"]
        for c in evidence["checks"]
        if c.get("kind") == "product"
    }
    # The former late integrity fault is now detected before any tests run.
    assert modes == {"harness-tests": "executed", "harness-integrity": "executed"}


def test_real_cli_cleanup_and_interrupt_cannot_close(tmp_path):
    for fault in ("cleanup", "interrupt"):
        folder = tmp_path / fault
        folder.mkdir()
        root = fixture_repository(folder, fault=fault)
        failed = cli(root, "verify", TASK)
        assert failed.returncode != 0
        close = cli(root, "close", TASK)
        assert close.returncode != 0
        assert not (root / "harness/specs/archive" / f"{TASK}.md").exists()
        (folder / "fault").unlink()
        retry = cli(root, "verify", TASK, "--close")
        assert retry.returncode == 0, retry.stdout + retry.stderr


def test_real_docs_close_has_no_test_collection_or_dependencies(tmp_path):
    root = fixture_repository(tmp_path, docs=True)
    result = cli(root, "verify", TASK, "--close")
    assert result.returncode == 0, result.stdout + result.stderr
    evidence = json.loads(
        (root / "harness/verification/evidence" / f"{TASK}.json").read_bytes()
    )
    assert evidence["execution"]["reused_paths"] == 0
    assert evidence["execution"]["impact"]["selected_refs"] == 0
    assert [c["name"] for c in evidence["checks"] if c.get("kind") == "product"] == [
        "harness-integrity"
    ]


def test_real_plan_status_and_close_cannot_start_gates_or_collectors(tmp_path):
    root=fixture_repository(tmp_path, fault='readonly')
    marker=tmp_path/'readonly'
    marker.touch()
    for command in ['plan','status']:
        result=cli(root,command,TASK)
        assert result.returncode==0,result.stdout+result.stderr
    marker.unlink()
    verify=cli(root,'verify',TASK)
    assert verify.returncode==0,verify.stdout+verify.stderr
    marker.touch()
    for command in ['plan','status','close']:
        result=cli(root,command,TASK)
        assert result.returncode==0,result.stdout+result.stderr
    assert (root/f'harness/specs/archive/{TASK}.md').is_file()


def test_real_close_source_race_rolls_back_and_concurrent_cli_is_rejected(tmp_path):
    root = fixture_repository(tmp_path, fault="close-source")
    verify = cli(root, "verify", TASK)
    assert verify.returncode == 0, verify.stdout + verify.stderr
    command = [
        sys.executable,
        "-c",
        ("from tools.run_store import repository_lock; import sys; "
         "lock=repository_lock(); lock.__enter__(); print('locked', flush=True); sys.stdin.readline(); lock.__exit__(None,None,None)"),
    ]
    process = subprocess.Popen(
        command,
        cwd=root / "harness",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    try:
        assert process.stdout.readline().strip() == "locked"
        concurrent = cli(root, "verify", TASK)
        assert (
            concurrent.returncode != 0
            and "repository lock" in concurrent.stdout + concurrent.stderr
        )
    finally:
        process.communicate("done\n", timeout=10)
    # The rejected contender must not revoke the previous successful receipt.
    close = cli(root, "close", TASK)
    assert (
        close.returncode != 0 and "changed during close" in close.stdout + close.stderr
    )
    assert (root / "harness/specs/active" / f"{TASK}.md").exists()
    assert not (root / "harness/specs/archive" / f"{TASK}.md").exists()
    assert not list((root / "harness/evolution/events").glob("*spec*json"))
