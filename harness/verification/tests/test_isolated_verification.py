from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from harness.tools import isolated_verification


@pytest.fixture(autouse=True)
def snapshot_stub(monkeypatch):
    monkeypatch.setattr(isolated_verification, "snapshot_preflight", lambda *_: {
        "name": "snapshot-preflight", "status": "passed", "passed": True, "duration_ms": 0})


def _completed(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, 0, "", "")


def test_isolated_gate_run_uses_detached_worktree_and_cleans_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    temporary = tmp_path / "gavin-task-verify-fixture"
    calls: list[tuple[str, ...]] = []
    gate_roots: list[Path] = []
    mkdtemp_options: list[dict[str, object]] = []
    monkeypatch.setattr(isolated_verification, "project_root", lambda: project)
    monkeypatch.setattr(
        isolated_verification,
        "isolation_config",
        lambda: {"mode": "git-worktree", "reuse_paths": []},
    )
    monkeypatch.setattr(
        isolated_verification.tempfile,
        "mkdtemp",
        lambda **options: str(
            mkdtemp_options.append(options) or temporary.mkdir() or temporary
        ),
    )

    def run_git(*args: str) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[:2] == ("worktree", "add"):
            Path(args[-2]).mkdir()
        elif args[:2] == ("worktree", "remove"):
            shutil.rmtree(Path(args[-1]))
        return _completed(*args)

    monkeypatch.setattr(isolated_verification, "_run_git", run_git)

    def run_gates(
        _: dict[str, list[str]],
        *,
        execution_root: Path,
    ) -> list[dict[str, object]]:
        gate_roots.append(execution_root)
        return [
            {
                "name": "fixture",
                "kind": "product",
                "status": "passed",
                "passed": True,
            }
        ]

    monkeypatch.setattr(isolated_verification, "run_gates", run_gates)

    results, context = isolated_verification.run_in_worktree(
        {"fixture": ["AC-1"]},
        "abc123",
    )

    assert gate_roots == [temporary / "worktree"]
    assert mkdtemp_options == [
        {"prefix": ".project-task-verify-", "dir": isolated_verification.tempfile.gettempdir()}
    ]
    assert calls[0][:3] == ("worktree", "add", "--detach")
    assert ("worktree", "remove", "--force", str(temporary / "worktree")) in calls
    assert results[-1]["name"] == "isolated-worktree"
    assert context["cleanup_status"] == "passed"
    assert not temporary.exists()


def test_dependency_link_removal_preserves_source(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    source.joinpath("sentinel.txt").write_text("keep", encoding="utf-8")

    isolated_verification._create_directory_link(source, destination)
    assert destination.joinpath("sentinel.txt").read_text(encoding="utf-8") == "keep"

    isolated_verification._remove_directory_link(destination)
    assert not destination.exists()
    assert source.joinpath("sentinel.txt").read_text(encoding="utf-8") == "keep"


def test_cleanup_failure_marks_isolated_execution_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    temporary = tmp_path / "gavin-task-verify-fixture"
    monkeypatch.setattr(isolated_verification, "project_root", lambda: project)
    monkeypatch.setattr(
        isolated_verification,
        "isolation_config",
        lambda: {"mode": "git-worktree", "reuse_paths": []},
    )
    monkeypatch.setattr(
        isolated_verification.tempfile,
        "mkdtemp",
        lambda **_: str(temporary.mkdir() or temporary),
    )

    def run_git(*args: str) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("worktree", "add"):
            Path(args[-2]).mkdir()
            return _completed(*args)
        if args[:2] == ("worktree", "remove"):
            return subprocess.CompletedProcess(args, 1, "", "cannot remove")
        return _completed(*args)

    monkeypatch.setattr(isolated_verification, "_run_git", run_git)
    monkeypatch.setattr(isolated_verification, "run_gates", lambda *_args, **_kwargs: [])

    results, context = isolated_verification.run_in_worktree({}, "abc123")

    assert results[-1]["name"] == "isolated-worktree-cleanup"
    assert results[-1]["status"] == "failed"
    assert context["cleanup_status"] == "failed"


def test_cleanup_removes_untracked_artifacts_left_after_git_worktree_remove(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    temporary = tmp_path / "gavin-task-verify-fixture"
    monkeypatch.setattr(isolated_verification, "project_root", lambda: project)
    monkeypatch.setattr(
        isolated_verification,
        "isolation_config",
        lambda: {"mode": "git-worktree", "reuse_paths": []},
    )
    monkeypatch.setattr(
        isolated_verification.tempfile,
        "mkdtemp",
        lambda **_: str(temporary.mkdir() or temporary),
    )

    def run_git(*args: str) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("worktree", "add"):
            worktree = Path(args[-2])
            worktree.mkdir()
            worktree.joinpath(".output").mkdir()
        return _completed(*args)

    monkeypatch.setattr(isolated_verification, "_run_git", run_git)
    monkeypatch.setattr(isolated_verification, "run_gates", lambda *_args, **_kwargs: [])

    results, context = isolated_verification.run_in_worktree({}, "abc123")

    assert results[-1]["name"] == "isolated-worktree"
    assert context["cleanup_status"] == "passed"
    assert not temporary.exists()
