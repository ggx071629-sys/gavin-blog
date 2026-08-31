from __future__ import annotations

import json
import subprocess
import tomllib
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
        "specs": {"active": "specs/active", "archive": "specs/archive"},
        "verification": {
            "evidence": "verification/evidence",
            "source_paths": ["apps", "harness/tools"],
        },
        "evolution": {"events": "evolution/events"},
        "indexes": {"specs": {"path": "specs"}},
        "change_enforcement": {
            "risk_prefixes": ["apps/", "harness/"],
            "risk_files": ["AGENTS.md", "README.md", "package.json"],
        },
    }
    monkeypatch.setattr(change_enforcement, "project_root", lambda: tmp_path)
    monkeypatch.setattr(change_enforcement, "harness_root", lambda: tmp_path / "harness")
    monkeypatch.setattr(change_enforcement, "load_config", lambda: config)
    monkeypatch.setattr(change_enforcement, "ensure_source_clean", lambda: None)
    _write(tmp_path, "README.md", "baseline\n")
    _commit(tmp_path, "baseline")
    return tmp_path


def _closed_task(
    root: Path,
    source: str,
    *,
    task_id: str = TASK_ID,
    schema: int = 2,
) -> None:
    archive = (
        "---\n"
        f"id: archive-{task_id}\n"
        "level: L2\n"
        "summary: fixture\n"
        f"task_id: {task_id}\n"
        "status: compressed\n"
        "load_when:\n"
        f"  - task:{task_id}\n"
        "---\n\n# Fixture\n"
    )
    source_tree = _git(root, "rev-parse", f"{source}^{{tree}}")
    evidence = {
        "schema_version": schema,
        "task_id": task_id,
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
    _write(root, f"harness/specs/archive/{task_id}.md", archive)
    _write(root, f"harness/verification/evidence/{task_id}.json", json.dumps(evidence))


def test_root_readme_change_requires_closed_task(repository: Path) -> None:
    base = _git(repository, "rev-parse", "HEAD")
    _write(repository, "README.md", "changed project contract\n")
    _commit(repository, "docs")

    result = change_enforcement.inspect_change(base)

    assert result["passed"] is False
    assert result["tasks"] == []
    assert result["risk_paths"] == ["README.md"]


def test_non_risk_change_does_not_require_task(repository: Path) -> None:
    base = _git(repository, "rev-parse", "HEAD")
    _write(repository, "notes.txt", "non-risk fixture\n")
    _commit(repository, "notes")

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


def test_evidence_cannot_cover_a_later_risk_change(repository: Path) -> None:
    base = _git(repository, "rev-parse", "HEAD")
    _write(repository, "apps/api.py", "value = 1\n")
    source = _commit(repository, "implementation")
    _closed_task(repository, source)
    _commit(repository, "close task")
    _write(repository, "apps/api.py", "value = 2\n")
    _commit(repository, "unverified follow-up")

    result = change_enforcement.inspect_change(base)

    assert result["passed"] is False
    assert result["tasks"] == []
    assert "risk changes after source_commit: apps/api.py" in result["details"][0]


def test_only_exact_task_close_artifacts_and_generated_indexes_are_allowed(
    repository: Path,
) -> None:
    base = _git(repository, "rev-parse", "HEAD")
    _write(repository, "apps/api.py", "value = 1\n")
    source = _commit(repository, "implementation")
    _closed_task(repository, source)
    _write(repository, f"harness/specs/active/{TASK_ID}.md", "temporary\n")
    _write(
        repository,
        f"harness/evolution/events/{TASK_ID}--spec-completed.json",
        "{}\n",
    )
    _write(repository, "harness/specs/INDEX.md", "generated\n")
    _commit(repository, "close task")

    result = change_enforcement.inspect_change(base)

    assert result["passed"] is True
    assert result["tasks"] == [TASK_ID]

    _write(repository, "harness/evolution/events/other--spec-completed.json", "{}\n")
    _commit(repository, "tamper with another event")
    result = change_enforcement.inspect_change(base)
    assert result["passed"] is False
    assert "other--spec-completed.json" in result["details"][0]


def test_newest_valid_task_can_cover_an_older_task_and_later_risk_change(
    repository: Path,
) -> None:
    newer_task = "20260812-newer-change"
    base = _git(repository, "rev-parse", "HEAD")
    _write(repository, "apps/api.py", "value = 1\n")
    first_source = _commit(repository, "first implementation")
    _closed_task(repository, first_source)
    _commit(repository, "close first task")
    _write(repository, "apps/api.py", "value = 2\n")
    second_source = _commit(repository, "second implementation")
    _closed_task(repository, second_source, task_id=newer_task)
    _commit(repository, "close second task")

    result = change_enforcement.inspect_change(base)

    assert result["passed"] is True
    assert result["tasks"] == [newer_task]


def test_project_risk_scope_covers_implementation_control_plane_and_root_files() -> None:
    root = Path(__file__).resolve().parents[3]
    with (root / "harness" / "config.toml").open("rb") as handle:
        config = tomllib.load(handle)
    expected = [
        ".github/CODEOWNERS",
        "apps/api/app/main.py",
        "packages/example/package.json",
        "scripts/check.mjs",
        "harness/docs/decisions/example.md",
        "harness/evolution/policy.md",
        "harness/telemetry/README.md",
        "harness/verification/README.md",
        "AGENTS.md",
        "README.md",
        ".gitattributes",
        ".gitignore",
        "package.json",
        "package-lock.json",
    ]

    assert change_enforcement.risk_paths(expected, config) == sorted(expected)


def test_failure_details_are_newest_first_and_bounded(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _git(repository, "rev-parse", "HEAD")
    _write(repository, "apps/api.py", "value = 1\n")
    source = _commit(repository, "implementation")
    task_ids = [f"20260812-fixture-{index:02d}" for index in range(6)]
    for task_id in task_ids:
        _closed_task(repository, source, task_id=task_id, schema=1)
    _commit(repository, "invalid task artifacts")
    monkeypatch.setattr(change_enforcement, "FAILURE_DETAIL_LIMIT", 3)

    result = change_enforcement.inspect_change(base)

    assert result["passed"] is False
    assert len(result["details"]) == 4
    assert task_ids[-1] in result["details"][0]
    assert result["details"][-1].endswith("additional task validation error(s) omitted")


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
