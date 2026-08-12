from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.tools import telemetry


def _event(kind: str, status: str, duration: float, *, stage: str | None = None) -> dict[str, object]:
    value: dict[str, object] = {"status": status, "duration_ms": duration}
    if stage:
        value["stage"] = stage
    return {
        "schema_version": 1,
        "observed_at": "2026-08-12T00:00:00+00:00",
        "kind": kind,
        "task_id": None,
        "value": value,
        "source": "fixture",
    }


def test_append_event_writes_one_valid_jsonl_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(telemetry, "local_directory", lambda: tmp_path)

    path = telemetry.append_event(
        "fixture.run",
        {"status": "passed", "duration_ms": 1},
        source="test",
        stream="fixture",
        observed_at="2026-08-12T00:00:00+00:00",
    )

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert telemetry.validate_event(json.loads(lines[0]))["kind"] == "fixture.run"


def test_summary_uses_nearest_rank_and_stable_groups() -> None:
    events = [
        _event("release.stage", "passed", 10, stage="api-tests"),
        _event("release.stage", "passed", 20, stage="api-tests"),
        _event("release.stage", "failed", 30, stage="web-quality"),
        _event("release.stage", "skipped", 40, stage="change-coverage"),
        _event("release.run", "failed", 100),
    ]

    summary = telemetry.summarize(events, source_files=2)

    assert summary["events"] == 5
    assert summary["source_files"] == 2
    assert summary["status"] == {"passed": 2, "failed": 2, "skipped": 1, "other": 0}
    assert summary["duration_ms"] == {"count": 5, "p50": 30.0, "p95": 100.0, "max": 100.0}
    assert summary["by_stage"]["api-tests"]["events"] == 2
    assert summary["by_stage"]["web-quality"]["status"]["failed"] == 1


def test_empty_directory_has_valid_empty_summary(tmp_path: Path) -> None:
    events, files = telemetry.load_events(tmp_path)

    summary = telemetry.summarize(events, files)

    assert summary["events"] == 0
    assert summary["duration_ms"] == {"count": 0, "p50": None, "p95": None, "max": None}


def test_malformed_jsonl_reports_file_and_line(tmp_path: Path) -> None:
    (tmp_path / "bad.jsonl").write_text("{}\nnot-json\n", encoding="utf-8")

    with pytest.raises(telemetry.TelemetryError, match=r"bad\.jsonl:1"):
        telemetry.load_events(tmp_path)


def test_task_observation_is_bounded_and_omits_raw_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(telemetry, "local_directory", lambda: tmp_path)
    checks = [
        {
            "name": "api-tests",
            "status": "failed",
            "duration_ms": 12,
            "command": "secret command",
            "details": ["raw output"],
            "result": {"failure": {"kind": "nonzero-exit", "summary": "private"}},
        }
    ]

    path = telemetry.observe_task_verification(
        "20260812-fixture",
        "focused",
        {"cleanup_status": "passed"},
        checks,
        "a" * 40,
    )

    raw = path.read_text(encoding="utf-8")
    event = json.loads(raw)
    assert event["value"]["failure_kinds"] == ["nonzero-exit"]
    assert "secret command" not in raw
    assert "raw output" not in raw
    assert "private" not in raw


def test_task_observation_failure_is_non_blocking(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        telemetry,
        "observe_task_verification",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk unavailable")),
    )

    error = telemetry.observe_task_verification_safely(
        "20260812-fixture", "focused", {}, [], "a" * 40
    )

    assert error == "disk unavailable"


def test_release_runner_records_stage_and_terminal_events() -> None:
    root = Path(__file__).resolve().parents[3]
    runner = (root / "scripts" / "run-release-check.mjs").read_text(encoding="utf-8")

    assert "observe('release.stage'" in runner
    assert "observe('release.run'" in runner
    assert "finishRelease('failed'" in runner
    assert "finishRelease('passed', 0)" in runner
    assert "appendFileSync" in runner
