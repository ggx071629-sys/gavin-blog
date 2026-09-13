from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path

import pytest

from harness.tools.qualification import (
    QualificationError,
    _case_suite,
    sign_manifest,
    verify_manifest,
)

RSA_N = (
    "nhZPwcMUZoA7dJR36ZmrKThaUhhjgROWktATDVeg9h1WH5O8dqehXOwX5a2Gu1UN23buVXMKoSLB"
    "gqp4Dx882HKT5fqoSK0eOH2P_AgwTwK03Xg_7YjNAak0SlQ2VO9lpD7qJJjM6yrKpDzWWq3cbvVa"
    "goYOJZqoqcblgtRGNI0QyFN3ADHw4LSOuSL6NtI2IZ4GB4Lfj-FiNsWFp0jmQRoz7_XwGri-ghfhc"
    "ldEr6WT03DCSLOYzFbCdIZ5WqOmbP1UZtZWlJpEkQ12QngmUKcnyhUXlUt-Q9uAAUvzicMqhs01i7"
    "6sxpxRWUkkUdJSkZ14BnnoZyzW8xDAgCE2cWpCXDS3YHcJYG2OJYcxu9vlCeOLLv0rY8zDkkCFPkz"
    "jTvkyJwkBPBlgN38526zMuWThR7IwxPjw5qSlzglIqswCMGjTXRO7BYKBGGYPauqDLNOlEu7HRfqwb"
    "dyfatZ5jyhdLXqVp3dlzlmM3KgkEMIapMaYzvId-kkvdr8ivbGr"
)
RSA_D = (
    "Au7Msv5grK14rOcrjwC5Uq3yIFobJSQNDpM1T0bkEbzQl2G2b4huRMWNL0cisUCuMvdIC6Yd4927s6"
    "YK99OEsvVJNiKKKF2sf7Agpt8rWkPlbBhqLd4fA4a1QCMY0PGSCVPbedYAiI-w1mQvNoZ0M6DHTurt"
    "bJgrxIk6l8yYCCs3zPzzamRYINW-B27qhRrYQz5lw-eTKIhYufBnKYfU3GSqjatFNZGzgxat_uDh7C"
    "pJDZ_8Erzg5aWUZ59ZCqvvh9ipCO5-36k74Jhn7FmCgjSgXERx9Dzd6lLZxop8M45gZ8QzD-TWRzB"
    "P5yt9bM8-YrlVCxBUeA5buxXG3jbLjXsWx2JM8D3u1dKAr8ojt0bOPkPcuJA_ptZkZALSfsaMOwCY8"
    "8tPhEQdKCLX8pUqBXZ8WmHwzoWlsSR8LfoPeHG3O-Zi3BsW7f8ctMxVwKaDyQlEKhcfz7g8jg9vos"
    "pSYDaQI9pt_OOYLXvKZRaxd067PsCEV75gPTtHh-gJEgX5"
)
HASH = "sha256:" + "a" * 64
CASE_CATEGORIES = (
    "profile",
    "deployment",
    "provider",
    "security",
    "streaming",
    "retrieval",
    "qdrant",
    "backup_restore",
    "saver",
    "resource",
    "conformance",
    "observability",
    "dark_launch",
)
RESULT_SECTIONS = (
    "profile_validation",
    "deployment",
    "provider_contract",
    "tls_proxy",
    "qdrant",
    "backup_restore",
    "saver",
    "resources",
    "conformance",
    "observability",
    "dark_launch",
)
INVALIDATION_PATHS = (
    "source_commit",
    "artifact_digest",
    "profile_digest",
    "case_suite_digest",
    "provider_contract",
    "model_identity",
    "provider_pricing",
    "active_generation",
    "tls_proxy_contract",
    "qdrant_contract",
    "secret_rotation",
    "qualification_trust_policy",
)


def _private_key() -> dict:
    return {
        "schema_version": 1,
        "key_id": "qualification-test-2026",
        "algorithm": "rsa-sha256-pkcs1-v1_5",
        "n": RSA_N,
        "e": 65537,
        "d": RSA_D,
    }


def _public_keys() -> dict:
    return {
        "schema_version": 1,
        "keys": [
            {
                "key_id": "qualification-test-2026",
                "algorithm": "rsa-sha256-pkcs1-v1_5",
                "n": RSA_N,
                "e": 65537,
                "not_before": "2026-08-01T00:00:00Z",
                "not_after": "2027-08-01T00:00:00Z",
            }
        ],
    }


def _unsigned_manifest() -> dict:
    cases = [
        {
            "case_id": f"QA-CASE-{index:02d}",
            "suite_version": "1.0.0",
            "status": "pass",
            "category": CASE_CATEGORIES[(index - 1) % len(CASE_CATEGORIES)],
            "classification": "deterministic" if index % 2 else "measured",
            "reviewer": "Gavin",
            "reviewed_at": "2026-08-30T10:30:00Z",
            "artifact_hashes": [HASH],
        }
        for index in range(1, 31)
    ]
    return {
        "schema_version": 1,
        "task_id": "20260830-public-qa-production-qualification",
        "qualification_state": "QUALIFICATION_GO_CANDIDATE",
        "source_commit": "b" * 40,
        "artifact_digest": HASH,
        "profile_digest": "sha256:" + "b" * 64,
        "case_suite_digest": "sha256:" + "c" * 64,
        "started_at": "2026-08-30T09:00:00Z",
        "completed_at": "2026-08-30T11:00:00Z",
        "expires_at": "2026-09-01T11:00:00Z",
        "invalidation_paths": list(INVALIDATION_PATHS),
        "target": {
            "real_target": True,
            "cpu_cores": 2,
            "memory_mib": 4096,
            "os_name": "Ubuntu Server",
            "os_version": "24.04.1",
            "architecture": "x86_64",
            "filesystem": "ext4",
            "deployment_kind": "systemd",
            "host_class": "approved-production-host",
        },
        "provider": {
            "real_provider": True,
            "chat": {
                "provider": "selected-chat-provider",
                "model": "selected-chat-model",
                "version": "2026-08-01",
                "model_identity_source": "provider-response",
                "input_price_micro_cny_per_million": 100_000,
                "output_price_micro_cny_per_million": 400_000,
                "reports_usage": True,
                "reports_finish_reason": True,
            },
            "embedding": {
                "provider": "selected-embedding-provider",
                "model": "selected-embedding-model",
                "version": "2026-08-01",
                "model_identity_source": "versioned-provider-contract",
                "dimension": 1536,
                "input_price_micro_cny_per_million": 20_000,
                "reports_usage": True,
            },
        },
        "active_generation": {
            "id": 42,
            "collection": "gavin_assistant_active",
            "dimension": 1536,
            "distance": "Cosine",
            "pipeline_version": "assistant-index-v1",
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
            "chat_calls": 30,
            "query_embedding_calls": 5,
            "index_embedding_calls": 2,
            "total_micro_cny": 1_000_000,
            "max_calls": 40,
            "max_micro_cny": 2_000_000,
            "within_envelope": True,
        },
        "results": {
            name: {
                "status": "pass",
                "case_ids": [cases[index % len(cases)]["case_id"]],
                "summary": f"Measured {name} contract satisfied its approved threshold.",
            }
            for index, name in enumerate(RESULT_SECTIONS)
        },
        "cases": cases,
        "artifacts": [
            {
                "artifact_id": "target-run-log",
                "kind": "sanitized-target-run",
                "sha256": HASH,
                "location_category": "encrypted-off-host-object-store",
                "retention_days": 30,
                "reviewed": True,
            }
        ],
        "operator": {
            "reviewer": "Gavin",
            "reviewed_at": "2026-08-30T11:10:00Z",
            "decision_reason": "All required qualification cases passed on the approved target.",
            "residual_risks": ["Single-host recovery is not high availability."],
            "remediation_tasks": [],
        },
    }


def _signed_manifest() -> dict:
    return sign_manifest(_unsigned_manifest(), _private_key())


def test_signed_go_manifest_verifies_and_binds_complete_case_suite() -> None:
    manifest = _signed_manifest()
    facts = verify_manifest(
        manifest,
        _public_keys(),
        expected_task_id=manifest["task_id"],
        expected_profile_digest=manifest["profile_digest"],
        expected_case_suite_digest=manifest["case_suite_digest"],
        expected_case_ids={case["case_id"] for case in manifest["cases"]},
        active=True,
        now=datetime(2026, 8, 31, tzinfo=timezone.utc),
    )
    assert facts["state"] == "QUALIFICATION_GO_CANDIDATE"
    assert len(facts["case_ids"]) == 30


def test_signed_no_go_allows_direct_blockers_but_not_unknown_or_blocker_chains() -> None:
    unsigned = _unsigned_manifest()
    unsigned["qualification_state"] = "QUALIFICATION_NO_GO"
    unsigned["cases"][2]["status"] = "measured_fail"
    unsigned["cases"][1]["status"] = "blocked_by:QA-CASE-03"
    unsigned["results"]["provider_contract"]["status"] = "measured_fail"
    unsigned["results"]["provider_contract"]["case_ids"] = ["QA-CASE-03"]
    unsigned["results"]["deployment"]["status"] = "blocked_by:QA-CASE-03"
    unsigned["results"]["deployment"]["case_ids"] = ["QA-CASE-02", "QA-CASE-03"]
    unsigned["operator"]["remediation_tasks"] = ["20260901-provider-usage-remediation"]
    unsigned["operator"]["decision_reason"] = (
        "Measured provider failure blocks deployment qualification."
    )
    manifest = sign_manifest(unsigned, _private_key())
    assert verify_manifest(
        manifest,
        _public_keys(),
        active=True,
        now=datetime(2026, 8, 31, tzinfo=timezone.utc),
    )["state"] == "QUALIFICATION_NO_GO"

    chained = copy.deepcopy(unsigned)
    chained["cases"][3]["status"] = "blocked_by:QA-CASE-02"
    with pytest.raises(QualificationError, match="directly by a measured_fail"):
        sign_manifest(chained, _private_key())

    unknown = copy.deepcopy(unsigned)
    unknown["cases"][3]["status"] = "unknown"
    with pytest.raises(QualificationError, match="cannot be unknown"):
        sign_manifest(unknown, _private_key())


def test_signature_detects_tampering_and_unpinned_keys() -> None:
    manifest = _signed_manifest()
    tampered = copy.deepcopy(manifest)
    tampered["results"]["profile_validation"]["summary"] += " Tampered."
    with pytest.raises(QualificationError, match="signature verification"):
        verify_manifest(tampered, _public_keys(), active=False)

    keys = _public_keys()
    keys["keys"][0]["key_id"] = "different-key"
    with pytest.raises(QualificationError, match="not pinned"):
        verify_manifest(manifest, keys, active=False)


def test_expiry_is_enforced_only_for_active_qualification_authorization() -> None:
    manifest = _signed_manifest()
    after_expiry = datetime(2026, 9, 2, tzinfo=timezone.utc)
    with pytest.raises(QualificationError, match="stale"):
        verify_manifest(manifest, _public_keys(), active=True, now=after_expiry)
    assert verify_manifest(
        manifest, _public_keys(), active=False, now=after_expiry
    )["state"] == "QUALIFICATION_GO_CANDIDATE"


def test_profile_case_and_target_bindings_cannot_drift() -> None:
    manifest = _signed_manifest()
    with pytest.raises(QualificationError, match="profile digest"):
        verify_manifest(
            manifest,
            _public_keys(),
            expected_profile_digest="sha256:" + "d" * 64,
            active=False,
        )
    with pytest.raises(QualificationError, match="exactly match"):
        verify_manifest(
            manifest,
            _public_keys(),
            expected_case_ids={"QA-CASE-01"},
            active=False,
        )


def test_repository_case_suite_is_versioned_complete_and_acyclic() -> None:
    suite = (
        Path(__file__).resolve().parents[1]
        / "qualification-cases"
        / "public-qa-conformance-v1.json"
    )
    digest, contracts = _case_suite(suite)
    assert digest.startswith("sha256:")
    assert len(contracts) == 47
    assert sum(case_id.startswith("QA-CONF-") for case_id in contracts) == 32
    assert contracts["QA-CONF-018"] == {
        "suite_version": "1.0.0",
        "category": "provider",
        "classification": "measured",
    }


def test_unproven_provider_facts_cannot_receive_a_go_classification() -> None:
    unsigned = _unsigned_manifest()
    unsigned["provider"]["embedding"]["reports_usage"] = False
    with pytest.raises(QualificationError, match="requires provider_contract failure"):
        sign_manifest(unsigned, _private_key())

    unsigned["qualification_state"] = "QUALIFICATION_NO_GO"
    unsigned["cases"][2]["status"] = "measured_fail"
    unsigned["results"]["provider_contract"] = {
        "status": "measured_fail",
        "case_ids": ["QA-CASE-03"],
        "summary": "Provider usage could not be proven from the measured response.",
    }
    unsigned["operator"]["remediation_tasks"] = ["20260901-provider-usage-remediation"]
    assert sign_manifest(unsigned, _private_key())["qualification_state"] == (
        "QUALIFICATION_NO_GO"
    )
