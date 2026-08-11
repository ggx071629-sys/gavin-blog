from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from tools import events, summarizer
from tools import harness as harness_cli

TASK_ID = "20260811-example-close"


def _spec_config() -> dict[str, object]:
    return {
        "specs": {
            "task_id_pattern": r"\d{8}-[a-z0-9-]+",
            "active": "specs/active",
            "archive": "specs/archive",
            "require_git_history_before_close": False,
        }
    }


def _write_active_spec(root: Path, body: str) -> Path:
    path = root / "specs" / "active" / f"{TASK_ID}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"id: spec-{TASK_ID}\n"
        "level: L1\n"
        "summary: Lifecycle fixture\n"
        "load_when:\n"
        f"  - task:{TASK_ID}\n"
        f"task_id: {TASK_ID}\n"
        "status: active\n"
        "---\n\n"
        f"{body}",
        encoding="utf-8",
    )
    return path


def _isolate_summarizer(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    config = _spec_config()
    monkeypatch.setattr(summarizer, "harness_root", lambda: root)
    monkeypatch.setattr(summarizer, "load_config", lambda: config)


@pytest.mark.parametrize("heading", ["#", "##"])
def test_close_preserves_h1_and_h2_required_sections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    heading: str,
) -> None:
    root = tmp_path / "harness"
    nested_heading = "##" if heading == "#" else "###"
    source = _write_active_spec(
        root,
        f"{heading} Context\n\nFixture context.\n\n"
        f"{heading} Goal\n\nPreserve this goal.\n\n"
        f"{nested_heading} Goal detail\n\nPreserve this nested detail.\n\n"
        f"{heading} Acceptance criteria\n\n- Preserve this criterion.\n\n"
        f"{heading} Verification plan\n\nRun focused tests.\n",
    )
    _isolate_summarizer(monkeypatch, root)

    archive, _ = summarizer.close_spec(TASK_ID)

    content = archive.read_text(encoding="utf-8")
    assert "## Goal\n\nPreserve this goal." in content
    assert "Preserve this nested detail." in content
    assert "## Acceptance criteria\n\n- Preserve this criterion." in content
    assert not source.exists()


@pytest.mark.parametrize(
    "body",
    [
        "# Context\n\nNo required sections.\n",
        "# Goal\n\n# Acceptance criteria\n\nA criterion.\n",
        "### Goal\n\nToo deeply nested.\n\n### Acceptance criteria\n\n- Also nested.\n",
    ],
)
def test_close_rejects_missing_empty_or_nested_required_sections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    body: str,
) -> None:
    root = tmp_path / "harness"
    source = _write_active_spec(root, body)
    _isolate_summarizer(monkeypatch, root)

    with pytest.raises(ValueError, match="required non-empty section"):
        summarizer.close_spec(TASK_ID)

    assert source.exists()
    assert not (root / "specs" / "archive" / f"{TASK_ID}.md").exists()


def _isolate_events(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    config = {
        "evolution": {
            "allowed_events": ["spec.completed", "workflow.friction_confirmed"],
            "events": "evolution/events",
            "proposals": "evolution/proposals",
        }
    }
    monkeypatch.setattr(events, "harness_root", lambda: root)
    monkeypatch.setattr(events, "load_config", lambda: config)
    monkeypatch.setattr(events, "validate_task_id", lambda _: None)


def test_lifecycle_event_can_be_recorded_without_a_proposal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "harness"
    _isolate_events(monkeypatch, root)

    event, proposal = events.emit_event(
        "spec.completed",
        TASK_ID,
        "The spec closed.",
        "lifecycle",
        create_proposal=False,
    )

    assert event.is_file()
    assert proposal is None
    assert not (root / "evolution" / "proposals" / f"{TASK_ID}--spec-completed.md").exists()


def test_explicit_event_still_creates_a_proposal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "harness"
    _isolate_events(monkeypatch, root)

    event, proposal = events.emit_event(
        "workflow.friction_confirmed",
        TASK_ID,
        "Concrete friction with evidence.",
        "manual",
    )

    assert event.is_file()
    assert proposal is not None and proposal.is_file()
    assert "Concrete friction with evidence." in proposal.read_text(encoding="utf-8")


def test_close_requests_an_event_without_a_proposal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = tmp_path / "archive.md"
    archive.write_text("archive", encoding="utf-8")
    evidence = tmp_path / "evidence.json"
    event = tmp_path / "event.json"
    results = [{"name": "fixture", "status": "passed", "duration_ms": 0, "details": []}]
    requested: list[bool] = []

    monkeypatch.setattr(harness_cli.summarizer, "validate_task_id", lambda _: None)
    monkeypatch.setattr(harness_cli.summarizer, "close_spec", lambda _: (archive, "source"))
    monkeypatch.setattr(harness_cli.summarizer, "restore_spec", lambda *_: None)
    monkeypatch.setattr(harness_cli.validator, "run_checks", lambda: results)
    monkeypatch.setattr(harness_cli.validator, "passed", lambda _: True)
    monkeypatch.setattr(harness_cli.validator, "evidence_path", lambda _: evidence)
    monkeypatch.setattr(
        harness_cli.validator,
        "write_evidence",
        lambda *_: evidence,
    )
    monkeypatch.setattr(harness_cli.indexer, "write_indexes", list)

    def record_event(*_: object, create_proposal: bool) -> tuple[Path, None]:
        requested.append(create_proposal)
        event.write_text("{}", encoding="utf-8")
        return event, None

    monkeypatch.setattr(harness_cli.events, "emit_event", record_event)

    result = harness_cli.command_close(argparse.Namespace(task_id=TASK_ID))

    assert result == 0
    assert requested == [False]
    assert event.is_file()
