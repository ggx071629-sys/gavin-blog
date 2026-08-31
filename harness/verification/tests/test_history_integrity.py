from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

CHECK_PATH = Path(__file__).parents[1] / "checks" / "history_integrity.py"


def _load_check():
    spec = importlib.util.spec_from_file_location("harness_history_integrity_check", CHECK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _closed_task(root: Path, task_id: str) -> None:
    _write(
        root / "specs" / "archive" / f"{task_id}.md",
        "---\n"
        f"id: archive-{task_id}\n"
        "level: L2\n"
        "summary: fixture\n"
        "load_when:\n"
        "  - fixture\n"
        f"task_id: {task_id}\n"
        "status: compressed\n"
        "---\n\n"
        f"[evidence](../../verification/evidence/{task_id}.json)\n",
    )
    _write(
        root / "verification" / "evidence" / f"{task_id}.json",
        json.dumps(
            {"schema_version": 2, "task_id": task_id, "status": "passed"}
        ),
    )
    _write(
        root / "evolution" / "events" / f"{task_id}--spec-completed.json",
        json.dumps(
            {
                "schema_version": 1,
                "event_type": "spec.completed",
                "task_id": task_id,
                "source": "lifecycle",
                "may_modify_agents_md": False,
            }
        ),
    )


def _context(root: Path) -> dict[str, object]:
    return {
        "harness_root": root,
        "project_root": root.parent,
        "config": {
            "specs": {"active": "specs/active", "archive": "specs/archive"},
            "verification": {"evidence": "verification/evidence"},
            "evolution": {"events": "evolution/events"},
        },
    }


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_history_integrity_accepts_complete_close_and_standalone_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    check = _load_check()
    task_id = "20260814-closed"
    _closed_task(tmp_path, task_id)
    _write(
        tmp_path / "verification" / "evidence" / "20260814-standalone.json",
        "{}",
    )
    monkeypatch.setattr(
        check,
        "_historical_active_paths",
        lambda _: {f"harness/specs/active/{task_id}.md"},
    )

    result = check.run(_context(tmp_path))

    assert result["passed"] is True
    assert result["details"] == [
        "1 deterministic closes retain archive, evidence, event, and active-spec history"
    ]


def test_history_integrity_rejects_missing_mismatched_and_active_close_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    check = _load_check()
    task_id = "20260814-broken"
    _closed_task(tmp_path, task_id)
    (tmp_path / "verification" / "evidence" / f"{task_id}.json").unlink()
    _write(tmp_path / "specs" / "active" / f"{task_id}.md", "active")
    event = tmp_path / "evolution" / "events" / f"{task_id}--spec-completed.json"
    payload = json.loads(event.read_text(encoding="utf-8"))
    payload["task_id"] = "20260814-other"
    _write(event, json.dumps(payload))
    monkeypatch.setattr(check, "_historical_active_paths", lambda _: set())

    result = check.run(_context(tmp_path))

    assert result["passed"] is False
    assert any("active task overlaps" in detail for detail in result["details"])
    assert any("original active spec is absent" in detail for detail in result["details"])
    assert any("main evidence is missing" in detail for detail in result["details"])
    assert any("event contract is inconsistent" in detail for detail in result["details"])


def test_m08_history_01_binds_exact_evidence_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    check = _load_check()
    task_id = "20260901-bound"
    evidence_payload = {
        "schema_version": 2,
        "task_id": task_id,
        "created_at": "2026-09-01T00:00:00+00:00",
        "command": f"python -m tools.harness verify {task_id}",
        "status": "passed",
        "acceptance_criteria": ["AC-1"],
        "criteria_results": [],
        "verification_profile": "focused",
        "fingerprints": {},
        "documentation": {},
        "execution": {},
        "verification_cases": {},
        "checks": [],
        "summary": {},
        "source_commit": "a" * 40,
    }
    evidence_text = json.dumps(evidence_payload, sort_keys=True)
    digest = hashlib.sha256(evidence_text.encode()).hexdigest()
    evidence = tmp_path / "verification/evidence" / f"{task_id}.json"
    _write(evidence, evidence_text)
    _write(
        tmp_path / "specs/archive" / f"{task_id}.md",
        "---\n"
        f"id: archive-{task_id}\n"
        f"task_id: {task_id}\n"
        "status: compressed\n"
        f"evidence_sha256: {digest}\n"
        "---\n\n"
        f"[evidence](../../verification/evidence/{task_id}.json)\n",
    )
    event = tmp_path / "evolution/events" / f"{task_id}--spec-completed.json"
    _write(
        event,
        json.dumps(
            {
                "schema_version": 2,
                "event_type": "spec.completed",
                "task_id": task_id,
                "source": "lifecycle",
                "may_modify_agents_md": False,
                "evidence_sha256": digest,
            }
        ),
    )
    monkeypatch.setattr(
        check,
        "_historical_active_paths",
        lambda _: {f"harness/specs/active/{task_id}.md"},
    )

    assert check.run(_context(tmp_path))["passed"] is True

    _write(evidence, evidence_text + "\n")
    result = check.run(_context(tmp_path))
    assert result["passed"] is False
    assert any("digest binding is inconsistent" in detail for detail in result["details"])

    event_payload = json.loads(event.read_text(encoding="utf-8"))
    event_payload["schema_version"] = 1
    event_payload.pop("evidence_sha256")
    _write(event, json.dumps(event_payload))
    result = check.run(_context(tmp_path))
    assert any("digest-bound close contract is required" in detail for detail in result["details"])


def test_historical_active_paths_include_side_parent_history_after_merge(
    tmp_path: Path,
) -> None:
    check = _load_check()
    task_path = "harness/specs/active/20260827-merged.md"
    _git(tmp_path, "init", "--initial-branch=main")
    _git(tmp_path, "config", "user.name", "Harness Test")
    _git(tmp_path, "config", "user.email", "harness@example.invalid")
    _write(tmp_path / "README.md", "base\n")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "base")

    _git(tmp_path, "switch", "-c", "task")
    _write(tmp_path / task_path, "active\n")
    _git(tmp_path, "add", task_path)
    _git(tmp_path, "commit", "-m", "add active spec")
    (tmp_path / task_path).unlink()
    _git(tmp_path, "add", "--update", task_path)
    _git(tmp_path, "commit", "-m", "close active spec")

    _git(tmp_path, "switch", "main")
    _write(tmp_path / "README.md", "base\nmain\n")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "advance main")
    _git(tmp_path, "merge", "--no-ff", "task", "-m", "merge task")

    assert task_path in check._historical_active_paths(tmp_path)
