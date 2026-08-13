from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.tools import harness as harness_cli
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


def _health_config() -> dict[str, object]:
    return {
        "telemetry": {
            "health": {
                "min_samples": 3,
                "baseline_samples": 3,
                "recent_samples": 3,
                "consecutive_failures": 2,
                "duration_ratio": 1.5,
            }
        }
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


def test_health_distinguishes_no_data_and_insufficient_data() -> None:
    empty = telemetry.assess_health([], config=_health_config())
    sparse = telemetry.assess_health(
        [_event("task.verification", "passed", 10)],
        config=_health_config(),
    )

    assert empty["status"] == "no-data"
    assert sparse["status"] == "insufficient-data"
    assert sparse["series"]["task.verification"]["status"] == "insufficient-data"


def test_health_rejects_incomplete_or_non_positive_configuration() -> None:
    with pytest.raises(telemetry.TelemetryError, match="configuration is incomplete"):
        telemetry.assess_health([], config={})

    config = _health_config()
    config["telemetry"]["health"]["min_samples"] = 0  # type: ignore[index]
    with pytest.raises(telemetry.TelemetryError, match="positive integer"):
        telemetry.assess_health([], config=config)


def test_health_requires_minimum_samples_before_consecutive_failure_signal() -> None:
    too_few = [
        _event("task.verification", "failed", 10),
        _event("task.verification", "failed", 10),
    ]
    enough = [
        _event("task.verification", "passed", 10),
        _event("task.verification", "failed", 10),
        _event("task.verification", "failed", 10),
    ]

    assert telemetry.assess_health(too_few, config=_health_config())["status"] == "insufficient-data"
    result = telemetry.assess_health(enough, config=_health_config())
    assert result["status"] == "signal"
    assert result["series"]["task.verification"]["signals"] == [
        {"kind": "consecutive-failures", "observed": 2, "threshold": 2}
    ]


def test_health_compares_non_overlapping_duration_windows() -> None:
    samples = [10, 9, 11, 20, 21, 19]
    events = [
        _event("release.stage", "passed", duration, stage="api-tests")
        for duration in samples
    ]

    result = telemetry.assess_health(events, config=_health_config())
    series = result["series"]["release.stage:api-tests"]

    assert result["status"] == "signal"
    assert series["duration"]["baseline_median_ms"] == 10.0
    assert series["duration"]["recent_median_ms"] == 20.0
    assert series["duration"]["ratio"] == 2.0
    assert series["signals"][0]["kind"] == "duration-regression"


def test_health_does_not_guess_a_ratio_from_zero_baseline() -> None:
    events = [
        _event("release.run", "passed", duration)
        for duration in [0, 0, 0, 10, 10, 10]
    ]

    result = telemetry.assess_health(events, config=_health_config())
    duration = result["series"]["release.run"]["duration"]

    assert result["status"] == "stable"
    assert duration["zero_baseline"] is True
    assert duration["ratio"] is None


def test_health_sorts_events_by_observed_time_before_evaluating_failures() -> None:
    events = [
        _event("task.verification", "failed", 10),
        _event("task.verification", "failed", 10),
        _event("task.verification", "passed", 10),
    ]
    events[0]["observed_at"] = "2026-08-12T00:00:03+00:00"
    events[1]["observed_at"] = "2026-08-12T00:00:02+00:00"
    events[2]["observed_at"] = "2026-08-12T00:00:01+00:00"

    result = telemetry.assess_health(events, config=_health_config())

    assert result["status"] == "signal"
    assert result["series"]["task.verification"]["consecutive_failures"] == 2


def test_health_cli_returns_success_for_signal(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    events = [
        _event("task.verification", "passed", 10),
        _event("task.verification", "failed", 10),
        _event("task.verification", "failed", 10),
    ]
    monkeypatch.setattr(telemetry, "load_events", lambda: (events, 1))
    monkeypatch.setattr(telemetry, "load_config", _health_config)

    exit_code = harness_cli.command_telemetry_health(
        type("Args", (), {"json": True})()
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "signal"
