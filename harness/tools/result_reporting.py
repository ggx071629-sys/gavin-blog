from __future__ import annotations

import re
from typing import Any

ANSI_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
COUNT_PATTERN = re.compile(
    r"(?P<count>\d+)\s+(?P<state>passed|failed|skipped|xfailed|xpassed|deselected|errors?)\b",
    re.IGNORECASE,
)
PYTEST_SUMMARY = re.compile(r"\bin\s+\d+(?:\.\d+)?s\b", re.IGNORECASE)
PLAYWRIGHT_SUMMARY = re.compile(
    r"^\d+\s+(?:passed|failed|skipped)(?:\s+\([^)]+\))?$",
    re.IGNORECASE,
)
DIAGNOSTIC_PATTERNS = (
    re.compile(r"^\d+\)\s+\[[^]]+\]"),
    re.compile(r"(?:\bAssertionError\b|Error:|\bFAILED\b)"),
    re.compile(r"\berror\s+TS\d+\b", re.IGNORECASE),
    re.compile(r"^npm error (?!Lifecycle script)", re.IGNORECASE),
    re.compile(r"\b(?:failed|error)\b", re.IGNORECASE),
)


def clean_output(value: str, *, redactions: list[str] | None = None) -> str:
    cleaned = ANSI_PATTERN.sub("", value)
    for target in redactions or []:
        if target:
            cleaned = cleaned.replace(target, "<isolated-worktree>")
            cleaned = cleaned.replace(target.replace("\\", "/"), "<isolated-worktree>")
    return cleaned


def _add_counts(target: dict[str, int], line: str) -> None:
    aliases = {
        "passed": "passed",
        "xpassed": "passed",
        "failed": "failed",
        "error": "failed",
        "errors": "failed",
        "skipped": "skipped",
        "xfailed": "skipped",
        "deselected": "skipped",
    }
    for match in COUNT_PATTERN.finditer(line):
        state = aliases[match.group("state").lower()]
        target[state] += int(match.group("count"))


def parse_test_counts(stdout: str, stderr: str = "") -> dict[str, int] | None:
    counts = {"passed": 0, "failed": 0, "skipped": 0}
    matched = False
    for raw_line in clean_output(stdout + "\n" + stderr).splitlines():
        line = raw_line.strip()
        is_vitest = line.startswith("Tests ")
        is_pytest = bool(PYTEST_SUMMARY.search(line)) and bool(COUNT_PATTERN.search(line))
        is_playwright = bool(PLAYWRIGHT_SUMMARY.fullmatch(line))
        if not (is_vitest or is_pytest or is_playwright):
            continue
        _add_counts(counts, line)
        matched = True
    return counts if matched else None


def failure_summary(
    stdout: str,
    stderr: str,
    *,
    redactions: list[str] | None = None,
) -> str:
    lines = [
        line.strip()
        for line in clean_output(stdout + "\n" + stderr, redactions=redactions).splitlines()
        if line.strip()
    ]
    for pattern in DIAGNOSTIC_PATTERNS:
        for line in lines:
            if pattern.search(line):
                return line[:300]
    return (lines[-1] if lines else "command exited without diagnostic output")[:300]


def failure_details(
    stdout: str,
    stderr: str,
    *,
    redactions: list[str] | None = None,
    line_limit: int = 12,
) -> list[str]:
    anchor = failure_summary(stdout, stderr, redactions=redactions)
    lines = [
        line.strip()
        for line in clean_output(stdout + "\n" + stderr, redactions=redactions).splitlines()
        if line.strip()
    ]
    details = [f"diagnostic: {anchor}"]
    for line in lines[-max(0, line_limit - 1) :]:
        bounded = line[:300]
        if bounded != anchor and bounded not in details:
            details.append(bounded)
    return details[:line_limit]


def summarize_criteria(
    criteria: list[str],
    mappings: dict[str, list[str]],
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    statuses = {
        str(check.get("name")): str(check.get("status", "failed"))
        for check in checks
        if isinstance(check, dict) and check.get("kind") == "product"
    }
    results: list[dict[str, Any]] = []
    for criterion in criteria:
        gates = [gate for gate, covered in mappings.items() if criterion in covered]
        gate_statuses = [statuses.get(gate) for gate in gates]
        if any(status == "failed" for status in gate_statuses):
            status = "failed"
        elif gates and all(status == "passed" for status in gate_statuses):
            status = "passed"
        else:
            status = "not-run"
        results.append({"id": criterion, "status": status, "gates": gates})
    return results


def summarize_checks(checks: list[dict[str, Any]]) -> dict[str, Any]:
    total_counts = {"passed": 0, "failed": 0, "skipped": 0}
    counts_detected = False
    failures: list[dict[str, str]] = []
    passed_checks = 0
    duration_ms = 0.0
    for check in checks:
        status = str(check.get("status", "failed"))
        if status == "passed":
            passed_checks += 1
        duration_ms += float(check.get("duration_ms", 0) or 0)
        result = check.get("result")
        if isinstance(result, dict):
            counts = result.get("test_counts")
            if isinstance(counts, dict) and check.get("provenance", {}).get("mode") not in {"reused", "subsumed"}:
                counts_detected = True
                for state in total_counts:
                    total_counts[state] += int(counts.get(state, 0) or 0)
        if status != "passed":
            failure = result.get("failure") if isinstance(result, dict) else None
            details = check.get("details")
            fallback = (
                str(details[0])
                if isinstance(details, list) and details
                else "check failed without diagnostic details"
            )
            failures.append(
                {
                    "name": str(check.get("name", "unknown")),
                    "kind": (
                        str(failure.get("kind", "check-failed"))
                        if isinstance(failure, dict)
                        else "check-failed"
                    ),
                    "summary": (
                        str(failure.get("summary", fallback))[:300]
                        if isinstance(failure, dict)
                        else fallback[:300]
                    ),
                }
            )
    summary: dict[str, Any] = {
        "checks": {
            "total": len(checks),
            "passed": passed_checks,
            "failed": len(checks) - passed_checks,
        },
        "duration_ms": round(duration_ms, 3),
        "failures": failures,
    }
    if counts_detected:
        summary["test_counts"] = total_counts
    return summary
