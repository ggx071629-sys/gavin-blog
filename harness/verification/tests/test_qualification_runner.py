from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from harness.tools import qualification, qualification_runner
from harness.tools.qualification_runner import QualificationRunnerError


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _inputs(tmp_path: Path, monkeypatch) -> tuple[Path, Path, dict]:
    from tests.test_assistant_qualification_profile import valid_profile_data

    profile_data = valid_profile_data()
    profile_data["storage"]["paths"]["qualification_root"] = str(
        (tmp_path / "qualification").resolve()
    )
    profile_path = tmp_path / "profile.json"
    _write_json(profile_path, profile_data)
    suite_path = (
        Path(__file__).resolve().parents[1]
        / "qualification-cases"
        / "public-qa-conformance-v1.json"
    )
    monkeypatch.setattr(
        qualification_runner,
        "_configured_inputs",
        lambda _task_id: (profile_path, suite_path),
    )
    return profile_path, suite_path, profile_data


def _initialize(tmp_path: Path, monkeypatch) -> tuple[Path, Path, dict]:
    _, suite_path, profile_data = _inputs(tmp_path, monkeypatch)
    artifact = tmp_path / "deployment-artifact.json"
    artifact.write_text('{"digest":"immutable"}', encoding="utf-8")
    workspace = tmp_path / "qualification" / "run-1"
    observation = {
        "observed_at": "2026-08-30T09:00:00+00:00",
        "effective_cpu_cores": 2,
        "effective_memory_bytes": 4_294_967_296,
        "os_name": "Ubuntu Server",
        "os_version": "24.04.1",
        "architecture": "x86_64",
        "filesystems": {"content_sqlite": "ext4"},
        "network_filesystem_detected": False,
        "host_identifier_retained": False,
        "ip_address_retained": False,
    }
    qualification_runner.initialize_run(
        task_id="20260830-public-qa-production-qualification",
        artifact_path=artifact,
        workspace=workspace,
        now=datetime(2026, 8, 30, 9, 0, tzinfo=UTC),
        source_commit="b" * 40,
        require_clean=False,
        target_observation=observation,
    )
    return workspace, suite_path, profile_data


def _record_all(
    tmp_path: Path,
    workspace: Path,
    suite_path: Path,
) -> list[dict]:
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    raw_artifact = tmp_path / "off-host-evidence.json"
    raw_artifact.write_text('{"reviewed":"sanitized"}', encoding="utf-8")
    for index, case in enumerate(suite["cases"], start=1):
        observation = {
            "schema_version": 1,
            "case_id": case["case_id"],
            "status": "pass",
            "reviewer": "Gavin",
            "reviewed_at": (
                datetime(2026, 8, 30, 9, 0, tzinfo=UTC) + timedelta(minutes=index)
            ).isoformat(),
            "artifact_records": [
                {
                    "artifact_id": "sanitized-target-run",
                    "kind": "sanitized-target-qualification",
                    "path": str(raw_artifact),
                    "location_category": "encrypted-off-host-filesystem",
                    "retention_days": 30,
                    "reviewed": True,
                }
            ],
        }
        observation_path = tmp_path / "observations" / f"{case['case_id']}.json"
        _write_json(observation_path, observation)
        qualification_runner.record_case(
            workspace=workspace,
            observation_path=observation_path,
            enforce_source=False,
        )
    return suite["cases"]


def _summary(profile: dict, cases: list[dict]) -> dict:
    result_sections = sorted(qualification.REQUIRED_RESULT_SECTIONS)
    return {
        "schema_version": 1,
        "completed_at": "2026-08-30T11:00:00+00:00",
        "provider": {
            "real_provider": True,
            "chat": {
                "provider": profile["providers"]["chat"]["provider"],
                "model": profile["providers"]["chat"]["model"],
                "version": profile["providers"]["chat"]["model_version"],
                "model_identity_source": "versioned-provider-contract",
                "input_price_micro_cny_per_million": profile["providers"]["chat"][
                    "input_price_micro_cny_per_million"
                ],
                "output_price_micro_cny_per_million": profile["providers"]["chat"][
                    "output_price_micro_cny_per_million"
                ],
                "reports_usage": True,
                "reports_finish_reason": True,
            },
            "embedding": {
                "provider": profile["providers"]["embedding"]["provider"],
                "model": profile["providers"]["embedding"]["model"],
                "version": profile["providers"]["embedding"]["model_version"],
                "model_identity_source": "versioned-provider-contract",
                "dimension": profile["providers"]["embedding"]["dimension"],
                "input_price_micro_cny_per_million": profile["providers"][
                    "embedding"
                ]["input_price_micro_cny_per_million"],
                "reports_usage": True,
            },
        },
        "active_generation": {
            "id": 42,
            "collection": f'{profile["qdrant"]["collection_prefix"]}_42',
            "dimension": profile["qdrant"]["vector_dimension"],
            "distance": profile["qdrant"]["distance"],
            "pipeline_version": profile["qdrant"]["pipeline_version"],
        },
        "switches": {
            "before": {
                "web_launcher": False,
                "api_capability": False,
                "runtime_gate": False,
            },
            "canary": {"edge_restricted": True, "administrator_enabled": True},
            "after": {
                "web_launcher": False,
                "api_capability": False,
                "runtime_gate": False,
            },
            "runner_auto_enabled": False,
        },
        "qualification_usage": {
            "beijing_dates": ["2026-08-30"],
            "chat_calls": 20,
            "query_embedding_calls": 5,
            "index_embedding_calls": 2,
            "total_micro_cny": 1_000_000,
            "max_calls": profile["providers"]["budgets"]["qualification_max_calls"],
            "max_micro_cny": profile["providers"]["budgets"][
                "qualification_max_micro_cny"
            ],
            "within_envelope": True,
        },
        "results": {
            section: {
                "status": "pass",
                "case_ids": [cases[index]["case_id"]],
                "summary": f"Measured {section} satisfied its approved target contract.",
            }
            for index, section in enumerate(result_sections)
        },
        "operator": {
            "reviewer": "Gavin",
            "reviewed_at": "2026-08-30T11:10:00+00:00",
            "decision_reason": "All required target qualification cases passed review.",
            "residual_risks": ["Single-host recovery is not high availability."],
            "remediation_tasks": [],
        },
    }


def test_initialize_is_zero_call_and_binds_target_artifact_and_inputs(
    tmp_path: Path, monkeypatch
) -> None:
    workspace, suite_path, _ = _initialize(tmp_path, monkeypatch)
    run = json.loads((workspace / "run.json").read_text(encoding="utf-8"))
    assert run["status"] == "collecting"
    assert run["source_commit"] == "b" * 40
    assert run["artifact_digest"].startswith("sha256:")
    assert run["case_suite_digest"] == qualification._case_suite(suite_path)[0]
    assert list((workspace / "cases").glob("*.json")) == []


def test_case_recording_requires_dependency_order_and_is_append_only(
    tmp_path: Path, monkeypatch
) -> None:
    workspace, suite_path, _ = _initialize(tmp_path, monkeypatch)
    suite = json.loads(suite_path.read_text(encoding="utf-8"))["cases"]
    dependent = next(case for case in suite if case["depends_on"])
    raw_artifact = tmp_path / "evidence.json"
    raw_artifact.write_text("{}", encoding="utf-8")
    observation = {
        "schema_version": 1,
        "case_id": dependent["case_id"],
        "status": "pass",
        "reviewer": "Gavin",
        "reviewed_at": "2026-08-30T09:10:00+00:00",
        "artifact_records": [
            {
                "artifact_id": "target-log",
                "kind": "sanitized-log",
                "path": str(raw_artifact),
                "location_category": "encrypted-off-host-filesystem",
                "retention_days": 30,
                "reviewed": True,
            }
        ],
    }
    observation_path = tmp_path / "dependent.json"
    _write_json(observation_path, observation)
    with pytest.raises(QualificationRunnerError, match="dependencies are not yet recorded"):
        qualification_runner.record_case(
            workspace=workspace,
            observation_path=observation_path,
            enforce_source=False,
        )


def test_complete_reviewed_cases_assemble_a_valid_unsigned_manifest(
    tmp_path: Path, monkeypatch
) -> None:
    workspace, suite_path, profile = _initialize(tmp_path, monkeypatch)
    cases = _record_all(tmp_path, workspace, suite_path)
    summary_path = tmp_path / "summary.json"
    _write_json(summary_path, _summary(profile, cases))
    output = tmp_path / "unsigned.json"
    qualification_runner.assemble_manifest(
        workspace=workspace,
        summary_path=summary_path,
        output_path=output,
        enforce_source=False,
    )
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["qualification_state"] == "QUALIFICATION_GO_CANDIDATE"
    assert len(manifest["cases"]) == 47
    assert len(manifest["artifacts"]) == 1
    facts = qualification._validate_manifest_structure(
        {
            **manifest,
            "signature": {
                "key_id": "unsigned-target-run",
                "algorithm": qualification.ALGORITHM,
                "value": "AA",
            },
        }
    )
    assert facts["state"] == "QUALIFICATION_GO_CANDIDATE"


def test_manifest_assembly_refuses_incomplete_cases(tmp_path: Path, monkeypatch) -> None:
    workspace, suite_path, profile = _initialize(tmp_path, monkeypatch)
    cases = json.loads(suite_path.read_text(encoding="utf-8"))["cases"]
    summary_path = tmp_path / "summary.json"
    _write_json(summary_path, _summary(profile, cases))
    with pytest.raises(QualificationRunnerError, match="cases are incomplete"):
        qualification_runner.assemble_manifest(
            workspace=workspace,
            summary_path=summary_path,
            output_path=tmp_path / "unsigned.json",
            enforce_source=False,
        )
