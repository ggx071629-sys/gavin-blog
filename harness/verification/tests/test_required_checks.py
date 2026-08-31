from __future__ import annotations

from pathlib import Path

import pytest

from harness.tools import validator


def _configure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    required: object,
) -> Path:
    checks = tmp_path / "checks"
    checks.mkdir()
    monkeypatch.setattr(validator, "harness_root", lambda: tmp_path)
    monkeypatch.setattr(validator, "project_root", lambda: tmp_path)
    monkeypatch.setattr(
        validator,
        "load_config",
        lambda: {
            "verification": {
                "checks": "checks",
                "required_task_checks": required,
            }
        },
    )
    return checks


def _write_check(path: Path, name: str) -> None:
    path.write_text(
        "def run(_context):\n"
        f"    return {{'name': {name!r}, 'passed': True, 'details': []}}\n",
        encoding="utf-8",
    )


def test_required_check_registration_passes_only_for_one_discovered_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checks = _configure(
        tmp_path,
        monkeypatch,
        required=["module-coverage"],
    )
    _write_check(checks / "module_coverage.py", "module-coverage")

    results = validator.run_checks()

    assert [result["name"] for result in results] == ["module-coverage"]
    assert validator.passed(results)


def test_required_check_registration_fails_closed_when_missing_or_duplicated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checks = _configure(
        tmp_path,
        monkeypatch,
        required=["module-coverage"],
    )

    missing = validator.run_checks()
    assert missing[-1]["name"] == "required-check-registration"
    assert missing[-1]["status"] == "failed"
    assert missing[-1]["details"] == [
        "required check is not registered: module-coverage"
    ]

    _write_check(checks / "one.py", "module-coverage")
    _write_check(checks / "two.py", "module-coverage")
    duplicated = validator.run_checks()
    assert duplicated[-1]["status"] == "failed"
    assert duplicated[-1]["details"] == [
        "required check must be registered exactly once: module-coverage"
    ]


def test_required_check_configuration_rejects_empty_or_duplicate_names(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure(tmp_path, monkeypatch, required=[])
    empty = validator.run_checks()
    assert "must be a non-empty array of check names" in empty[-1]["details"][0]

    monkeypatch.setattr(
        validator,
        "load_config",
        lambda: {
            "verification": {
                "checks": "checks",
                "required_task_checks": ["module-coverage", "module-coverage"],
            }
        },
    )
    duplicated = validator.run_checks()
    assert "must not contain duplicates" in duplicated[-1]["details"][0]
