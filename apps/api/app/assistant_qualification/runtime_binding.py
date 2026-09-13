from __future__ import annotations

import ipaddress
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from ..content_write_fence import content_database_path, content_write_fence_path
from .profile import QualificationProfile, load_profile, profile_digest

if TYPE_CHECKING:
    from ..config import Settings


class QualificationBindingError(RuntimeError):
    """The running production configuration drifted from its approved profile."""


def _micro_cny(value: Decimal | None, field: str) -> int:
    if value is None:
        raise QualificationBindingError(f"{field} is missing")
    scaled = value * Decimal(1_000_000)
    if scaled != scaled.to_integral_value():
        raise QualificationBindingError(f"{field} cannot be represented as integer micro-CNY")
    return int(scaled)


def _absolute(value: str | None, field: str) -> Path:
    if value is None or not value.strip():
        raise QualificationBindingError(f"{field} is required by the qualification profile")
    path = Path(value)
    if not path.is_absolute():
        raise QualificationBindingError(f"{field} must be absolute in production")
    return path.resolve()


def _expect(actual: Any, expected: Any, field: str) -> None:
    if actual != expected:
        raise QualificationBindingError(f"{field} does not match the qualification profile")


def _profile_path(settings: Settings) -> Path:
    return _absolute(
        settings.assistant_qualification_profile_path,
        "assistant_qualification_profile_path",
    )


def _load_bound_profile(settings: Settings) -> QualificationProfile:
    path = _profile_path(settings)
    try:
        profile = load_profile(path)
    except (OSError, ValueError) as exc:
        raise QualificationBindingError("qualification profile is unreadable or invalid") from exc
    _expect(
        settings.assistant_qualification_profile_digest,
        profile_digest(profile),
        "assistant_qualification_profile_digest",
    )
    return profile


def _validate_storage(settings: Settings, profile: QualificationProfile) -> None:
    expected = profile.storage.paths
    actual_paths = (
        (content_database_path(settings), expected.content_sqlite, "database_url"),
        (
            content_write_fence_path(settings),
            expected.content_write_fence,
            "content_write_fence_path",
        ),
        (
            _absolute(settings.assistant_runtime_path, "assistant_runtime_path"),
            expected.assistant_runtime,
            "assistant_runtime_path",
        ),
        (_absolute(settings.media_root, "media_root"), expected.media_root, "media_root"),
        (
            _absolute(settings.assistant_qdrant_volume, "assistant_qdrant_volume"),
            expected.qdrant_volume,
            "assistant_qdrant_volume",
        ),
    )
    for actual, configured, field in actual_paths:
        _expect(actual, Path(configured).resolve(), field)


def _validate_edge(settings: Settings, profile: QualificationProfile) -> None:
    edge = profile.edge
    _expect(
        str(settings.assistant_public_origin or "").rstrip("/"),
        edge.canonical_origin.rstrip("/"),
        "assistant_public_origin",
    )
    actual_cidrs = [
        str(ipaddress.ip_network(value, strict=False))
        for value in settings.assistant_trusted_proxy_cidrs
    ]
    _expect(actual_cidrs, edge.trusted_proxy_cidrs, "assistant_trusted_proxies")
    _expect(
        settings.assistant_client_ip_header,
        edge.client_ip_header,
        "assistant_client_ip_header",
    )
    _expect(
        settings.assistant_sse_heartbeat_seconds,
        edge.heartbeat_interval_seconds,
        "assistant_sse_heartbeat_seconds",
    )


def _validate_providers(settings: Settings, profile: QualificationProfile) -> None:
    chat = profile.providers.chat
    embedding = profile.providers.embedding
    budgets = profile.providers.budgets
    values = (
        (settings.assistant_chat_provider, chat.protocol, "assistant_chat_provider"),
        (settings.assistant_chat_model, chat.model, "assistant_chat_model"),
        (
            settings.assistant_chat_model_version,
            chat.model_version,
            "assistant_chat_model_version",
        ),
        (
            settings.assistant_chat_max_input_tokens,
            chat.max_input_tokens,
            "assistant_chat_max_input_tokens",
        ),
        (
            settings.assistant_chat_max_output_tokens,
            chat.max_output_tokens,
            "assistant_chat_max_output_tokens",
        ),
        (
            settings.assistant_chat_context_window_tokens,
            chat.context_window_tokens,
            "assistant_chat_context_window_tokens",
        ),
        (settings.assistant_chat_reports_usage, chat.reports_usage, "assistant_chat_reports_usage"),
        (
            settings.assistant_chat_reports_finish_reason,
            chat.reports_finish_reason,
            "assistant_chat_reports_finish_reason",
        ),
        (
            settings.assistant_embedding_provider,
            embedding.protocol,
            "assistant_embedding_provider",
        ),
        (settings.assistant_embedding_model, embedding.model, "assistant_embedding_model"),
        (
            settings.assistant_embedding_model_version,
            embedding.model_version,
            "assistant_embedding_model_version",
        ),
        (
            settings.assistant_embedding_dimension,
            embedding.dimension,
            "assistant_embedding_dimension",
        ),
        (
            settings.assistant_embedding_max_batch_items,
            embedding.max_batch_items,
            "assistant_embedding_max_batch_items",
        ),
        (
            settings.assistant_embedding_provider_max_concurrency,
            embedding.max_concurrency,
            "assistant_embedding_provider_max_concurrency",
        ),
        (
            settings.assistant_chat_provider_max_concurrency,
            chat.max_concurrency,
            "assistant_chat_provider_max_concurrency",
        ),
        (
            settings.assistant_provider_timeout_seconds,
            profile.runner_timing.provider_timeout_seconds,
            "assistant_provider_timeout_seconds",
        ),
        (
            settings.assistant_pipeline_version,
            profile.qdrant.pipeline_version,
            "assistant_pipeline_version",
        ),
        (
            settings.assistant_qdrant_collection_prefix,
            profile.qdrant.collection_prefix,
            "assistant_qdrant_collection_prefix",
        ),
        (
            settings.assistant_qdrant_timeout_seconds,
            profile.qdrant.request_timeout_seconds,
            "assistant_qdrant_timeout_seconds",
        ),
        (settings.assistant_ntp_service, profile.host.ntp_service, "assistant_ntp_service"),
        (
            settings.assistant_max_clock_drift_seconds,
            profile.host.max_clock_drift_seconds,
            "assistant_max_clock_drift_seconds",
        ),
    )
    for actual, configured, field in values:
        _expect(actual, configured, field)
    prices = (
        (
            settings.assistant_chat_input_price_cny_per_million,
            chat.input_price_micro_cny_per_million,
            "assistant_chat_input_price_cny_per_million",
        ),
        (
            settings.assistant_chat_output_price_cny_per_million,
            chat.output_price_micro_cny_per_million,
            "assistant_chat_output_price_cny_per_million",
        ),
        (
            settings.assistant_embedding_input_price_cny_per_million,
            embedding.input_price_micro_cny_per_million,
            "assistant_embedding_input_price_cny_per_million",
        ),
        (
            settings.assistant_chat_daily_budget_cny,
            budgets.chat_daily_micro_cny,
            "assistant_chat_daily_budget_cny",
        ),
        (
            settings.assistant_query_embedding_daily_budget_cny,
            budgets.query_embedding_daily_micro_cny,
            "assistant_query_embedding_daily_budget_cny",
        ),
        (
            settings.assistant_index_embedding_daily_budget_cny,
            budgets.index_embedding_daily_micro_cny,
            "assistant_index_embedding_daily_budget_cny",
        ),
    )
    for price_cny, price_micro, price_field in prices:
        _expect(_micro_cny(price_cny, price_field), price_micro, price_field)


def _validate_qdrant(settings: Settings, profile: QualificationProfile) -> None:
    parsed = urlparse(str(settings.assistant_qdrant_url or ""))
    _expect(parsed.hostname, profile.services.qdrant.bind_address, "assistant_qdrant_url host")
    _expect(parsed.port, profile.services.qdrant.port, "assistant_qdrant_url port")
    _expect(
        settings.assistant_embedding_dimension,
        profile.qdrant.vector_dimension,
        "Qdrant vector dimension",
    )


def validate_runtime_profile_binding(settings: Settings) -> QualificationProfile:
    """Bind a production API/Worker process to one reviewed non-secret profile."""

    if settings.environment != "production":
        raise QualificationBindingError("runtime qualification binding is production-only")
    profile = _load_bound_profile(settings)
    _validate_storage(settings, profile)
    _validate_edge(settings, profile)
    _validate_providers(settings, profile)
    _validate_qdrant(settings, profile)
    return profile


def selected_profile_path(settings: Settings) -> Path:
    """Return the exact selected profile path after production binding validation."""

    validate_runtime_profile_binding(settings)
    return _profile_path(settings)
