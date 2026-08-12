from __future__ import annotations

from harness.tools.result_reporting import (
    failure_summary,
    parse_test_counts,
    summarize_checks,
)


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
