from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from harness.tools import harness as harness_cli
from harness.tools import product_verification

TASK_ID = "20260812-product-evidence"


def _write_spec(path: Path, *, plan: str = "- harness-tests => AC-1, AC-2") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"id: spec-{TASK_ID}\n"
        "level: L1\n"
        "summary: Product evidence fixture\n"
        "load_when:\n"
        f"  - task:{TASK_ID}\n"
        f"task_id: {TASK_ID}\n"
        "status: active\n"
        "verification_profile: focused\n"
        "---\n\n"
        "# Acceptance criteria\n\n"
        "- AC-1: First observable outcome.\n"
        "- AC-2: Second observable outcome.\n\n"
        "# Verification plan\n\n"
        f"{plan}\n",
        encoding="utf-8",
    )
    return path


def test_verification_contract_requires_complete_deterministic_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _write_spec(tmp_path / f"{TASK_ID}.md")
    monkeypatch.setattr(product_verification, "active_spec", lambda _: spec)

    criteria, mappings = product_verification.verification_contract(TASK_ID)

    assert criteria == ["AC-1", "AC-2"]
    assert mappings == {"harness-tests": ["AC-1", "AC-2"]}

    _write_spec(spec, plan="- harness-tests => AC-1")
    with pytest.raises(
        product_verification.ProductVerificationError,
        match="lack a verification gate: AC-2",
    ):
        product_verification.verification_contract(TASK_ID)


def test_run_gates_uses_registered_argv_without_a_shell(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], Path]] = []
    monkeypatch.setattr(product_verification, "project_root", lambda: tmp_path)
    monkeypatch.setattr(
        product_verification,
        "_configured_gates",
        lambda: {
            "harness-tests": {
                "cwd": ".",
                "command": ["{python}", "-m", "pytest", "verification/tests"],
            }
        },
    )

    def run(command: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append((command, Path(str(kwargs["cwd"]))))
        assert "shell" not in kwargs
        return SimpleNamespace(returncode=0, stdout="passed", stderr="")

    monkeypatch.setattr(product_verification.subprocess, "run", run)

    results = product_verification.run_gates({"harness-tests": ["AC-1"]})

    assert results[0]["status"] == "passed"
    assert results[0]["covers"] == ["AC-1"]
    assert calls[0][0][0] == product_verification.sys.executable
    assert calls[0][1] == tmp_path


def test_task_verify_runs_product_gates_and_writes_current_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = tmp_path / "task.json"
    harness_results = [
        {
            "name": "structure",
            "passed": True,
            "status": "passed",
            "duration_ms": 1,
            "details": [],
        }
    ]
    gate_results = [
        {
            "name": "harness-tests",
            "kind": "product",
            "command": "python -m pytest",
            "passed": True,
            "status": "passed",
            "duration_ms": 2,
            "covers": ["AC-1", "AC-2"],
            "details": [],
        }
    ]
    monkeypatch.setattr(harness_cli.summarizer, "validate_task_id", lambda _: None)
    monkeypatch.setattr(harness_cli.summarizer, "active_spec", lambda _: tmp_path / "spec.md")
    monkeypatch.setattr(harness_cli.summarizer, "ensure_spec_in_git_history", lambda _: None)
    monkeypatch.setattr(harness_cli.lifecycle, "task_status", lambda _: "active")
    monkeypatch.setattr(harness_cli.validator, "run_checks", lambda: list(harness_results))
    monkeypatch.setattr(product_verification, "ensure_source_clean", lambda: None)
    monkeypatch.setattr(
        product_verification,
        "verification_contract",
        lambda _: (["AC-1", "AC-2"], {"harness-tests": ["AC-1", "AC-2"]}),
    )
    monkeypatch.setattr(product_verification, "verification_profile", lambda _: "focused")
    monkeypatch.setattr(product_verification, "validate_configured_gates", lambda *_: None)
    monkeypatch.setattr(
        product_verification,
        "evidence_fingerprints",
        lambda *_: {"source_tree": "tree"},
    )
    execution = {
        "mode": "git-worktree",
        "source_commit": "abc123",
        "cleanup_status": "passed",
    }
    monkeypatch.setattr(product_verification, "head_commit", lambda: "abc123")
    monkeypatch.setattr(
        harness_cli.isolated_verification,
        "run_in_worktree",
        lambda *_: (gate_results, execution),
    )

    def write(
        task_id: str,
        command: str,
        criteria: list[str],
        profile: str,
        fingerprints: dict[str, str],
        written_execution: dict[str, object],
        results: list[dict[str, object]],
    ) -> Path:
        assert task_id == TASK_ID
        assert command.endswith(TASK_ID)
        assert criteria == ["AC-1", "AC-2"]
        assert profile == "focused"
        assert fingerprints == {"source_tree": "tree"}
        assert written_execution == execution
        assert results == harness_results + gate_results
        evidence.write_text("{}", encoding="utf-8")
        return evidence

    monkeypatch.setattr(harness_cli.validator, "write_task_evidence", write)
    monkeypatch.setattr(product_verification, "derived_task_state", lambda *_: "verified")

    assert harness_cli.command_verify(SimpleNamespace(task_id=TASK_ID)) == 0
    assert evidence.is_file()


def test_close_evidence_requires_current_head_complete_coverage_and_clean_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = tmp_path / "evidence.json"
    payload = {
        "schema_version": 2,
        "task_id": TASK_ID,
        "status": "passed",
        "source_commit": "abc123",
        "acceptance_criteria": ["AC-1", "AC-2"],
        "verification_profile": "focused",
        "fingerprints": {"source_tree": "tree"},
        "execution": {
            "mode": "git-worktree",
            "source_commit": "abc123",
            "cleanup_status": "passed",
        },
        "checks": [
            {
                "name": "harness-tests",
                "kind": "product",
                "command": "python -m pytest",
                "status": "passed",
                "covers": ["AC-1", "AC-2"],
            },
            {
                "name": "isolated-worktree",
                "kind": "isolation",
                "command": "git worktree add --detach <temporary> HEAD",
                "status": "passed",
                "covers": [],
            },
        ],
    }
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(
        product_verification,
        "verification_contract",
        lambda _: (["AC-1", "AC-2"], {"harness-tests": ["AC-1", "AC-2"]}),
    )
    monkeypatch.setattr(product_verification, "verification_profile", lambda _: "focused")
    monkeypatch.setattr(product_verification, "validate_configured_gates", lambda *_: None)
    monkeypatch.setattr(
        product_verification,
        "evidence_fingerprints",
        lambda *_: {"source_tree": "tree"},
    )
    monkeypatch.setattr(product_verification, "head_commit", lambda: "abc123")
    monkeypatch.setattr(product_verification, "ensure_source_clean", lambda: None)

    assert product_verification.validate_evidence(TASK_ID, evidence) == []

    payload["source_commit"] = "stale"
    payload["checks"][0]["covers"] = ["AC-1"]
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    errors = product_verification.validate_evidence(TASK_ID, evidence)
    assert "task evidence source_commit does not match HEAD" in errors
    assert any("coverage does not match" in error for error in errors)


def test_profile_requires_its_minimum_registered_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        product_verification,
        "_configured_gates",
        lambda: {"api-lint": {}, "api-tests": {}, "web-quality": {}},
    )
    monkeypatch.setattr(
        product_verification,
        "_configured_profiles",
        lambda: {
            "stack": {
                "required_gates": ["api-lint", "api-tests", "web-quality"]
            }
        },
    )

    with pytest.raises(
        product_verification.ProductVerificationError,
        match="requires gates: api-tests, web-quality",
    ):
        product_verification.validate_configured_gates(
            {"api-lint": ["AC-1"]},
            "stack",
        )


def test_derived_verified_state_falls_back_to_active_when_inputs_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = tmp_path / "evidence.json"
    monkeypatch.setattr(product_verification, "validate_evidence", lambda *_: [])
    assert product_verification.derived_task_state(TASK_ID, evidence) == "verified"

    monkeypatch.setattr(
        product_verification,
        "validate_evidence",
        lambda *_: ["fingerprint drift"],
    )
    assert product_verification.derived_task_state(TASK_ID, evidence) == "active"


def test_fingerprints_change_with_spec_contract_and_gate_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _write_spec(tmp_path / f"{TASK_ID}.md")
    gate_config = {
        "harness-tests": {
            "cwd": ".",
            "command": ["{python}", "-m", "pytest"],
        }
    }
    monkeypatch.setattr(product_verification, "active_spec", lambda _: spec)
    monkeypatch.setattr(product_verification, "_configured_gates", lambda: gate_config)
    monkeypatch.setattr(
        product_verification,
        "_configured_profiles",
        lambda: {"focused": {"required_gates": []}},
    )
    monkeypatch.setattr(product_verification, "_git_value", lambda *_: "tree-one")
    criteria = ["AC-1", "AC-2"]
    mappings = {"harness-tests": criteria}

    first = product_verification.evidence_fingerprints(
        TASK_ID,
        criteria,
        mappings,
        "focused",
    )
    spec.write_text(spec.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    second = product_verification.evidence_fingerprints(
        TASK_ID,
        criteria,
        mappings,
        "focused",
    )
    gate_config["harness-tests"]["command"].append("-q")
    third = product_verification.evidence_fingerprints(
        TASK_ID,
        criteria,
        mappings,
        "focused",
    )

    assert first["source_tree"] == "tree-one"
    assert first["active_spec_sha256"] != second["active_spec_sha256"]
    assert second["gate_config_sha256"] != third["gate_config_sha256"]
