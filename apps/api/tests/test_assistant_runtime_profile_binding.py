from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.assistant.constants import POLICY_VERSION
from app.assistant.validation import validate_online_settings
from app.assistant_index.embeddings import validate_assistant_worker_settings
from app.assistant_qualification.profile import QualificationProfile, profile_digest
from app.assistant_qualification.runtime_binding import (
    QualificationBindingError,
    selected_profile_path,
    validate_runtime_profile_binding,
)
from app.config import Settings
from tests.test_assistant_qualification_profile import valid_profile_data


def _cny(micro: int) -> Decimal:
    return Decimal(micro) / Decimal(1_000_000)


def _bound(tmp_path: Path) -> tuple[Settings, Path, QualificationProfile]:
    data = valid_profile_data()
    names = {
        "content_sqlite": "content/gavin.db",
        "content_write_fence": "content/gavin.write-fence.lock",
        "assistant_runtime": "runtime/assistant.db",
        "media_root": "media",
        "qdrant_volume": "qdrant",
        "qualification_root": "qualification",
        "rollback_root": "rollback",
    }
    for field, relative in names.items():
        data["storage"]["paths"][field] = str((tmp_path / relative).resolve())
    profile = QualificationProfile.model_validate(data)
    profile_path = (tmp_path / "selected-profile.json").resolve()
    profile_path.write_text(
        json.dumps(profile.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )
    chat = profile.providers.chat
    embedding = profile.providers.embedding
    budgets = profile.providers.budgets
    settings = Settings(
        environment="production",
        admin_password="production-admin-password-not-a-placeholder",
        database_url=f"sqlite:///{Path(profile.storage.paths.content_sqlite).as_posix()}",
        content_write_fence_path=profile.storage.paths.content_write_fence,
        media_root=profile.storage.paths.media_root,
        assistant_runtime_path=profile.storage.paths.assistant_runtime,
        assistant_qdrant_volume=profile.storage.paths.qdrant_volume,
        assistant_qdrant_timeout_seconds=profile.qdrant.request_timeout_seconds,
        assistant_qdrant_collection_prefix=profile.qdrant.collection_prefix,
        assistant_qualification_profile_path=str(profile_path),
        assistant_qualification_profile_digest=profile_digest(profile),
        assistant_public_origin=profile.edge.canonical_origin,
        assistant_trusted_proxies=",".join(profile.edge.trusted_proxy_cidrs),
        assistant_client_ip_header=profile.edge.client_ip_header,
        assistant_sse_heartbeat_seconds=profile.edge.heartbeat_interval_seconds,
        assistant_chat_provider=chat.protocol,
        assistant_chat_model=chat.model,
        assistant_chat_model_version=chat.model_version,
        assistant_chat_max_input_tokens=chat.max_input_tokens,
        assistant_chat_max_output_tokens=chat.max_output_tokens,
        assistant_chat_context_window_tokens=chat.context_window_tokens,
        assistant_chat_reports_usage=chat.reports_usage,
        assistant_chat_reports_finish_reason=chat.reports_finish_reason,
        assistant_chat_input_price_cny_per_million=_cny(
            chat.input_price_micro_cny_per_million
        ),
        assistant_chat_output_price_cny_per_million=_cny(
            chat.output_price_micro_cny_per_million
        ),
        assistant_chat_daily_budget_cny=_cny(budgets.chat_daily_micro_cny),
        assistant_query_embedding_daily_budget_cny=_cny(
            budgets.query_embedding_daily_micro_cny
        ),
        assistant_index_embedding_daily_budget_cny=_cny(
            budgets.index_embedding_daily_micro_cny
        ),
        assistant_embedding_provider=embedding.protocol,
        assistant_embedding_model=embedding.model,
        assistant_embedding_model_version=embedding.model_version,
        assistant_embedding_dimension=embedding.dimension,
        assistant_embedding_max_batch_items=embedding.max_batch_items,
        assistant_embedding_provider_max_concurrency=embedding.max_concurrency,
        assistant_chat_provider_max_concurrency=chat.max_concurrency,
        assistant_embedding_input_price_cny_per_million=_cny(
            embedding.input_price_micro_cny_per_million
        ),
        assistant_provider_timeout_seconds=profile.runner_timing.provider_timeout_seconds,
        assistant_ntp_service=profile.host.ntp_service,
        assistant_max_clock_drift_seconds=profile.host.max_clock_drift_seconds,
        assistant_pipeline_version=profile.qdrant.pipeline_version,
        assistant_qdrant_url=(
            f"http://{profile.services.qdrant.bind_address}:"
            f"{profile.services.qdrant.port}"
        ),
        _env_file=None,
    )
    return settings, profile_path, profile


def test_production_runtime_is_bound_to_exact_reviewed_profile(tmp_path: Path) -> None:
    settings, profile_path, profile = _bound(tmp_path)

    assert validate_runtime_profile_binding(settings) == profile
    assert selected_profile_path(settings) == profile_path


def test_production_worker_startup_enforces_profile_binding(tmp_path: Path) -> None:
    settings, _, _ = _bound(tmp_path)
    worker = settings.model_copy(
        update={
            "assistant_index_worker_enabled": True,
            "assistant_embedding_endpoint": "https://provider.invalid/v1",
            "assistant_embedding_api_key": "embedding-secret-not-recorded",
            "assistant_qdrant_api_key": "qdrant-secret-not-recorded",
        }
    )

    validate_assistant_worker_settings(worker)


def test_production_online_startup_enforces_profile_binding(tmp_path: Path) -> None:
    settings, _, _ = _bound(tmp_path)
    online = settings.model_copy(
        update={
            "assistant_online_enabled": True,
            "assistant_single_process_confirmed": True,
            "assistant_chat_endpoint": "https://provider.invalid/v1",
            "assistant_chat_api_key": "chat-secret-not-recorded",
            "assistant_embedding_endpoint": "https://provider.invalid/v1",
            "assistant_embedding_api_key": "embedding-secret-not-recorded",
            "assistant_qdrant_api_key": "qdrant-secret-not-recorded",
            "assistant_ip_hmac_secret": "ip-secret-value-with-at-least-32-bytes",
            "assistant_session_hmac_secret": "session-secret-value-at-least-32-bytes",
            "assistant_csrf_hmac_secret": "csrf-secret-value-with-at-least-32-bytes",
            "assistant_proxy_hmac_secret": "proxy-secret-value-at-least-32-bytes",
            "assistant_readiness_hmac_secret": "ready-secret-value-at-least-32-bytes",
            "assistant_proxy_max_clock_skew_seconds": 10,
            "assistant_provider_probe_sha256": "sha256:" + "a" * 64,
            "assistant_release_id": "release-20260830-qualification",
            "assistant_policy_version": POLICY_VERSION,
            "assistant_runner_cleanup_grace_seconds": 30,
        }
    )

    validate_online_settings(online)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("assistant_chat_model_version", "2026-08-02", "model_version"),
        ("assistant_chat_daily_budget_cny", Decimal("3.00"), "daily_budget"),
        ("assistant_qdrant_url", "http://127.0.0.1:7333", "port"),
        ("assistant_qdrant_volume", "relative/qdrant", "must be absolute"),
    ],
)
def test_production_runtime_rejects_profile_drift(
    tmp_path: Path, field: str, value: object, match: str
) -> None:
    settings, _, _ = _bound(tmp_path)
    drifted = settings.model_copy(update={field: value})

    with pytest.raises(QualificationBindingError, match=match):
        validate_runtime_profile_binding(drifted)


def test_production_runtime_rejects_profile_changed_after_digest_approval(
    tmp_path: Path,
) -> None:
    settings, profile_path, _ = _bound(tmp_path)
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    changed = copy.deepcopy(payload)
    changed["profile_revision"] = 2
    profile_path.write_text(json.dumps(changed), encoding="utf-8")

    with pytest.raises(QualificationBindingError, match="profile_digest"):
        validate_runtime_profile_binding(settings)


def test_non_production_cannot_claim_production_profile_binding(tmp_path: Path) -> None:
    settings, _, _ = _bound(tmp_path)

    with pytest.raises(QualificationBindingError, match="production-only"):
        validate_runtime_profile_binding(settings.model_copy(update={"environment": "test"}))
