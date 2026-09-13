from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.assistant_qualification.cli import main
from app.assistant_qualification.profile import (
    REQUIRED_INVALIDATION_PATHS,
    REQUIRED_SOAK_SCENARIOS,
    QualificationProfile,
    canonical_profile,
    load_profile,
    profile_digest,
)


def _artifact(version: str, marker: str) -> dict:
    return {
        "version": version,
        "digest": f"sha256:{marker * 64}",
        "source": f"registry/gavin/{marker}",
    }


def _approval(reason: str) -> dict:
    return {
        "approved": True,
        "approved_by": "Gavin",
        "approved_at": "2026-08-30T09:00:00+08:00",
        "rationale": reason,
    }


def _secret(reference: str) -> dict:
    return {
        "kind": "environment",
        "reference": reference,
        "rotation_interval_days": 90,
        "rotation_procedure": "Disable the assistant, rotate this credential, and requalify.",
    }


def valid_profile_data() -> dict:
    service = {
        "os_user": "gavin-app",
        "bind_address": "127.0.0.1",
        "replicas": 1,
        "graceful_shutdown_seconds": 30,
        "restart_policy": "on-failure",
    }
    return {
        "schema_version": 2,
        "profile_id": "20260830-public-qa-production-qualification",
        "profile_revision": 1,
        "approval": _approval(
            "Approve this exact non-secret profile before deployment or provider calls."
        ),
        "safety": {
            "web_launcher_enabled": False,
            "api_capability_enabled": False,
            "runtime_gate_enabled": False,
            "destructive_tests_use_isolation": True,
        },
        "host": {
            "os_name": "Ubuntu Server",
            "os_version": "24.04.1",
            "architecture": "x86_64",
            "deployment_kind": "systemd",
            "cpu_cores": 2,
            "memory_mib": 4096,
            "filesystem_type": "ext4",
            "disk_capacity_mib": 65_536,
            "approved_disk_watermark_percent": 80,
            "ntp_service": "systemd-timesyncd",
            "max_clock_drift_seconds": 5,
        },
        "services": {
            "web": {
                **service,
                "artifact": _artifact("1.0.0", "a"),
                "port": 3000,
                "startup_order": 4,
                "health_path": "/",
            },
            "api": {
                **service,
                "artifact": _artifact("1.0.0", "b"),
                "port": 8000,
                "startup_order": 3,
                "health_path": "/api/health",
            },
            "index_worker": {
                **service,
                "artifact": _artifact("1.0.0", "c"),
                "port": 8001,
                "startup_order": 2,
                "health_path": None,
            },
            "qdrant": {
                **service,
                "artifact": _artifact("1.15.4", "d"),
                "os_user": "qdrant",
                "port": 6333,
                "startup_order": 1,
                "health_path": "/healthz",
            },
        },
        "edge": {
            "product": _artifact("1.28.0", "e"),
            "kind": "reverse-proxy",
            "domain": "blog.gavinchou.dev",
            "canonical_origin": "https://blog.gavinchou.dev",
            "public_ports": [80, 443],
            "trusted_proxy_cidrs": ["127.0.0.0/8"],
            "client_ip_header": "X-Gavin-Client-IP",
            "tls_minimum_version": "1.3",
            "hsts_max_age_seconds": 31_536_000,
            "idle_timeout_seconds": 300,
            "request_timeout_seconds": 300,
            "heartbeat_interval_seconds": 15,
            "strips_untrusted_forwarding_headers": True,
            "sse_buffering_disabled": True,
            "csp": {
                "mode": "report-only-risk-accepted",
                "risk_expires_at": "2026-10-30T09:00:00+08:00",
                "remediation_reference": "decision:public-assistant-csp-enforcement",
            },
        },
        "storage": {
            "media_backend": "local",
            "persistent_local_filesystem": True,
            "paths": {
                "content_sqlite": "/srv/gavin/content/gavin.db",
                "content_write_fence": "/srv/gavin/content/gavin.write-fence.lock",
                "assistant_runtime": "/srv/gavin/runtime/assistant.db",
                "media_root": "/srv/gavin/media",
                "qdrant_volume": "/srv/gavin/qdrant",
                "qualification_root": "/srv/gavin/qualification",
                "rollback_root": "/srv/gavin/rollback",
            },
            "content_peak_mib": 2048,
            "media_peak_mib": 8192,
            "runtime_peak_mib": 512,
            "qdrant_peak_mib": 8192,
            "rebuild_peak_extra_mib": 8192,
            "backup_staging_mib": 8192,
            "rollback_reserve_mib": 8192,
        },
        "secrets": {
            "administrator_password": _secret("GAVIN_ADMIN_PASSWORD"),
            "session": _secret("GAVIN_ASSISTANT_SESSION_HMAC_SECRET"),
            "csrf": _secret("GAVIN_ASSISTANT_CSRF_HMAC_SECRET"),
            "assistant_ip_hmac": _secret("GAVIN_ASSISTANT_IP_HMAC_SECRET"),
            "proxy_identity_hmac": _secret("GAVIN_ASSISTANT_PROXY_HMAC_SECRET"),
            "readiness": _secret("GAVIN_ASSISTANT_READINESS_HMAC_SECRET"),
            "qualification_signing": _secret("GAVIN_QUALIFICATION_SIGNING_KEY"),
            "chat_api_key": _secret("GAVIN_ASSISTANT_CHAT_API_KEY"),
            "embedding_api_key": _secret("GAVIN_ASSISTANT_EMBEDDING_API_KEY"),
            "qdrant_api_key": _secret("GAVIN_ASSISTANT_QDRANT_API_KEY"),
            "backup_encryption": _secret("GAVIN_BACKUP_ENCRYPTION_KEY"),
        },
        "providers": {
            "chat": {
                "protocol": "openai-compatible",
                "provider": "selected-chat-provider",
                "endpoint": {
                    "scheme": "https",
                    "reference": "config:assistant-chat-endpoint",
                },
                "model": "selected-chat-model",
                "model_version": "2026-08-01",
                "model_identity_source": "versioned-provider-contract",
                "provider_contract_reference": "contract:chat-provider-2026-08-01",
                "timeout_seconds": 60,
                "max_concurrency": 3,
                "reports_usage": True,
                "max_input_tokens": 16_000,
                "max_output_tokens": 2_000,
                "context_window_tokens": 32_000,
                "reports_finish_reason": True,
                "input_price_micro_cny_per_million": 100_000,
                "output_price_micro_cny_per_million": 400_000,
            },
            "embedding": {
                "protocol": "openai-compatible",
                "provider": "selected-embedding-provider",
                "endpoint": {
                    "scheme": "https",
                    "reference": "config:assistant-embedding-endpoint",
                },
                "model": "selected-embedding-model",
                "model_version": "2026-08-01",
                "model_identity_source": "versioned-provider-contract",
                "provider_contract_reference": "contract:embedding-provider-2026-08-01",
                "timeout_seconds": 60,
                "max_concurrency": 4,
                "reports_usage": True,
                "dimension": 1536,
                "max_input_tokens": 8192,
                "max_batch_items": 64,
                "input_price_micro_cny_per_million": 20_000,
            },
            "budgets": {
                "chat_daily_micro_cny": 2_000_000,
                "query_embedding_daily_micro_cny": 500_000,
                "index_embedding_daily_micro_cny": 5_000_000,
                "qualification_max_calls": 40,
                "qualification_max_micro_cny": 2_000_000,
                "qualification_calls_approved": True,
                "beijing_budget_timezone": "Asia/Shanghai",
                "missing_usage_policy": "conservative-settlement-and-open-circuit",
            },
        },
        "qdrant": {
            "server": _artifact("1.15.4", "d"),
            "request_timeout_seconds": 30,
            "authentication_required": True,
            "tls_when_not_same_host": True,
            "collection_prefix": "gavin_assistant",
            "pipeline_version": "assistant-index-v1",
            "distance": "Cosine",
            "vector_dimension": 1536,
            "disk_watermark_percent": 75,
        },
        "backup": {
            "consistency_strategy": "write-fence-and-online-backup",
            "destination_reference": "backup:encrypted-off-host-primary",
            "outside_host_failure_domain": True,
            "encrypted": True,
            "frequency_seconds": 3600,
            "retention_count": 24,
            "rpo_seconds": 3600,
            "rto_seconds": 3600,
            "failure_alert_after_seconds": 7200,
            "runtime_excluded": True,
            "wal_shm_excluded": True,
            "langgraph_checkpoints_excluded": True,
        },
        "runner_timing": {
            "provider_timeout_seconds": 60,
            "cleanup_margin_seconds": 30,
            "settlement_margin_seconds": 30,
            "runner_horizon_seconds": 240,
        },
        "thresholds": {
            "approval": _approval(
                "Approve resource and latency thresholds before observing qualification results."
            ),
            "basis_reference": "capacity-plan:2vcpu-4gb-v1",
            "full_work_cycle_seconds": 3600,
            "soak_duration_seconds": 7200,
            "traffic_model": (
                "Two low-rate HR visitors plus one burst to three concurrent SSE turns."
            ),
            "scenarios": sorted(REQUIRED_SOAK_SCENARIOS),
            "max_total_rss_mib": 3072,
            "max_sustained_cpu_percent": 180,
            "max_swap_mib": 256,
            "max_file_descriptors": 2048,
            "max_disk_growth_mib_per_hour": 256,
            "max_qdrant_p95_ms": 500,
            "max_fts_p95_ms": 250,
            "max_graph_p50_ms": 20_000,
            "max_graph_p95_ms": 60_000,
            "max_process_restarts": 0,
        },
        "evidence": {
            "ttl_seconds": 172_800,
            "invalidation_paths": sorted(REQUIRED_INVALIDATION_PATHS),
            "raw_artifact_location_category": "encrypted-off-host-object-store",
            "raw_artifact_retention_days": 30,
            "reviewer_attests_hashes": True,
        },
        "observability": {
            "channels": [
                {
                    "kind": "email",
                    "reference": "alert:assistant-production",
                    "retention_days": 30,
                    "drill_observation_seconds": 300,
                }
            ],
            "backup_max_age_seconds": 7200,
            "tls_expiry_alert_days": 30,
            "worker_heartbeat_stale_seconds": 60,
            "log_retention_days": 14,
            "raw_questions_logged": False,
            "raw_answers_logged": False,
            "raw_ips_logged": False,
            "raw_provider_payloads_logged": False,
            "provider_account_budget_alert_configured": True,
        },
        "governance": {
            "data_retention_policy_reference": "policy:selected-provider-data-retention",
            "processing_region": "approved-provider-region",
            "visitor_disclosure_reference": "notice:public-assistant-provider-disclosure",
            "raw_langsmith_tracing_enabled": False,
        },
    }


def test_profile_is_strict_canonical_and_zero_call(tmp_path: Path, capsys) -> None:
    data = valid_profile_data()
    first = QualificationProfile.model_validate(data)
    reordered = {key: data[key] for key in reversed(data)}
    second = QualificationProfile.model_validate(reordered)

    assert profile_digest(first) == profile_digest(second)
    assert canonical_profile(first) == canonical_profile(second)

    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps(reordered), encoding="utf-8")
    assert load_profile(profile_path) == first
    assert main(["validate", str(profile_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["valid"] is True
    assert result["provider_calls"] == 0
    assert result["deployment_actions"] == 0
    assert set(result["switches"].values()) == {False}


@pytest.mark.parametrize(
    ("path", "value", "match"),
    [
        (("host", "os_version"), "latest", "placeholder"),
        (("services", "api", "artifact", "digest"), "sha256:abc", "digest"),
        (("edge", "domain"), "assistant.example.com", "example"),
        (("safety", "api_capability_enabled"), True, "False"),
        (("providers", "budgets", "chat_daily_micro_cny"), 1, "2000000"),
        (("storage", "media_backend"), "s3", "local"),
    ],
)
def test_profile_rejects_placeholders_floating_artifacts_and_unsafe_state(
    path: tuple[str, ...], value: object, match: str
) -> None:
    data = valid_profile_data()
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(ValidationError, match=match):
        QualificationProfile.model_validate(data)


def test_profile_rejects_unknown_fields_and_secret_values() -> None:
    data = valid_profile_data()
    data["secrets"]["readiness"]["value"] = "this-must-never-be-accepted"
    with pytest.raises(ValidationError, match="Extra inputs"):
        QualificationProfile.model_validate(data)


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (
            lambda data: data["runner_timing"].update(runner_horizon_seconds=100),
            "exceeds runner horizon",
        ),
        (
            lambda data: data["edge"].update(heartbeat_interval_seconds=300),
            "heartbeat interval",
        ),
        (
            lambda data: data["storage"].update(backup_staging_mib=50_000),
            "exceed disk watermark",
        ),
        (
            lambda data: data["thresholds"].update(soak_duration_seconds=1800),
            "complete approved work cycle",
        ),
        (
            lambda data: data["services"]["api"].update(bind_address="0.0.0.0"),
            "loopback or an approved private",
        ),
        (
            lambda data: data["qdrant"].update(vector_dimension=3072),
            "dimensions must match",
        ),
        (
            lambda data: data["providers"]["embedding"].update(timeout_seconds=30),
            "Embedding and runner provider timeout",
        ),
        (
            lambda data: data["qdrant"].update(
                server=_artifact("1.15.4", "f")
            ),
            "artifacts must be identical",
        ),
    ],
)
def test_profile_rejects_self_deceptive_cross_field_thresholds(mutate, match: str) -> None:
    data = valid_profile_data()
    mutate(data)
    with pytest.raises(ValidationError, match=match):
        QualificationProfile.model_validate(data)


def test_profile_rejects_missing_required_soak_or_invalidation_case() -> None:
    soak = valid_profile_data()
    soak["thresholds"]["scenarios"].remove("backup")
    with pytest.raises(ValidationError, match="soak scenarios missing"):
        QualificationProfile.model_validate(soak)

    invalidation = valid_profile_data()
    invalidation["evidence"]["invalidation_paths"].remove("provider_pricing")
    with pytest.raises(ValidationError, match="invalidation paths missing"):
        QualificationProfile.model_validate(invalidation)


def test_profile_digest_changes_for_relevant_drift() -> None:
    original = QualificationProfile.model_validate(valid_profile_data())
    changed_data = copy.deepcopy(valid_profile_data())
    changed_data["providers"]["chat"]["model_version"] = "2026-08-02"
    changed = QualificationProfile.model_validate(changed_data)
    assert profile_digest(original) != profile_digest(changed)
