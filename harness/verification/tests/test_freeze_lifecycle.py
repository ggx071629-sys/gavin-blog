from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
HARNESS_ROOT = PROJECT_ROOT / "harness"
for candidate in (PROJECT_ROOT, HARNESS_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

harness_cli = importlib.import_module("harness.tools.harness")
indexer = importlib.import_module("harness.tools.indexer")
lifecycle = importlib.import_module("harness.tools.lifecycle")
metadata = importlib.import_module("harness.tools.metadata")
summarizer = importlib.import_module("harness.tools.summarizer")

TASK_ID = "20260811-example-freeze"
BODY = """# Context

Fixture context.

# Goal

Preserve this goal.

# Non-goals

- Preserve this boundary.

# Acceptance criteria

- Preserve this criterion.

# Risks

- Fixture risk.

# Verification plan

Run focused tests.
"""


def _config() -> dict[str, object]:
    return {
        "specs": {
            "task_id_pattern": r"\d{8}-[a-z0-9-]+",
            "active": "specs/active",
            "archive": "specs/archive",
            "require_git_history_before_close": False,
        }
    }


def _write_spec(root: Path, *, status: str = "active", extra: str = "") -> Path:
    path = root / "specs" / "active" / f"{TASK_ID}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"id: spec-{TASK_ID}\n"
        "level: L1\n"
        "summary: Freeze fixture\n"
        "load_when:\n"
        f"  - task:{TASK_ID}\n"
        f"task_id: {TASK_ID}\n"
        f"status: {status}\n"
        "verification_profile: focused\n"
        f"{extra}"
        "---\n\n"
        f"{BODY}",
        encoding="utf-8",
    )
    return path


def _isolate(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    config = _config()
    monkeypatch.setattr(lifecycle, "harness_root", lambda: root)
    monkeypatch.setattr(lifecycle, "load_config", lambda: config)
    monkeypatch.setattr(summarizer, "harness_root", lambda: root)
    monkeypatch.setattr(summarizer, "load_config", lambda: config)


def test_freeze_and_resume_append_auditable_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "harness"
    path = _write_spec(root)
    _isolate(monkeypatch, root)

    lifecycle.freeze_spec(
        TASK_ID,
        "Waiting for external E2E.",
        at="2026-08-11T01:02:03+00:00",
    )

    frozen, _ = metadata.parse_front_matter(path)
    assert frozen["status"] == "frozen"
    assert frozen["frozen_at"] == "2026-08-11T01:02:03+00:00"
    assert frozen["freeze_reason"] == "Waiting for external E2E."
    assert len(frozen["frozen_scope_sha256"]) == 64
    history = lifecycle.parse_state_history(frozen)
    assert history == [
        {
            "action": "freeze",
            "at": "2026-08-11T01:02:03+00:00",
            "reason": "Waiting for external E2E.",
            "scope_sha256": frozen["frozen_scope_sha256"],
        }
    ]

    lifecycle.resume_spec(
        TASK_ID,
        "External E2E is available.",
        at="2026-08-11T02:03:04+00:00",
    )

    active, _ = metadata.parse_front_matter(path)
    assert active["status"] == "active"
    assert "frozen_at" not in active
    assert "freeze_reason" not in active
    assert "frozen_scope_sha256" not in active
    history = lifecycle.parse_state_history(active)
    assert [event["action"] for event in history] == ["freeze", "resume"]
    assert history[-1]["reason"] == "External E2E is available."


def test_frozen_contract_digest_allows_notes_but_rejects_scope_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "harness"
    path = _write_spec(root)
    _isolate(monkeypatch, root)
    lifecycle.freeze_spec(TASK_ID, "Blocked.", at="2026-08-11T01:00:00+00:00")

    path.write_text(
        path.read_text(encoding="utf-8") + "\n# Freeze notes\n\nDependency contacted.\n",
        encoding="utf-8",
    )
    assert lifecycle.validate_active_spec(path) == []

    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "Preserve this criterion.", "A rewritten criterion."
        ),
        encoding="utf-8",
    )
    assert any("core contract digest" in error for error in lifecycle.validate_active_spec(path))
    with pytest.raises(lifecycle.LifecycleError, match="core contract digest"):
        lifecycle.resume_spec(TASK_ID, "Resume anyway.")


def test_illegal_or_ambiguous_transitions_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "harness"
    _write_spec(root)
    _isolate(monkeypatch, root)

    with pytest.raises(lifecycle.LifecycleError, match="reason must be non-empty"):
        lifecycle.freeze_spec(TASK_ID, "   ")
    with pytest.raises(lifecycle.LifecycleError, match="requires status frozen"):
        lifecycle.resume_spec(TASK_ID, "Not frozen.")
    with pytest.raises(lifecycle.LifecycleError, match="must use UTC"):
        lifecycle.freeze_spec(
            TASK_ID,
            "Wrong timezone.",
            at="2026-08-11T09:00:00+08:00",
        )

    lifecycle.freeze_spec(TASK_ID, "Blocked.")
    with pytest.raises(lifecycle.LifecycleError, match="requires status active"):
        lifecycle.freeze_spec(TASK_ID, "Duplicate.")


def test_legacy_migration_preserves_supplied_date_and_marks_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "harness"
    path = _write_spec(
        root,
        status="frozen",
        extra="frozen_at: 2026-08-07\nfreeze_reason: Historical blocker.\n",
    )
    _isolate(monkeypatch, root)

    lifecycle.migrate_legacy_frozen_spec(TASK_ID)

    data, _ = metadata.parse_front_matter(path)
    event = lifecycle.parse_state_history(data)[0]
    assert event["at"] == "2026-08-07"
    assert event["reason"] == "Historical blocker."
    assert event["baseline"] == "migration"
    assert lifecycle.validate_active_spec(path) == []


def test_task_verify_reports_frozen_and_cannot_write_success_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = [{"name": "fixture", "status": "passed", "passed": True, "duration_ms": 0}]
    written: list[list[dict[str, object]]] = []
    monkeypatch.setattr(harness_cli.summarizer, "validate_task_id", lambda _: None)
    monkeypatch.setattr(harness_cli.validator, "run_checks", lambda: list(results))
    monkeypatch.setattr(harness_cli.lifecycle, "task_status", lambda _: "frozen")
    monkeypatch.setattr(
        harness_cli.validator,
        "write_task_evidence",
        lambda _task, _command, _criteria, _mappings, _profile, _fingerprints, _documentation, _execution, checks, _cases: written.append(checks)
        or Path("evidence.json"),
    )

    result = harness_cli.command_verify(argparse.Namespace(task_id=TASK_ID))

    assert result == 1
    assert written[0][-1]["name"] == "task-lifecycle"
    assert written[0][-1]["status"] == "failed"


def test_close_rejects_frozen_before_running_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checks_called = False
    monkeypatch.setattr(harness_cli.summarizer, "validate_task_id", lambda _: None)
    monkeypatch.setattr(harness_cli.lifecycle, "task_status", lambda _: "frozen")

    def run_checks() -> list[dict[str, object]]:
        nonlocal checks_called
        checks_called = True
        return []

    monkeypatch.setattr(harness_cli.validator, "run_checks", run_checks)

    assert harness_cli.command_close(argparse.Namespace(task_id=TASK_ID)) == 1
    assert checks_called is False


def test_transition_rolls_back_when_index_generation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "harness"
    path = _write_spec(root)
    original = path.read_bytes()
    _isolate(monkeypatch, root)
    monkeypatch.setattr(harness_cli.summarizer, "validate_task_id", lambda _: None)
    monkeypatch.setattr(harness_cli.summarizer, "active_spec", lambda _: path)
    attempts = 0

    def write_indexes() -> list[Path]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("fixture index failure")
        return []

    monkeypatch.setattr(harness_cli.indexer, "write_indexes", write_indexes)

    result = harness_cli.command_freeze(
        argparse.Namespace(task_id=TASK_ID, reason="Blocked.")
    )

    assert result == 1
    assert attempts == 2
    assert path.read_bytes() == original


def test_close_preserves_state_history_in_compressed_archive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "harness"
    _write_spec(root)
    _isolate(monkeypatch, root)
    lifecycle.freeze_spec(TASK_ID, "Blocked.", at="2026-08-11T01:00:00+00:00")
    lifecycle.resume_spec(TASK_ID, "Ready.", at="2026-08-11T02:00:00+00:00")

    archive, _ = summarizer.close_spec(TASK_ID)

    data, _ = metadata.parse_front_matter(archive)
    assert [event["action"] for event in lifecycle.parse_state_history(data)] == [
        "freeze",
        "resume",
    ]


def test_spec_index_separates_active_and_frozen_counts(tmp_path: Path) -> None:
    root = tmp_path / "specs"
    _write_spec(root.parent)
    second = root / "active" / "20260811-second-freeze.md"
    second.write_text(
        second.parent.joinpath(f"{TASK_ID}.md").read_text(encoding="utf-8")
        .replace(TASK_ID, "20260811-second-freeze")
        .replace("status: active", "status: frozen"),
        encoding="utf-8",
    )

    content = indexer.render_scope("Specification Index", root, include_status=True)

    assert "Open specifications: **1 active**, **1 frozen**." in content
    assert "| ID | Status | Level |" in content
    assert "| spec-20260811-second-freeze | frozen |" in content
