from __future__ import annotations

from harness.tools.harness import _configure_console_streams, _print_results
from harness.tools.result_reporting import (
    failure_details,
    failure_summary,
    parse_test_counts,
    summarize_checks,
    summarize_criteria,
)


def test_result_output_survives_a_legacy_console_encoding(monkeypatch) -> None:
    import io
    import sys

    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding="ascii", errors="strict")
    monkeypatch.setattr(sys, "stdout", stream)

    _configure_console_streams()
    _print_results(
        [
            {
                "name": "release",
                "status": "failed",
                "details": ["diagnostic: Playwright › failed"],
            }
        ]
    )
    stream.flush()

    assert b"Playwright \\u203a failed" in buffer.getvalue()


def test_test_count_parser_handles_project_frameworks_without_double_counting() -> None:
    output = """
================ 3 passed, 1 skipped, 2 warnings in 0.42s ================
 Test Files  2 passed (2)
      Tests  5 passed | 1 failed (6)
  ok 1 [chromium] individual test
  1 failed
  2 passed (3.1s)
"""

    assert parse_test_counts(output) == {"passed": 10, "failed": 2, "skipped": 1}


def test_failure_summary_removes_ansi_and_isolated_absolute_path() -> None:
    root = r"C:\Temp\gavin-task-verify-123\worktree"
    output = f"\x1b[31mError: failed at {root}\\tests\\fixture.py\x1b[0m"

    summary = failure_summary(output, "", redactions=[root])

    assert summary == "Error: failed at <isolated-worktree>\\tests\\fixture.py"
    assert "\x1b" not in summary


def test_failure_details_preserves_diagnostic_anchor_and_bounded_tail() -> None:
    output = "\n".join(
        [
            "starting",
            "1) [quality-chromium] › site-quality.spec.ts:10:1 › fails contrast",
            "AssertionError: expected 90",
            *[f"tail {index}" for index in range(20)],
        ]
    )

    details = failure_details(output, "", line_limit=5)

    assert details[0] == (
        "diagnostic: 1) [quality-chromium] › site-quality.spec.ts:10:1 › fails contrast"
    )
    assert details[1:] == ["tail 16", "tail 17", "tail 18", "tail 19"]
    assert len(details) == 5


def test_criteria_summary_distinguishes_passed_failed_and_not_run() -> None:
    criteria = ["AC-1", "AC-2", "AC-3"]
    mappings = {
        "lint": ["AC-1"],
        "tests": ["AC-1", "AC-2"],
        "release": ["AC-3"],
    }
    checks = [
        {"name": "lint", "kind": "product", "status": "passed"},
        {"name": "tests", "kind": "product", "status": "failed"},
    ]

    assert summarize_criteria(criteria, mappings, checks) == [
        {"id": "AC-1", "status": "failed", "gates": ["lint", "tests"]},
        {"id": "AC-2", "status": "failed", "gates": ["tests"]},
        {"id": "AC-3", "status": "not-run", "gates": ["release"]},
    ]


def test_task_summary_aggregates_counts_duration_and_failures() -> None:
    checks = [
        {
            "name": "pytest",
            "status": "passed",
            "duration_ms": 10.125,
            "result": {
                "exit_code": 0,
                "test_counts": {"passed": 3, "failed": 0, "skipped": 1},
            },
        },
        {
            "name": "playwright",
            "status": "failed",
            "duration_ms": 20.25,
            "details": ["fallback"],
            "result": {
                "exit_code": 1,
                "test_counts": {"passed": 2, "failed": 1, "skipped": 0},
                "failure": {"kind": "nonzero-exit", "summary": "one journey failed"},
            },
        },
    ]

    assert summarize_checks(checks) == {
        "checks": {"total": 2, "passed": 1, "failed": 1},
        "duration_ms": 30.375,
        "failures": [
            {
                "name": "playwright",
                "kind": "nonzero-exit",
                "summary": "one journey failed",
            }
        ],
        "test_counts": {"passed": 5, "failed": 1, "skipped": 1},
    }
