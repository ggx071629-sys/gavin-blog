from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from harness.tools import change_enforcement

TASK_ID = "20260812-example-change"


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _commit(root: Path, message: str) -> str:
    _git(root, "add", ".")
    _git(root, "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD")


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "harness@example.test")
    _git(tmp_path, "config", "user.name", "Harness Test")
    (tmp_path / "harness").mkdir()
    config = {
        "specs": {"archive": "specs/archive"},
        "verification": {
            "evidence": "verification/evidence",
            "source_paths": ["apps", "harness/tools"],
        },
        "change_enforcement": {
            "risk_prefixes": ["apps/", "harness/tools/"],
            "risk_files": ["package.json"],
        },
    }
    monkeypatch.setattr(change_enforcement, "project_root", lambda: tmp_path)
    monkeypatch.setattr(change_enforcement, "harness_root", lambda: tmp_path / "harness")
    monkeypatch.setattr(change_enforcement, "load_config", lambda: config)
    monkeypatch.setattr(change_enforcement, "ensure_source_clean", lambda: None)
    _write(tmp_path, "README.md", "baseline\n")
    _commit(tmp_path, "baseline")
    return tmp_path


def _closed_task(root: Path, source: str, *, schema: int = 2) -> None:
    archive = (
        "---\n"
        f"id: archive-{TASK_ID}\n"
        "level: L2\n"
        "summary: fixture\n"
        f"task_id: {TASK_ID}\n"
        "status: compressed\n"
        "load_when:\n"
        f"  - task:{TASK_ID}\n"
        "---\n\n# Fixture\n"
    )
    source_tree = _git(root, "rev-parse", f"{source}^{{tree}}")
    evidence = {
        "schema_version": schema,
        "task_id": TASK_ID,
        "status": "passed",
        "source_commit": source,
        "fingerprints": {"source_tree": source_tree},
        "execution": {
            "mode": "git-worktree",
            "source_commit": source,
            "cleanup_status": "passed",
        },
        "checks": [
            {"name": "tests", "kind": "product", "status": "passed"},
            {"name": "isolated-worktree", "kind": "isolation", "status": "passed"},
        ],
    }
    _write(root, f"harness/specs/archive/{TASK_ID}.md", archive)
    _write(root, f"harness/verification/evidence/{TASK_ID}.json", json.dumps(evidence))


def test_documentation_only_change_does_not_require_task(repository: Path) -> None:
    base = _git(repository, "rev-parse", "HEAD")
    _write(repository, "README.md", "documentation only\n")
    _commit(repository, "docs")

    result = change_enforcement.inspect_change(base)

    assert result["passed"] is True
    assert result["risk_paths"] == []


def test_risk_change_without_closed_task_fails(repository: Path) -> None:
    base = _git(repository, "rev-parse", "HEAD")
    _write(repository, "apps/api.py", "value = 1\n")
    _commit(repository, "implementation")

    result = change_enforcement.inspect_change(base)

    assert result["passed"] is False
    assert result["tasks"] == []
    assert result["risk_paths"] == ["apps/api.py"]


def test_current_v2_task_evidence_covers_risk_change(repository: Path) -> None:
    base = _git(repository, "rev-parse", "HEAD")
    _write(repository, "apps/api.py", "value = 1\n")
    source = _commit(repository, "implementation")
    _closed_task(repository, source)
    _commit(repository, "close task")

    result = change_enforcement.inspect_change(base)

    assert result["passed"] is True
    assert result["tasks"] == [TASK_ID]


def test_schema_v1_evidence_cannot_cover_change(repository: Path) -> None:
    base = _git(repository, "rev-parse", "HEAD")
    _write(repository, "apps/api.py", "value = 1\n")
    source = _commit(repository, "implementation")
    _closed_task(repository, source, schema=1)
    _commit(repository, "close task")

    result = change_enforcement.inspect_change(base)

    assert result["passed"] is False
    assert "schema_version must be 2" in result["details"][0]


def test_evidence_source_must_be_after_base(repository: Path) -> None:
    old_source = _git(repository, "rev-parse", "HEAD")
    _write(repository, "README.md", "new base\n")
    base = _commit(repository, "new base")
    _write(repository, "apps/api.py", "value = 1\n")
    _commit(repository, "implementation")
    _closed_task(repository, old_source)
    _commit(repository, "reuse old task")

    result = change_enforcement.inspect_change(base)

    assert result["passed"] is False
    assert "must be after the change base" in result["details"][0]


def test_invalid_ref_has_actionable_error(repository: Path) -> None:
    with pytest.raises(change_enforcement.ChangeEnforcementError, match="unknown-ref"):
        change_enforcement.inspect_change("unknown-ref")


def test_release_runner_wires_explicit_change_refs() -> None:
    root = Path(__file__).resolve().parents[3]
    runner = (root / "scripts" / "run-release-check.mjs").read_text(encoding="utf-8")

    assert "process.env.HARNESS_BASE_REF" in runner
    assert "process.env.HARNESS_HEAD_REF || 'HEAD'" in runner
    assert "'change-check', '--base', harnessBaseRef, '--head', harnessHeadRef" in runner
    assert "change coverage skipped" in runner
