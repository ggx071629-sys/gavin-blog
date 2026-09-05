from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from harness.tools import harness as harness_cli
from harness.tools import lifecycle, product_verification

TASK_ID = "20260812-documentation-fixture"


def _metadata(*, impact: str = "required", targets: list[str] | None = None) -> dict[str, object]:
    return {
        "documentation_impact": impact,
        "documentation_targets": targets or [],
        "documentation_reason": "The durable operating contract changes.",
    }


def _run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _write_spec(path: Path, metadata: dict[str, object]) -> None:
    targets = metadata.get("documentation_targets", [])
    target_lines = ""
    if targets:
        target_lines = "documentation_targets:\n" + "".join(
            f"  - {target}\n" for target in targets
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"id: spec-{TASK_ID}\n"
        "level: L1\n"
        "summary: Documentation fixture\n"
        "load_when:\n"
        f"  - task:{TASK_ID}\n"
        f"task_id: {TASK_ID}\n"
        "status: active\n"
        "verification_profile: focused\n"
        f"documentation_impact: {metadata['documentation_impact']}\n"
        f"{target_lines}"
        f"documentation_reason: {metadata['documentation_reason']}\n"
        "state_history:\n"
        "---\n\n"
        "# Goal\n\nFixture.\n\n"
        "# Non-goals\n\nFixture.\n\n"
        "# Acceptance criteria\n\n- AC-1: Fixture.\n\n"
        "# Verification plan\n\n"
        "## Verification cases\n\n- AC-1 => M08-TRACE-01\n\n"
        "## Gates\n\n- harness-tests => AC-1\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        ({}, "documentation_impact"),
        (_metadata(impact="required", targets=[]), "must declare targets"),
        (_metadata(impact="none", targets=["README.md"]), "must not declare targets"),
        (_metadata(targets=["../README.md"]), "safe project-relative"),
        (_metadata(targets=["AGENTS.md"]), "forbidden"),
        (_metadata(targets=["harness/specs/active/task.md"]), "transient artifact"),
        (_metadata(targets=["harness/specs/INDEX.md"]), "generated index"),
        (_metadata(targets=["README.txt"]), "Markdown file"),
    ],
)
def test_documentation_contract_rejects_missing_ambiguous_or_unsafe_declarations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    metadata: dict[str, object],
    message: str,
) -> None:
    root = tmp_path / "project"
    harness = root / "harness"
    harness.mkdir(parents=True)
    monkeypatch.setattr(lifecycle, "project_root", lambda: root)
    monkeypatch.setattr(lifecycle, "harness_root", lambda: harness)
    monkeypatch.setattr(
        lifecycle,
        "load_config",
        lambda: {"evolution": {"forbidden_targets": ["../AGENTS.md"]}},
    )

    with pytest.raises(lifecycle.LifecycleError, match=message):
        lifecycle.documentation_contract(metadata)


def test_frozen_spec_is_exempt_from_documentation_declaration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "project"
    harness = root / "harness"
    path = harness / "specs" / "active" / f"{TASK_ID}.md"
    _write_spec(path, _metadata(impact="none"))
    config = {
        "specs": {
            "active": "specs/active",
            "task_id_pattern": r"\d{8}-[a-z0-9-]+",
            "require_documentation_impact": True,
        },
        "evolution": {"forbidden_targets": ["../AGENTS.md"]},
    }
    monkeypatch.setattr(lifecycle, "project_root", lambda: root)
    monkeypatch.setattr(lifecycle, "harness_root", lambda: harness)
    monkeypatch.setattr(lifecycle, "load_config", lambda: config)

    lifecycle.freeze_spec(TASK_ID, "Waiting for an external dependency.", at="2026-08-12T00:00:00+00:00")
    content = path.read_text(encoding="utf-8")
    content = content.replace("documentation_impact: none\n", "")
    content = content.replace(
        "documentation_reason: The durable operating contract changes.\n", ""
    )
    path.write_text(content, encoding="utf-8")

    assert lifecycle.validate_active_spec(path) == []


def test_required_documentation_must_change_after_spec_baseline_and_be_clean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "project"
    harness = root / "harness"
    root.mkdir()
    _run_git(root, "init", "-q")
    _run_git(root, "config", "user.name", "Harness Tests")
    _run_git(root, "config", "user.email", "harness@example.test")
    readme = root / "README.md"
    readme.write_text("# Baseline\n", encoding="utf-8")
    _run_git(root, "add", "README.md")
    _run_git(root, "commit", "-q", "-m", "initial docs")

    spec = harness / "specs" / "active" / f"{TASK_ID}.md"
    _write_spec(spec, _metadata(targets=["README.md"]))
    _run_git(root, "add", spec.relative_to(root).as_posix())
    _run_git(root, "commit", "-q", "-m", "add spec")

    config = {
        "verification": {"source_paths": ["harness/tools"]},
        "evolution": {"forbidden_targets": ["../AGENTS.md"]},
    }
    monkeypatch.setattr(product_verification, "project_root", lambda: root)
    monkeypatch.setattr(product_verification, "active_spec", lambda _: spec)
    monkeypatch.setattr(product_verification, "load_config", lambda: config)
    monkeypatch.setattr(lifecycle, "project_root", lambda: root)
    monkeypatch.setattr(lifecycle, "harness_root", lambda: harness)
    monkeypatch.setattr(lifecycle, "load_config", lambda: config)

    with pytest.raises(
        product_verification.ProductVerificationError,
        match="no committed change after",
    ):
        product_verification.documentation_report(TASK_ID)

    readme.write_text("# Updated after the spec\n", encoding="utf-8")
    _run_git(root, "add", "README.md")
    _run_git(root, "commit", "-q", "-m", "update docs")
    report = product_verification.documentation_report(TASK_ID)
    assert report["targets"] == ["README.md"]
    assert report["baseline_commit"]
    assert len(report["target_blobs"]["README.md"]) == 40

    readme.write_text("# Dirty drift\n", encoding="utf-8")
    with pytest.raises(
        product_verification.ProductVerificationError,
        match="uncommitted changes: README.md",
    ):
        product_verification.documentation_report(TASK_ID)


def test_task_verify_stops_before_product_gates_when_documentation_is_incomplete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from harness.tools import impact
    monkeypatch.setattr(impact, "enabled", lambda: False)
    written: list[list[dict[str, object]]] = []
    monkeypatch.setattr(harness_cli.summarizer, "validate_task_id", lambda _: None)
    monkeypatch.setattr(harness_cli.summarizer, "active_spec", lambda _: tmp_path / "spec.md")
    monkeypatch.setattr(harness_cli.summarizer, "ensure_spec_in_git_history", lambda _: None)
    monkeypatch.setattr(harness_cli.lifecycle, "task_status", lambda _: "active")
    monkeypatch.setattr(
        harness_cli.validator,
        "run_checks",
        lambda: [{"name": "fixture", "passed": True, "status": "passed", "duration_ms": 0}],
    )
    monkeypatch.setattr(
        product_verification,
        "verification_contract",
        lambda _: (["AC-1"], {"harness-tests": ["AC-1"]}),
    )
    monkeypatch.setattr(product_verification, "verification_profile", lambda _: "focused")
    monkeypatch.setattr(product_verification, "validate_configured_gates", lambda *_: None)
    monkeypatch.setattr(
        product_verification,
        "documentation_report",
        lambda _: (_ for _ in ()).throw(
            product_verification.ProductVerificationError("documentation target is stale")
        ),
    )
    monkeypatch.setattr(
        harness_cli.isolated_verification,
        "run_in_worktree",
        lambda *_: (_ for _ in ()).throw(AssertionError("product gates must not run")),
    )
    monkeypatch.setattr(
        harness_cli.validator,
        "write_task_evidence",
        lambda _task, _command, _criteria, _mappings, _profile, _fingerprints, _documentation, _execution, checks, _cases: written.append(checks)
        or tmp_path / "evidence.json",
    )
    monkeypatch.setattr(product_verification, "derived_task_state", lambda *_: "active")

    assert harness_cli.command_verify(argparse.Namespace(task_id=TASK_ID)) == 1
    assert written[0][-1]["name"] == "task-verification-precondition"
    assert written[0][-1]["details"] == ["documentation target is stale"]
