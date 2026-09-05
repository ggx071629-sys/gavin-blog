from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

events = importlib.import_module("harness.tools.events")
harness_cli = importlib.import_module("harness.tools.harness")
summarizer = importlib.import_module("harness.tools.summarizer")

TASK_ID = "20260811-example-close"


@pytest.fixture(autouse=True)
def _isolate_close_attestation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(harness_cli.verification_resume, "authenticate", lambda *_: {})
    monkeypatch.setattr(harness_cli.verification_resume, "authenticated_digest", lambda *_: "a" * 64)
    monkeypatch.setattr(harness_cli.run_store, "store_root", lambda: tmp_path / "local-runs")
    monkeypatch.setattr(harness_cli, "_evidence_sha256", lambda _task: "a" * 64)


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
        "verification_profile: focused\n"
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
            "allowed_events": [
                "spec.completed",
                "workflow.friction_confirmed",
                "verification.repeated_failure",
            ],
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
    assert event.read_bytes().endswith(b"\n")
    assert b"\r\n" not in event.read_bytes()
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


def test_repeated_failure_event_requires_and_persists_confirmed_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "harness"
    _isolate_events(monkeypatch, root)
    runs = [
        {
            "run_id": "run-one",
            "observed_at": "2026-08-14T00:00:00+00:00",
            "source_commit": "a" * 40,
            "failure_kinds": ["nonzero-exit"],
            "isolation_cleanup": "passed",
        },
        {
            "run_id": "run-two",
            "observed_at": "2026-08-14T00:01:00+00:00",
            "source_commit": "b" * 40,
            "failure_kinds": ["timeout"],
            "isolation_cleanup": "passed",
        },
    ]

    event, proposal = events.emit_event(
        "verification.repeated_failure",
        TASK_ID,
        "Two comparable failures were confirmed.",
        "manual",
        evidence_runs=runs,
    )

    payload = json.loads(event.read_text(encoding="utf-8"))
    assert payload["evidence_runs"] == runs
    assert proposal is not None
    proposal_text = proposal.read_text(encoding="utf-8")
    assert "## Confirmed failure runs" in proposal_text
    assert "run-one" in proposal_text and "run-two" in proposal_text


def test_repeated_failure_event_rejects_unconfirmed_or_non_manual_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "harness"
    _isolate_events(monkeypatch, root)

    with pytest.raises(ValueError, match="requires two confirmed"):
        events.emit_event(
            "verification.repeated_failure", TASK_ID, "Unconfirmed.", "manual"
        )
    with pytest.raises(ValueError, match="must use manual"):
        events.emit_event(
            "verification.repeated_failure",
            TASK_ID,
            "Wrong source.",
            "lifecycle",
            evidence_runs=[{}, {}],
        )
    with pytest.raises(ValueError, match="only valid"):
        events.emit_event(
            "workflow.friction_confirmed",
            TASK_ID,
            "Wrong event.",
            "manual",
            evidence_runs=[{}, {}],
        )
    with pytest.raises(ValueError, match="fields are invalid"):
        events.emit_event(
            "verification.repeated_failure",
            TASK_ID,
            "Malformed runs.",
            "manual",
            evidence_runs=[{}, {}],
        )
    assert not (root / "evolution" / "events").exists()
    assert not (root / "evolution" / "proposals").exists()


def test_close_requests_an_event_without_a_proposal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = tmp_path / "archive.md"
    source = tmp_path / "source.md"
    source.write_text("source", encoding="utf-8")
    evidence = tmp_path / "evidence.json"
    event = tmp_path / "event.json"
    results = [{"name": "fixture", "status": "passed", "duration_ms": 0, "details": []}]
    requested: list[bool] = []

    monkeypatch.setattr(harness_cli.summarizer, "validate_task_id", lambda _: None)
    monkeypatch.setattr(harness_cli.summarizer, "active_spec", lambda _: source)
    monkeypatch.setattr(harness_cli.summarizer, "archive_spec", lambda _: archive)

    def close_spec(_: str, **_kwargs: object) -> tuple[Path, str]:
        archive.write_text("archive", encoding="utf-8")
        return archive, "source"

    monkeypatch.setattr(harness_cli.summarizer, "close_spec", close_spec)
    monkeypatch.setattr(harness_cli.summarizer, "restore_spec", lambda *_: None)
    monkeypatch.setattr(harness_cli.validator, "run_close_checks", lambda: results)
    monkeypatch.setattr(harness_cli.validator, "passed", lambda _: True)
    monkeypatch.setattr(harness_cli.validator, "evidence_path", lambda _: evidence)
    monkeypatch.setattr(
        harness_cli.product_verification,
        "validate_evidence",
        lambda *_a, **_k: [],
    )
    monkeypatch.setattr(harness_cli.indexer, "write_indexes", list)

    def record_event(
        *_: object,
        create_proposal: bool,
        evidence_sha256: str,
    ) -> tuple[Path, None]:
        requested.append(create_proposal)
        assert evidence_sha256 == "a" * 64
        event.write_text("{}", encoding="utf-8")
        return event, None

    monkeypatch.setattr(harness_cli.events, "emit_event", record_event)
    monkeypatch.setattr(harness_cli.events, "event_path", lambda *_: event)

    result = harness_cli.command_close(argparse.Namespace(task_id=TASK_ID))

    assert result == 0
    assert requested == [False]
    assert event.is_file()


def test_close_rejects_invalid_task_evidence_before_running_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checks_called = False
    monkeypatch.setattr(harness_cli.summarizer, "validate_task_id", lambda _: None)
    monkeypatch.setattr(harness_cli.lifecycle, "task_status", lambda _: "active")
    monkeypatch.setattr(harness_cli.validator, "evidence_path", lambda _: Path("missing.json"))
    monkeypatch.setattr(
        harness_cli.product_verification,
        "validate_evidence",
        lambda *_a, **_k: ["task evidence missing"],
    )

    def run_checks() -> list[dict[str, object]]:
        nonlocal checks_called
        checks_called = True
        return []

    monkeypatch.setattr(harness_cli.validator, "run_close_checks", run_checks)

    assert harness_cli.command_close(argparse.Namespace(task_id=TASK_ID)) == 1
    assert checks_called is False


def test_m08_evidence_01_close_requires_authenticated_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence_validated = False
    monkeypatch.setattr(harness_cli.summarizer, "validate_task_id", lambda _: None)
    monkeypatch.setattr(harness_cli.lifecycle, "task_status", lambda _: "active")
    def reject(*_):
        raise ValueError("missing authenticated receipt")
    monkeypatch.setattr(harness_cli.verification_resume, "authenticate", reject)

    def validate(*_args: object) -> list[str]:
        nonlocal evidence_validated
        evidence_validated = True
        return []

    monkeypatch.setattr(harness_cli.product_verification, "validate_evidence", validate)

    assert harness_cli.command_close(argparse.Namespace(task_id=TASK_ID)) == 1
    assert evidence_validated is False


def test_close_all_skips_frozen_and_preflights_every_active_spec(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    active = tmp_path / "20260812-active-one.md"
    invalid = tmp_path / "20260812-active-two.md"
    frozen = tmp_path / "20260812-frozen-one.md"
    close_calls: list[str] = []
    checks_called = False
    monkeypatch.setattr(harness_cli.summarizer, "active_specs", lambda: [active, invalid, frozen])
    monkeypatch.setattr(harness_cli.summarizer, "validate_task_id", lambda _: None)
    monkeypatch.setattr(
        harness_cli.lifecycle,
        "task_status",
        lambda task: "frozen" if task == frozen.stem else "active",
    )
    monkeypatch.setattr(harness_cli.validator, "evidence_path", lambda task: tmp_path / f"{task}.json")
    monkeypatch.setattr(
        harness_cli.product_verification,
        "validate_evidence",
        lambda task, _, **_k: ["stale evidence"] if task == invalid.stem else [],
    )
    monkeypatch.setattr(
        harness_cli.summarizer,
        "close_spec",
        lambda task: close_calls.append(task),
    )

    def run_checks() -> list[dict[str, object]]:
        nonlocal checks_called
        checks_called = True
        return []

    monkeypatch.setattr(harness_cli.validator, "run_close_checks", run_checks)

    assert harness_cli.command_close_all(argparse.Namespace()) == 1
    assert close_calls == []
    assert checks_called is False
    assert f"[SKIPPED] {frozen.stem} is frozen" in capsys.readouterr().out


def test_close_all_rolls_back_every_task_when_post_check_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tasks = ["20260812-active-one", "20260812-active-two"]
    paths = [tmp_path / f"{task}.md" for task in tasks]
    for path in paths:
        path.write_text(f"source:{path.stem}", encoding="utf-8")
    restored: list[str] = []
    index_calls = 0
    check_runs = 0
    passed = [{"name": "fixture", "status": "passed", "duration_ms": 0}]
    failed = [{"name": "fixture", "status": "failed", "duration_ms": 0}]
    monkeypatch.setattr(harness_cli.summarizer, "active_specs", lambda: paths)
    monkeypatch.setattr(
        harness_cli.summarizer,
        "active_spec",
        lambda task: tmp_path / f"{task}.md",
    )
    monkeypatch.setattr(
        harness_cli.summarizer,
        "archive_spec",
        lambda task: tmp_path / f"{task}.archive.md",
    )
    monkeypatch.setattr(harness_cli.summarizer, "validate_task_id", lambda _: None)
    monkeypatch.setattr(harness_cli.lifecycle, "task_status", lambda _: "active")
    monkeypatch.setattr(harness_cli.validator, "evidence_path", lambda task: tmp_path / f"{task}.json")
    monkeypatch.setattr(harness_cli.product_verification, "validate_evidence", lambda *_a, **_k: [])

    def run_checks() -> list[dict[str, object]]:
        nonlocal check_runs
        check_runs += 1
        return passed if check_runs == 1 else failed

    monkeypatch.setattr(harness_cli.validator, "run_close_checks", run_checks)

    def close_spec(task: str, **_kwargs: object) -> tuple[Path, str]:
        archive = tmp_path / f"{task}.archive.md"
        archive.write_text("archive", encoding="utf-8")
        return archive, f"source:{task}"

    monkeypatch.setattr(harness_cli.summarizer, "close_spec", close_spec)

    def restore_spec(task: str, source: str, archive: Path) -> None:
        assert source == f"source:{task}"
        archive.unlink()
        restored.append(task)

    monkeypatch.setattr(harness_cli.summarizer, "restore_spec", restore_spec)

    def emit_event(*args: object, **_: object) -> tuple[Path, None]:
        task = str(args[1])
        event = tmp_path / f"{task}.event.json"
        event.write_text("{}", encoding="utf-8")
        return event, None

    monkeypatch.setattr(harness_cli.events, "emit_event", emit_event)
    monkeypatch.setattr(
        harness_cli.events,
        "event_path",
        lambda _event, task: tmp_path / f"{task}.event.json",
    )

    def write_indexes() -> list[Path]:
        nonlocal index_calls
        index_calls += 1
        return []

    monkeypatch.setattr(harness_cli.indexer, "write_indexes", write_indexes)

    assert harness_cli.command_close_all(argparse.Namespace()) == 1
    assert restored == list(reversed(tasks))
    assert not list(tmp_path.glob("*.archive.md"))
    assert not list(tmp_path.glob("*.event.json"))
    assert index_calls == 2


def test_close_all_success_writes_every_task_and_indexes_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tasks = ["20260812-active-one", "20260812-active-two"]
    paths = [tmp_path / f"{task}.md" for task in tasks]
    for path in paths:
        path.write_text(f"source:{path.stem}", encoding="utf-8")
    index_calls = 0
    passed = [{"name": "fixture", "status": "passed", "duration_ms": 0}]
    monkeypatch.setattr(harness_cli.summarizer, "active_specs", lambda: paths)
    monkeypatch.setattr(
        harness_cli.summarizer,
        "active_spec",
        lambda task: tmp_path / f"{task}.md",
    )
    monkeypatch.setattr(
        harness_cli.summarizer,
        "archive_spec",
        lambda task: tmp_path / f"{task}.archive.md",
    )
    monkeypatch.setattr(harness_cli.summarizer, "validate_task_id", lambda _: None)
    monkeypatch.setattr(harness_cli.lifecycle, "task_status", lambda _: "active")
    monkeypatch.setattr(harness_cli.validator, "evidence_path", lambda task: tmp_path / f"{task}.json")
    monkeypatch.setattr(harness_cli.product_verification, "validate_evidence", lambda *_a, **_k: [])
    monkeypatch.setattr(harness_cli.validator, "run_close_checks", lambda: passed)

    def close_spec(task: str, **_kwargs: object) -> tuple[Path, str]:
        archive = tmp_path / f"{task}.archive.md"
        archive.write_text("archive", encoding="utf-8")
        return archive, f"source:{task}"

    monkeypatch.setattr(harness_cli.summarizer, "close_spec", close_spec)

    def emit_event(*args: object, **_: object) -> tuple[Path, None]:
        event = tmp_path / f"{args[1]}.event.json"
        event.write_text("{}", encoding="utf-8")
        return event, None

    monkeypatch.setattr(harness_cli.events, "emit_event", emit_event)
    monkeypatch.setattr(
        harness_cli.events,
        "event_path",
        lambda _event, task: tmp_path / f"{task}.event.json",
    )

    def write_indexes() -> list[Path]:
        nonlocal index_calls
        index_calls += 1
        return []

    monkeypatch.setattr(harness_cli.indexer, "write_indexes", write_indexes)

    assert harness_cli.command_close_all(argparse.Namespace()) == 0
    assert len(list(tmp_path.glob("*.archive.md"))) == 2
    assert len(list(tmp_path.glob("*.event.json"))) == 2
    assert index_calls == 1


def test_close_cleans_partial_event_when_emission_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / f"{TASK_ID}.md"
    archive = tmp_path / f"{TASK_ID}.archive.md"
    event = tmp_path / f"{TASK_ID}.event.json"
    source.write_text("source", encoding="utf-8")
    passed = [{"name": "fixture", "status": "passed", "duration_ms": 0}]
    monkeypatch.setattr(harness_cli.summarizer, "validate_task_id", lambda _: None)
    monkeypatch.setattr(harness_cli.lifecycle, "task_status", lambda _: "active")
    monkeypatch.setattr(harness_cli.validator, "evidence_path", lambda _: tmp_path / "evidence.json")
    monkeypatch.setattr(harness_cli.product_verification, "validate_evidence", lambda *_a, **_k: [])
    monkeypatch.setattr(harness_cli.summarizer, "active_spec", lambda _: source)
    monkeypatch.setattr(harness_cli.summarizer, "archive_spec", lambda _: archive)
    monkeypatch.setattr(harness_cli.events, "event_path", lambda *_: event)
    monkeypatch.setattr(harness_cli.validator, "run_close_checks", lambda: passed)
    monkeypatch.setattr(harness_cli.indexer, "write_indexes", list)

    def close_spec(_: str, **_kwargs: object) -> tuple[Path, str]:
        archive.write_text("partial archive", encoding="utf-8")
        source.unlink()
        return archive, "source"

    monkeypatch.setattr(harness_cli.summarizer, "close_spec", close_spec)

    def emit_event(*_: object, **__: object) -> tuple[Path, None]:
        event.write_text("partial event", encoding="utf-8")
        raise OSError("event write failed")

    monkeypatch.setattr(harness_cli.events, "emit_event", emit_event)

    assert harness_cli.command_close(argparse.Namespace(task_id=TASK_ID)) == 1
    assert source.read_text(encoding="utf-8") == "source"
    assert not archive.exists()
    assert not event.exists()


def test_close_all_dry_run_performs_full_preflight_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = "20260812-active-one"
    source = tmp_path / f"{task}.md"
    archive = tmp_path / f"{task}.archive.md"
    event = tmp_path / f"{task}.event.json"
    source.write_text("source", encoding="utf-8")
    passed = [{"name": "fixture", "status": "passed", "duration_ms": 0}]
    monkeypatch.setattr(harness_cli.summarizer, "active_specs", lambda: [source])
    monkeypatch.setattr(harness_cli.summarizer, "validate_task_id", lambda _: None)
    monkeypatch.setattr(harness_cli.summarizer, "active_spec", lambda _: source)
    monkeypatch.setattr(harness_cli.summarizer, "archive_spec", lambda _: archive)
    monkeypatch.setattr(harness_cli.lifecycle, "task_status", lambda _: "active")
    monkeypatch.setattr(harness_cli.validator, "evidence_path", lambda _: tmp_path / "evidence.json")
    monkeypatch.setattr(harness_cli.product_verification, "validate_evidence", lambda *_a, **_k: [])
    monkeypatch.setattr(harness_cli.events, "event_path", lambda *_: event)
    monkeypatch.setattr(harness_cli.validator, "run_close_checks", lambda: passed)

    def forbidden(*_: object, **__: object) -> None:
        raise AssertionError("dry-run must not write close artifacts")

    monkeypatch.setattr(harness_cli.summarizer, "close_spec", forbidden)
    monkeypatch.setattr(harness_cli.events, "emit_event", forbidden)
    monkeypatch.setattr(harness_cli.indexer, "write_indexes", forbidden)

    assert harness_cli.command_close_all(argparse.Namespace(dry_run=True)) == 0
    assert source.read_text(encoding="utf-8") == "source"
    assert not archive.exists()
    assert not event.exists()


def test_status_json_is_read_only_and_missing_task_returns_one(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    record = {
        "task_id": TASK_ID,
        "state": "missing",
        "verification_profile": None,
        "evidence": "missing",
        "blockers": ["not found"],
    }
    monkeypatch.setattr(harness_cli.task_reporting, "task_record", lambda _: record)

    result = harness_cli.command_status(
        argparse.Namespace(task_id=TASK_ID, json=True)
    )

    assert result == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"schema_version": 1, "tasks": [record]}
