from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from harness.tools import harness as harness_cli
from harness.tools import product_verification, validator
from harness.tools.result_reporting import summarize_checks

TASK_ID = "20260812-product-evidence"


@pytest.fixture(autouse=True)
def legacy_contract_fixture(monkeypatch):
    # These fixtures exercise the retained legacy schema with synthetic gate routes.
    from harness.tools import impact
    monkeypatch.setattr(impact, "enabled", lambda: False)



def test_task_evidence_is_written_with_canonical_lf_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = tmp_path / "task.json"
    monkeypatch.setattr(validator, "evidence_path", lambda _: evidence)
    monkeypatch.setattr(validator, "_source_commit", lambda: "a" * 40)

    validator.write_task_evidence(
        TASK_ID,
        f"python -m tools.harness verify {TASK_ID}",
        ["AC-1"],
        {"harness-tests": ["AC-1"]},
        "focused",
        {"source_tree": "tree"},
        {},
        {"mode": "git-worktree"},
        [
            {
                "name": "harness-tests",
                "kind": "product",
                "command": "python -m pytest",
                "status": "passed",
                "passed": True,
                "duration_ms": 1,
                "covers": ["AC-1"],
                "details": [],
                "result": {"exit_code": 0},
            }
        ],
    )

    assert evidence.read_bytes().endswith(b"\n")
    assert b"\r\n" not in evidence.read_bytes()


def _write_spec(
    path: Path,
    *,
    plan: str = "- harness-tests => AC-1, AC-2",
    cases: str = "- AC-1 => M08-TRACE-01\n- AC-2 => M08-TRACE-02",
) -> Path:
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
        "documentation_impact: none\n"
        "documentation_reason: The fixture does not change durable documentation.\n"
        "---\n\n"
        "# Acceptance criteria\n\n"
        "- AC-1: First observable outcome.\n"
        "- AC-2: Second observable outcome.\n\n"
        "# Verification plan\n\n"
        "## Verification cases\n\n"
        f"{cases}\n\n"
        "## Gates\n\n"
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


def test_verification_case_plan_requires_one_structural_mapping_per_criterion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _write_spec(tmp_path / f"{TASK_ID}.md")
    monkeypatch.setattr(product_verification, "active_spec", lambda _: spec)

    assert product_verification.verification_case_plan(
        TASK_ID, ["AC-1", "AC-2"]
    ) == {
        "AC-1": ["M08-TRACE-01"],
        "AC-2": ["M08-TRACE-02"],
    }

    _write_spec(spec, cases="- AC-1 => M08-FUTURE-01")
    with pytest.raises(
        product_verification.ProductVerificationError,
        match="lack a Verification cases mapping: AC-2",
    ):
        product_verification.verification_case_plan(TASK_ID, ["AC-1", "AC-2"])

    _write_spec(
        spec,
        cases="- AC-1 => M08-FUTURE-01\n- AC-1 => M08-FUTURE-02\n- AC-2 => M08-TRACE-02",
    )
    with pytest.raises(
        product_verification.ProductVerificationError,
        match="mapped more than once",
    ):
        product_verification.verification_case_plan(TASK_ID, ["AC-1", "AC-2"])


def test_resolved_verification_cases_require_case_existence_and_gate_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _write_spec(tmp_path / f"{TASK_ID}.md")
    monkeypatch.setattr(product_verification, "active_spec", lambda _: spec)
    gates = {
        "harness-tests": {},
        "e2e": {},
        "api-tests": {},
    }
    monkeypatch.setattr(product_verification, "_configured_gates", lambda: gates)
    case_index = {
        "M08-TRACE-01": {
            "id": "M08-TRACE-01",
            "module_id": "M08",
            "module_name": "工程控制面",
            "priority": "P0",
            "scenario": "Resolve the first case.",
            "expectations": [],
            "required_gates": ["harness-tests"],
            "test_refs": [{"path": "first.py", "name": "test_first"}],
        },
        "M08-TRACE-02": {
            "id": "M08-TRACE-02",
            "module_id": "M08",
            "module_name": "工程控制面",
            "priority": "P1",
            "scenario": "Resolve the second case.",
            "expectations": [],
            "required_gates": ["e2e"],
            "test_refs": [{"path": "second.ts", "name": "second"}],
        },
    }
    resolved_contract = {
        "contract": {"contract_id": "fixture-v1"},
        "digest": "b" * 64,
        "case_index": case_index,
    }
    monkeypatch.setattr(
        product_verification,
        "resolve_module_contract",
        lambda *_args, **_kwargs: resolved_contract,
    )

    report = product_verification.resolved_verification_cases(
        TASK_ID,
        ["AC-1", "AC-2"],
        {"harness-tests": ["AC-1"], "e2e": ["AC-2"]},
    )

    assert report["contract_sha256"] == "b" * 64
    assert report["criteria"][0]["cases"][0]["id"] == "M08-TRACE-01"
    assert report["criteria"][1]["cases"][0]["gate_satisfaction"] == [
        {"gate": "e2e", "satisfied_by": "e2e", "mode": "direct"}
    ]

    case_index["M08-TRACE-02"]["required_gates"] = ["api-tests"]
    with pytest.raises(
        product_verification.ProductVerificationError,
        match="does not cover M08-TRACE-02 required gates: api-tests",
    ):
        product_verification.resolved_verification_cases(
            TASK_ID,
            ["AC-1", "AC-2"],
            {"harness-tests": ["AC-1"], "e2e": ["AC-2"]},
        )

    case_index.pop("M08-TRACE-01")
    with pytest.raises(
        product_verification.ProductVerificationError,
        match="unresolved module case: M08-TRACE-01",
    ):
        product_verification.resolved_verification_cases(
            TASK_ID,
            ["AC-1", "AC-2"],
            {"harness-tests": ["AC-1"], "e2e": ["AC-2"]},
        )

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
        assert kwargs["timeout_seconds"] == 900
        return SimpleNamespace(returncode=0, stdout="passed", stderr="")

    monkeypatch.setattr(product_verification, "_run_supervised_command", run)

    results = product_verification.run_gates({"harness-tests": ["AC-1"]})

    assert results[0]["status"] == "passed"
    assert results[0]["covers"] == ["AC-1"]
    assert calls[0][0][0] == product_verification.sys.executable
    assert calls[0][1] == tmp_path


def test_api_python_placeholder_uses_execution_root_virtual_environment(
    tmp_path: Path,
) -> None:
    execution_root = tmp_path / "isolated"
    interpreter = (
        execution_root / "apps" / "api" / ".venv" / "Scripts" / "python.exe"
    )
    interpreter.parent.mkdir(parents=True)
    interpreter.write_bytes(b"")
    cwd = execution_root / "apps" / "api"
    cwd.mkdir(parents=True, exist_ok=True)

    command, resolved_cwd, timeout = product_verification._command(
        "api-lint",
        {
            "cwd": "apps/api",
            "command": ["{api_python}", "-m", "ruff", "check", "."],
            "timeout_seconds": 120,
        },
        execution_root,
    )

    assert command[0] == str(interpreter)
    assert resolved_cwd == cwd.resolve()
    assert timeout == 120


def test_api_python_placeholder_fails_closed_without_virtual_environment(
    tmp_path: Path,
) -> None:
    (tmp_path / "apps" / "api").mkdir(parents=True)

    with pytest.raises(
        product_verification.ProductVerificationError,
        match="API virtual environment Python was not found",
    ):
        product_verification._command(
            "api-tests",
            {"cwd": "apps/api", "command": ["{api_python}", "-m", "pytest"]},
            tmp_path,
        )


def test_gate_failure_result_distinguishes_nonzero_timeout_and_execution_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(product_verification, "project_root", lambda: tmp_path)
    monkeypatch.setattr(
        product_verification,
        "_configured_gates",
        lambda: {
            "fixture": {
                "cwd": ".",
                "command": ["{python}", "-m", "fixture"],
                "timeout_seconds": 1,
            }
        },
    )
    root_text = str(tmp_path)
    monkeypatch.setattr(
        product_verification,
        "_run_supervised_command",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=1,
            stdout=f"Error: failed at {root_text}\\fixture.py\n1 failed in 0.1s",
            stderr="",
        ),
    )

    nonzero = product_verification.run_gates(
        {"fixture": ["AC-1"]},
        execution_root=tmp_path,
    )[0]
    assert nonzero["result"]["failure"] == {
        "kind": "nonzero-exit",
        "summary": "Error: failed at <isolated-worktree>\\fixture.py",
        "source": "gate-runner", "hint": "nonzero-exit",
    }
    assert nonzero["details"][0] == (
        "diagnostic: Error: failed at <isolated-worktree>\\fixture.py"
    )
    assert nonzero["result"]["test_counts"]["failed"] == 1

    def timeout(*_args: object, **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired("fixture", 1)

    monkeypatch.setattr(product_verification, "_run_supervised_command", timeout)
    timed_out = product_verification.run_gates({"fixture": ["AC-1"]})[0]
    assert timed_out["result"]["failure"]["kind"] == "timeout"

    monkeypatch.setattr(
        product_verification,
        "_configured_gates",
        lambda: {"fixture": {"cwd": ".", "command": ["missing-fixture-command"]}},
    )
    monkeypatch.setattr(product_verification.shutil, "which", lambda _: None)
    execution_error = product_verification.run_gates({"fixture": ["AC-1"]})[0]
    assert execution_error["result"]["failure"]["kind"] == "startup"


def test_task_verify_runs_product_gates_and_writes_current_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = tmp_path / "task.json"
    harness_results = [
        {
            "name": "module-coverage",
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
    monkeypatch.setattr(product_verification, "ensure_source_clean", lambda *_: None)
    monkeypatch.setattr(
        product_verification,
        "verification_contract",
        lambda _: (["AC-1", "AC-2"], {"harness-tests": ["AC-1", "AC-2"]}),
    )
    monkeypatch.setattr(product_verification, "verification_profile", lambda _: "focused")
    monkeypatch.setattr(product_verification, "validate_configured_gates", lambda *_: None)
    verification_cases = {
        "schema_version": 1,
        "contract_id": "fixture",
        "contract_sha256": "a" * 64,
        "criteria": [],
    }
    monkeypatch.setattr(
        product_verification,
        "resolved_verification_cases",
        lambda *_: verification_cases,
    )
    documentation = {
        "impact": "none",
        "reason": "Fixture only.",
        "targets": [],
        "baseline_commit": None,
        "target_blobs": {},
    }
    monkeypatch.setattr(
        product_verification,
        "documentation_report",
        lambda _: documentation,
    )
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
        mappings: dict[str, list[str]],
        profile: str,
        fingerprints: dict[str, str],
        written_documentation: dict[str, object],
        written_execution: dict[str, object],
        results: list[dict[str, object]],
        written_verification_cases: dict[str, object],
        **_kwargs,
    ) -> Path:
        assert task_id == TASK_ID
        assert command.endswith(TASK_ID)
        assert criteria == ["AC-1", "AC-2"]
        assert mappings == {"harness-tests": ["AC-1", "AC-2"]}
        assert profile == "focused"
        assert fingerprints == {"source_tree": "tree"}
        assert written_documentation == documentation
        assert written_execution == execution
        assert results == harness_results + gate_results
        assert written_verification_cases == verification_cases
        evidence.write_text("{}", encoding="utf-8")
        return evidence

    monkeypatch.setattr(harness_cli.run_store, "store_root", lambda: tmp_path / "local-runs")
    monkeypatch.setattr(harness_cli.verification_resume.inputs, "input_snapshot", lambda *_: {"head": "abc123"})
    monkeypatch.setattr(harness_cli.verification_resume, "execute", lambda *_a, **_k: (gate_results, execution))
    monkeypatch.setattr(harness_cli.verification_resume, "attest", lambda *_: None)
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
        "created_at": "2026-08-12T00:00:00+00:00",
        "command": f"python -m tools.harness verify {TASK_ID}",
        "status": "passed",
        "source_commit": "abc123",
        "acceptance_criteria": ["AC-1", "AC-2"],
        "criteria_results": [
            {
                "id": "AC-1",
                "status": "passed",
                "gates": ["harness-tests"],
            },
            {
                "id": "AC-2",
                "status": "passed",
                "gates": ["harness-tests"],
            },
        ],
        "verification_profile": "focused",
        "fingerprints": {"source_tree": "tree"},
        "documentation": {
            "impact": "none",
            "reason": "Fixture only.",
            "targets": [],
            "baseline_commit": None,
            "target_blobs": {},
        },
        "execution": {
            "mode": "git-worktree",
            "source_commit": "abc123",
            "cleanup_status": "passed",
        },
        "verification_cases": {
            "schema_version": 1,
            "contract_id": "fixture",
            "contract_sha256": "a" * 64,
            "criteria": [],
        },
        "checks": [
            {
                "name": "harness-tests",
                "kind": "product",
                "command": "python -m pytest",
                "status": "passed",
                "covers": ["AC-1", "AC-2"],
                "result": {"exit_code": 0},
            },
            {
                "name": "isolated-worktree",
                "kind": "isolation",
                "command": "git worktree add --detach <temporary> HEAD",
                "status": "passed",
                "covers": [],
                "result": {"exit_code": 0},
            },
            {
                "name": "module-coverage",
                "status": "passed",
                "duration_ms": 1,
                "details": [],
            },
        ],
    }
    payload["summary"] = summarize_checks(payload["checks"])
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    current_documentation = dict(payload["documentation"])
    monkeypatch.setattr(
        product_verification,
        "verification_contract",
        lambda _: (["AC-1", "AC-2"], {"harness-tests": ["AC-1", "AC-2"]}),
    )
    monkeypatch.setattr(product_verification, "verification_profile", lambda _: "focused")
    monkeypatch.setattr(product_verification, "validate_configured_gates", lambda *_: None)
    current_verification_cases = json.loads(json.dumps(payload["verification_cases"]))
    monkeypatch.setattr(
        product_verification,
        "resolved_verification_cases",
        lambda *_: current_verification_cases,
    )
    monkeypatch.setattr(
        product_verification,
        "documentation_report",
        lambda _: current_documentation,
    )
    monkeypatch.setattr(
        product_verification,
        "evidence_fingerprints",
        lambda *_: {"source_tree": "tree"},
    )
    monkeypatch.setattr(product_verification, "head_commit", lambda: "abc123")
    monkeypatch.setattr(product_verification, "ensure_source_clean", lambda *_: None)
    monkeypatch.setattr(
        product_verification,
        "_configured_gates",
        lambda: {
            "harness-tests": {
                "cwd": ".",
                "command": ["python", "-m", "pytest"],
            }
        },
    )
    monkeypatch.setattr(
        product_verification,
        "_command",
        lambda *_args, **_kwargs: (["python", "-m", "pytest"], tmp_path, 900),
    )

    assert product_verification.validate_evidence(TASK_ID, evidence) == []

    module_check = payload["checks"].pop()
    payload["summary"] = summarize_checks(payload["checks"])
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    assert any(
        "exactly one global required check: module-coverage" in error
        for error in product_verification.validate_evidence(TASK_ID, evidence)
    )
    payload["checks"].append(module_check)
    payload["summary"] = summarize_checks(payload["checks"])

    payload["verification_cases"]["contract_sha256"] = "c" * 64
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    assert any(
        "verification cases do not match" in error
        for error in product_verification.validate_evidence(TASK_ID, evidence)
    )
    payload["verification_cases"] = json.loads(
        json.dumps(current_verification_cases)
    )

    payload["checks"][0]["result"] = {
        "subsumption": {"contract_sha256": "forged", "verified": []}
    }
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    assert any(
        "subsumption proof does not match" in error
        for error in product_verification.validate_evidence(TASK_ID, evidence)
    )
    payload["checks"][0].pop("result")

    payload["criteria_results"][0]["status"] = "failed"
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    assert (
        "task evidence criteria results do not match checks"
        in product_verification.validate_evidence(TASK_ID, evidence)
    )
    payload["criteria_results"][0]["status"] = "passed"

    payload["documentation"]["reason"] = "Stale fixture reason."
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    assert any(
        "documentation does not match" in error
        for error in product_verification.validate_evidence(TASK_ID, evidence)
    )
    payload["documentation"]["reason"] = "Fixture only."

    payload["source_commit"] = "stale"
    payload["checks"][0]["covers"] = ["AC-1"]
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    errors = product_verification.validate_evidence(TASK_ID, evidence)
    assert "task evidence source_commit does not match HEAD" in errors
    assert any("coverage does not match" in error for error in errors)

    payload["source_commit"] = "abc123"
    payload["checks"][0]["covers"] = ["AC-1", "AC-2"]
    payload["summary"]["checks"]["passed"] = 1
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    assert "task evidence summary does not match checks" in product_verification.validate_evidence(
        TASK_ID,
        evidence,
    )


def test_m08_evidence_01_rejects_forged_gate_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_close_evidence_requires_current_head_complete_coverage_and_clean_source(
        tmp_path,
        monkeypatch,
    )


def test_m08_spec_01_enforces_nested_plan_and_planned_modules(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Keep the synthetic future module independent of the live module catalog.
    monkeypatch.setattr(product_verification, "EXPECTED_MODULE_IDS", ("M08",))
    spec = _write_spec(
        tmp_path / f"{TASK_ID}.md",
        cases="- AC-1 => M11-FUTURE-01\n- AC-2 => M08-TRACE-02",
    )
    monkeypatch.setattr(product_verification, "active_spec", lambda _: spec)

    with pytest.raises(
        product_verification.ProductVerificationError,
        match="neither current nor planned: M11",
    ):
        product_verification.verification_case_plan(TASK_ID, ["AC-1", "AC-2"])

    text = spec.read_text(encoding="utf-8").replace(
        "verification_profile: focused\n",
        "verification_profile: focused\nplanned_modules:\n  - M11\n",
    )
    spec.write_text(text, encoding="utf-8")
    assert product_verification.verification_case_plan(
        TASK_ID, ["AC-1", "AC-2"]
    )["AC-1"] == ["M11-FUTURE-01"]

    spec.write_text(
        text.replace("## Verification cases", "# Verification cases"),
        encoding="utf-8",
    )
    with pytest.raises(
        product_verification.ProductVerificationError,
        match="must contain exactly",
    ):
        product_verification.verification_contract(TASK_ID)


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


def _write_subsumption_contract(
    path: Path,
    stages: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "owner_gate": "release",
                "stages": stages,
            }
        ),
        encoding="utf-8",
    )


def test_release_contract_satisfies_direct_profile_and_risk_requirements(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stages = [
        {
            "gate": "api-lint",
            "stage": "api-lint",
            "cwd": "apps/api",
            "command": ["{api_python}", "-m", "ruff", "check", "."],
        },
        {
            "gate": "api-tests",
            "stage": "api-tests",
            "cwd": "apps/api",
            "command": ["{api_python}", "-m", "pytest"],
        },
    ]
    _write_subsumption_contract(tmp_path / "scripts" / "release.json", stages)
    gates = {
        "api-lint": {"cwd": "apps/api", "command": stages[0]["command"]},
        "api-tests": {"cwd": "apps/api", "command": stages[1]["command"]},
        "release": {
            "cwd": ".",
            "command": ["npm", "run", "quality:release"],
            "subsumption_contract": "scripts/release.json",
        },
    }
    monkeypatch.setattr(product_verification, "project_root", lambda: tmp_path)
    monkeypatch.setattr(product_verification, "_configured_gates", lambda: gates)
    monkeypatch.setattr(
        product_verification,
        "_configured_profiles",
        lambda: {"stack": {"required_gates": ["api-lint", "api-tests"]}},
    )
    monkeypatch.setattr(
        product_verification,
        "derived_gate_requirements",
        lambda _: {
            "paths": ["apps/api/app/main.py"],
            "routes": [
                {
                    "id": "api",
                    "matched_paths": ["apps/api/app/main.py"],
                    "required_gates": ["api-lint", "api-tests"],
                }
            ],
            "required_gates": ["api-lint", "api-tests"],
        },
    )
    spec = _write_spec(tmp_path / f"{TASK_ID}.md")
    spec.write_text(
        spec.read_text(encoding="utf-8").replace(
            "verification_profile: focused\n",
            "verification_profile: stack\n"
            "verification_escalation: Release subsumes the API lint and test floor.\n",
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(product_verification, "active_spec", lambda _: spec)

    product_verification.validate_configured_gates(
        {"release": ["AC-1"]},
        "stack",
        TASK_ID,
    )

    assert product_verification._requirement_report(
        {"api-lint", "api-tests"}, {"release": ["AC-1"]}
    ) == {
        "satisfied": [
            {"gate": "api-lint", "satisfied_by": "release", "mode": "subsumed"},
            {"gate": "api-tests", "satisfied_by": "release", "mode": "subsumed"},
        ],
        "missing": [],
    }

    first_hash = product_verification._selected_subsumption_contracts(["release"])[
        "release"
    ]["sha256"]
    contract_path = tmp_path / "scripts" / "release.json"
    contract_path.write_text(
        contract_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    second_hash = product_verification._selected_subsumption_contracts(["release"])[
        "release"
    ]["sha256"]
    assert first_hash != second_hash


def test_release_contract_rejects_registered_gate_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stage = {
        "gate": "api-tests",
        "stage": "api-tests",
        "cwd": "apps/api",
        "command": ["{api_python}", "-m", "pytest"],
    }
    _write_subsumption_contract(tmp_path / "scripts" / "release.json", [stage])
    gates = {
        "api-tests": {
            "cwd": "apps/api",
            "command": ["{api_python}", "-m", "pytest", "-q"],
        },
        "release": {
            "cwd": ".",
            "command": ["npm", "run", "quality:release"],
            "subsumption_contract": "scripts/release.json",
        },
    }
    monkeypatch.setattr(product_verification, "project_root", lambda: tmp_path)
    monkeypatch.setattr(product_verification, "_configured_gates", lambda: gates)

    with pytest.raises(
        product_verification.ProductVerificationError,
        match="does not match registered gate api-tests",
    ):
        product_verification._selected_subsumption_contracts(["release"])


def test_subsumption_runtime_proof_is_exact_and_required() -> None:
    contract = {
        "sha256": "a" * 64,
        "stages": [{"gate": "api-tests", "stage": "api-tests"}],
    }
    proof = {
        "schema_version": 1,
        "owner_gate": "release",
        "contract_sha256": "a" * 64,
        "completed": [{"gate": "api-tests", "stage": "api-tests"}],
    }

    assert product_verification._parse_subsumption_proof(
        product_verification.SUBSUMPTION_PROOF_PREFIX + json.dumps(proof),
        contract,
        "release",
    ) == {
        "contract_sha256": "a" * 64,
        "verified": [{"gate": "api-tests", "stage": "api-tests"}],
    }

    with pytest.raises(
        product_verification.ProductVerificationError,
        match="exactly one terminal",
    ):
        product_verification._parse_subsumption_proof("", contract, "release")

    proof["contract_sha256"] = "b" * 64
    with pytest.raises(
        product_verification.ProductVerificationError,
        match="does not match",
    ):
        product_verification._parse_subsumption_proof(
            product_verification.SUBSUMPTION_PROOF_PREFIX + json.dumps(proof),
            contract,
            "release",
        )


def test_zero_exit_gate_fails_closed_without_subsumption_proof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stage = {
        "gate": "child",
        "stage": "child",
        "cwd": ".",
        "command": ["{python}", "-m", "child"],
    }
    _write_subsumption_contract(tmp_path / "scripts" / "release.json", [stage])
    gates = {
        "child": {"cwd": ".", "command": stage["command"]},
        "release": {
            "cwd": ".",
            "command": ["{python}", "-m", "release"],
            "subsumption_contract": "scripts/release.json",
        },
    }
    monkeypatch.setattr(product_verification, "project_root", lambda: tmp_path)
    monkeypatch.setattr(product_verification, "_configured_gates", lambda: gates)
    monkeypatch.setattr(
        product_verification,
        "_run_supervised_command",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout="release completed without proof",
            stderr="",
        ),
    )

    result = product_verification.run_gates({"release": ["AC-1"]})[0]

    assert result["status"] == "failed"
    assert result["result"]["exit_code"] == 0
    assert result["result"]["failure"]["kind"] == "subsumption-proof"


def test_risk_routes_derive_stable_gate_floor_from_committed_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        product_verification,
        "_configured_risk_routes",
        lambda: [
            {
                "id": "api",
                "prefixes": ["apps/api/"],
                "files": [],
                "required_gates": ["api-lint", "api-tests"],
            },
            {
                "id": "harness-docs",
                "prefixes": ["harness/docs/"],
                "files": ["README.md"],
                "required_gates": ["harness-integrity"],
            },
            {
                "id": "release-control",
                "prefixes": ["harness/tools/"],
                "files": ["package-lock.json"],
                "required_gates": ["release", "api-tests"],
            },
        ],
    )
    monkeypatch.setattr(
        product_verification,
        "implementation_paths",
        lambda _: [
            "README.md",
            "apps/api/app/main.py",
            "harness/tools/harness.py",
            "package-lock.json",
        ],
    )

    derived = product_verification.derived_gate_requirements(TASK_ID)

    assert derived["required_gates"] == [
        "api-lint",
        "api-tests",
        "harness-integrity",
        "release",
    ]
    assert [route["id"] for route in derived["routes"]] == [
        "api",
        "harness-docs",
        "release-control",
    ]
    assert derived["routes"][0]["matched_paths"] == ["apps/api/app/main.py"]
    assert derived["routes"][1]["matched_paths"] == ["README.md"]


def test_risk_derived_gates_cannot_be_removed_by_profile_or_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        product_verification,
        "_configured_gates",
        lambda: {"api-tests": {}, "release": {}},
    )
    monkeypatch.setattr(
        product_verification,
        "_configured_profiles",
        lambda: {"focused": {"required_gates": []}},
    )
    monkeypatch.setattr(
        product_verification,
        "derived_gate_requirements",
        lambda _: {
            "paths": ["harness/tools/harness.py"],
            "routes": [
                {
                    "id": "release-control",
                    "matched_paths": ["harness/tools/harness.py"],
                    "required_gates": ["release"],
                }
            ],
            "required_gates": ["release"],
        },
    )

    with pytest.raises(
        product_verification.ProductVerificationError,
        match=(
            "risk-derived verification requires gates: release; "
            "triggered by harness/tools/harness.py"
        ),
    ):
        product_verification.validate_configured_gates(
            {"api-tests": ["AC-1"]},
            "focused",
            TASK_ID,
        )

    product_verification.validate_configured_gates(
        {"api-tests": ["AC-1"], "release": ["AC-1"]},
        "focused",
        TASK_ID,
    )


def test_risk_route_configuration_rejects_unknown_gate_and_unsafe_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        product_verification,
        "_configured_gates",
        lambda: {"release": {}},
    )
    config = {
        "verification": {
            "risk_routes": [
                {
                    "id": "unsafe",
                    "prefixes": ["../outside/"],
                    "files": [],
                    "required_gates": ["missing"],
                }
            ]
        }
    }
    monkeypatch.setattr(product_verification, "load_config", lambda: config)

    with pytest.raises(
        product_verification.ProductVerificationError,
        match="invalid project-relative prefix",
    ):
        product_verification._configured_risk_routes()

    config["verification"]["risk_routes"][0]["prefixes"] = ["apps/"]
    with pytest.raises(
        product_verification.ProductVerificationError,
        match="uses unregistered gates: missing",
    ):
        product_verification._configured_risk_routes()


def test_implementation_paths_start_after_spec_introduction_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        product_verification,
        "_spec_introduction_commit",
        lambda _: "baseline",
    )

    def git_value(*args: str) -> str:
        calls.append(args)
        return "apps/web/app.vue\0harness/tools/harness.py\0"

    monkeypatch.setattr(product_verification, "_git_value", git_value)

    assert product_verification.implementation_paths(TASK_ID) == [
        "apps/web/app.vue",
        "harness/tools/harness.py",
    ]
    assert calls == [("diff", "--name-only", "-z", "baseline..HEAD")]


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
    derived = {
        "paths": ["apps/api/app/main.py"],
        "routes": [
            {
                "id": "api",
                "matched_paths": ["apps/api/app/main.py"],
                "required_gates": ["harness-tests"],
            }
        ],
        "required_gates": ["harness-tests"],
    }
    monkeypatch.setattr(
        product_verification,
        "derived_gate_requirements",
        lambda _: derived,
    )
    monkeypatch.setattr(product_verification, "_git_value", lambda *_: "tree-one")
    criteria = ["AC-1", "AC-2"]
    mappings = {"harness-tests": criteria}
    documentation = {
        "impact": "none",
        "reason": "Fixture only.",
        "targets": [],
        "baseline_commit": None,
        "target_blobs": {},
    }

    first = product_verification.evidence_fingerprints(
        TASK_ID,
        criteria,
        mappings,
        "focused",
        documentation,
    )
    spec.write_text(spec.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    second = product_verification.evidence_fingerprints(
        TASK_ID,
        criteria,
        mappings,
        "focused",
        documentation,
    )
    gate_config["harness-tests"]["command"].append("-q")
    third = product_verification.evidence_fingerprints(
        TASK_ID,
        criteria,
        mappings,
        "focused",
        documentation,
    )
    changed_documentation = {
        **documentation,
        "target_blobs": {"README.md": "new-blob"},
    }
    fourth = product_verification.evidence_fingerprints(
        TASK_ID,
        criteria,
        mappings,
        "focused",
        changed_documentation,
    )
    derived["paths"] = ["apps/api/app/changed.py"]
    fifth = product_verification.evidence_fingerprints(
        TASK_ID,
        criteria,
        mappings,
        "focused",
        changed_documentation,
    )
    verification_cases = {
        "schema_version": 1,
        "contract_id": "fixture-v1",
        "contract_sha256": "d" * 64,
        "criteria": [],
    }
    sixth = product_verification.evidence_fingerprints(
        TASK_ID,
        criteria,
        mappings,
        "focused",
        changed_documentation,
        verification_cases,
    )

    assert first["source_tree"] == "tree-one"
    assert first["active_spec_sha256"] != second["active_spec_sha256"]
    assert second["gate_config_sha256"] != third["gate_config_sha256"]
    assert (
        third["documentation_targets_sha256"]
        != fourth["documentation_targets_sha256"]
    )
    assert fourth["gate_config_sha256"] != fifth["gate_config_sha256"]
    assert sixth["module_contract_sha256"] == "d" * 64
    assert (
        fifth["verification_contract_sha256"]
        != sixth["verification_contract_sha256"]
    )


def test_live_risk_routes_rightsize_harness_docs_control_and_release() -> None:
    config = product_verification.load_config()["verification"]
    assert "risk_routes" not in config
    assert config["impact"]["reuse"] is False
    assert config["profiles"]["focused"]["required_gates"] == []
    assert config["profiles"]["release"]["required_gates"] == ["release"]


def test_bundle_gate_cannot_be_the_only_mapping_for_multiple_criteria(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        product_verification,
        "_configured_gates",
        lambda: {
            "release": {"subsumption_contract": "scripts/release-stage-contract.json"},
            "harness-tests": {},
        },
    )
    with pytest.raises(
        product_verification.ProductVerificationError,
        match="bundle gates cannot be the only mapping",
    ):
        product_verification.validate_mapping_policy(
            ["AC-1", "AC-2"],
            {"release": ["AC-1", "AC-2"]},
        )

    product_verification.validate_mapping_policy(
        ["AC-1"],
        {"release": ["AC-1"]},
    )
    product_verification.validate_mapping_policy(
        ["AC-1", "AC-2"],
        {"harness-tests": ["AC-1", "AC-2"], "release": ["AC-2"]},
    )


def test_extra_bundle_gate_requires_verification_escalation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _write_spec(tmp_path / f"{TASK_ID}.md")
    monkeypatch.setattr(product_verification, "active_spec", lambda _: spec)
    monkeypatch.setattr(
        product_verification,
        "_configured_gates",
        lambda: {
            "release": {"subsumption_contract": "scripts/release-stage-contract.json"},
            "harness-tests": {},
        },
    )
    monkeypatch.setattr(
        product_verification,
        "derived_gate_requirements",
        lambda _: {
            "paths": ["harness/tools/telemetry.py"],
            "routes": [
                {
                    "id": "harness-control",
                    "matched_paths": ["harness/tools/telemetry.py"],
                    "required_gates": ["harness-tests", "harness-integrity"],
                }
            ],
            "required_gates": ["harness-tests", "harness-integrity"],
        },
    )

    with pytest.raises(
        product_verification.ProductVerificationError,
        match="requires verification_escalation: release",
    ):
        product_verification.validate_mapping_policy(
            ["AC-1", "AC-2"],
            {"harness-tests": ["AC-1", "AC-2"], "release": ["AC-1"]},
            task_id=TASK_ID,
        )

    spec.write_text(
        spec.read_text(encoding="utf-8").replace(
            "verification_profile: focused\n",
            "verification_profile: focused\n"
            "verification_escalation: Need the full release owner for CI proof.\n",
        ),
        encoding="utf-8",
    )
    product_verification.validate_mapping_policy(
        ["AC-1", "AC-2"],
        {"harness-tests": ["AC-1", "AC-2"], "release": ["AC-1"]},
        task_id=TASK_ID,
    )


def test_spec_lint_reuses_contract_checks_without_product_gates(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[str] = []

    def lint(task_id: str) -> tuple[list[str], dict[str, list[str]], str]:
        calls.append(task_id)
        return ["AC-1"], {"harness-tests": ["AC-1"]}, "focused"

    monkeypatch.setattr(harness_cli.summarizer, "validate_task_id", lambda _: None)
    monkeypatch.setattr(product_verification, "lint_task_contract", lint)
    monkeypatch.setattr(
        harness_cli.isolated_verification,
        "run_in_worktree",
        lambda *_: (_ for _ in ()).throw(AssertionError("spec-lint must not run gates")),
    )

    exit_code = harness_cli.command_spec_lint(
        type("Args", (), {"task_id": TASK_ID})()
    )

    assert exit_code == 0
    assert calls == [TASK_ID]
    assert "PASSED" in capsys.readouterr().out
