from __future__ import annotations

from pathlib import Path

import pytest
from harness.tools import task_reporting, verification_resume

TASK_ID = "20260812-status-fixture"


def _active(path: Path, status: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"id: spec-{TASK_ID}\n"
        "level: L1\n"
        "summary: Status fixture\n"
        "load_when:\n"
        f"  - task:{TASK_ID}\n"
        f"task_id: {TASK_ID}\n"
        f"status: {status}\n"
        "verification_profile: focused\n"
        "---\n",
        encoding="utf-8",
    )


def test_frozen_status_does_not_validate_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active = tmp_path / "active.md"
    _active(active, "frozen")
    monkeypatch.setattr(task_reporting.summarizer, "validate_task_id", lambda _: None)
    monkeypatch.setattr(task_reporting.summarizer, "active_spec", lambda _: active)

    def forbidden(*_: object) -> list[str]:
        raise AssertionError("frozen evidence must not be evaluated")

    monkeypatch.setattr(task_reporting.product_verification, "validate_evidence", forbidden)

    record = task_reporting.task_record(TASK_ID)

    assert record["state"] == "frozen"
    assert record["evidence"] == "not-evaluated"


def test_status_reports_verified_compressed_and_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active = tmp_path / "active.md"
    archive = tmp_path / "archive.md"
    _active(active, "active")
    monkeypatch.setattr(task_reporting.summarizer, "validate_task_id", lambda _: None)
    monkeypatch.setattr(task_reporting.summarizer, "active_spec", lambda _: active)
    monkeypatch.setattr(task_reporting.summarizer, "archive_spec", lambda _: archive)
    monkeypatch.setattr(task_reporting.validator, "evidence_path", lambda _: tmp_path / "evidence.json")
    monkeypatch.setattr(task_reporting.product_verification, "validate_evidence", lambda *_a, **_k: [])
    monkeypatch.setattr(verification_resume, "authenticate", lambda *_: {})
    monkeypatch.setattr(verification_resume, "gate_plan", lambda *_: [])
    monkeypatch.setattr(verification_resume, "preview", lambda *_: {"gates": [], "next": "verify"})

    assert task_reporting.task_record(TASK_ID)["state"] == "verified"

    active.unlink()
    archive.write_text("archive", encoding="utf-8")
    assert task_reporting.task_record(TASK_ID)["state"] == "compressed"

    archive.unlink()
    assert task_reporting.task_record(TASK_ID)["state"] == "missing"
