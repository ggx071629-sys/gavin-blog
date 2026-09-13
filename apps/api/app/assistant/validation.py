from __future__ import annotations

from decimal import Decimal
from urllib.parse import urlparse

from ..assistant_index.constants import FORBIDDEN_IDENTITY_VALUES
from ..config import Settings
from .constants import (
    CHAT_PROVIDERS,
    EMBEDDING_PROVIDERS,
    POLICY_VERSION,
    PROVIDER_TEST,
)

REQUIRED_WHEN_ENABLED = (
    "assistant_runtime_path",
    "assistant_public_origin",
    "assistant_sse_heartbeat_seconds",
    "assistant_ip_hmac_secret",
    "assistant_session_hmac_secret",
    "assistant_csrf_hmac_secret",
    "assistant_readiness_hmac_secret",
    "assistant_release_id",
    "assistant_policy_version",
    "assistant_chat_provider",
    "assistant_chat_model",
    "assistant_chat_model_version",
    "assistant_chat_provider_max_concurrency",
    "assistant_chat_endpoint",
    "assistant_chat_api_key",
    "assistant_chat_max_input_tokens",
    "assistant_chat_max_output_tokens",
    "assistant_chat_context_window_tokens",
    "assistant_chat_input_price_cny_per_million",
    "assistant_chat_output_price_cny_per_million",
    "assistant_chat_reports_usage",
    "assistant_chat_reports_finish_reason",
    "assistant_chat_daily_budget_cny",
    "assistant_query_embedding_daily_budget_cny",
    "assistant_index_embedding_daily_budget_cny",
    "assistant_embedding_input_price_cny_per_million",
    "assistant_provider_timeout_seconds",
    "assistant_runner_cleanup_grace_seconds",
    "assistant_embedding_provider",
    "assistant_embedding_model",
    "assistant_embedding_model_version",
    "assistant_embedding_dimension",
    "assistant_embedding_max_batch_items",
    "assistant_embedding_provider_max_concurrency",
    "assistant_embedding_endpoint",
    "assistant_embedding_api_key",
)


def _identity(settings: Settings, field: str) -> str:
    value = getattr(settings, field)
    if value is None:
        raise RuntimeError(f"{field} is required when the public assistant is enabled")
    text = str(value).strip()
    if text.lower() in FORBIDDEN_IDENTITY_VALUES:
        raise RuntimeError(f"{field} is missing or a placeholder")
    return text


def _https(url: str, field: str, *, allow_http_in_test: bool) -> None:
    parsed = urlparse(url)
    if parsed.scheme == "https" and parsed.netloc:
        return
    if allow_http_in_test and parsed.scheme in {"http", "https"} and parsed.netloc:
        return
    raise RuntimeError(f"{field} must be an explicit https endpoint")


def validate_online_settings(settings: Settings) -> None:
    if not settings.assistant_online_enabled:
        return
    if not settings.assistant_single_process_confirmed:
        raise RuntimeError("GAVIN_ASSISTANT_SINGLE_PROCESS_CONFIRMED must be true")
    for field in REQUIRED_WHEN_ENABLED:
        value = getattr(settings, field)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise RuntimeError(f"{field} is required when the public assistant is enabled")
        if isinstance(value, str) and value.strip().lower() in FORBIDDEN_IDENTITY_VALUES:
            raise RuntimeError(f"{field} is missing or a placeholder")
    if settings.assistant_policy_version != POLICY_VERSION:
        raise RuntimeError("assistant_policy_version does not match the running policy")
    max_input = int(settings.assistant_chat_max_input_tokens or 0)
    max_output = int(settings.assistant_chat_max_output_tokens or 0)
    context_window = int(settings.assistant_chat_context_window_tokens or 0)
    if max_input + max_output > context_window:
        raise RuntimeError(
            "assistant chat input and output limits exceed the declared context window"
        )
    chat_provider = _identity(settings, "assistant_chat_provider")
    embedding_provider = _identity(settings, "assistant_embedding_provider")
    if chat_provider not in CHAT_PROVIDERS:
        raise RuntimeError(f"unsupported chat provider {chat_provider!r}")
    if embedding_provider not in EMBEDDING_PROVIDERS:
        raise RuntimeError(f"unsupported embedding provider {embedding_provider!r}")
    allow_test = settings.environment != "production"
    if settings.environment == "production":
        if chat_provider == PROVIDER_TEST or embedding_provider == PROVIDER_TEST:
            raise RuntimeError("test assistant providers are not allowed in production")
        if (
            not settings.assistant_chat_reports_usage
            or not settings.assistant_chat_reports_finish_reason
        ):
            raise RuntimeError("production chat must report usage and finish reason")
        _identity(settings, "assistant_qualification_profile_digest")
        _identity(settings, "assistant_provider_probe_sha256")
        _identity(settings, "assistant_qualification_profile_path")
    else:
        if not allow_test and chat_provider == PROVIDER_TEST:
            raise RuntimeError("test chat provider is not allowed")
    timeout = settings.assistant_provider_timeout_seconds
    grace = settings.assistant_runner_cleanup_grace_seconds
    if timeout is None or grace is None or timeout + grace >= 900:
        raise RuntimeError("provider timeout plus cleanup grace must be below the purge SLA")
    _https(
        str(settings.assistant_chat_endpoint),
        "assistant_chat_endpoint",
        allow_http_in_test=allow_test,
    )
    _https(
        str(settings.assistant_embedding_endpoint),
        "assistant_embedding_endpoint",
        allow_http_in_test=allow_test,
    )
    origin = _identity(settings, "assistant_public_origin").rstrip("/")
    parsed = urlparse(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"}:
        raise RuntimeError("assistant_public_origin must be a canonical origin")
    for secret_field in (
        "assistant_ip_hmac_secret",
        "assistant_session_hmac_secret",
        "assistant_csrf_hmac_secret",
        "assistant_readiness_hmac_secret",
    ):
        secret = _identity(settings, secret_field)
        if len(secret) < 32:
            raise RuntimeError(f"{secret_field} must be at least 32 characters")
    control_secrets = {
        settings.assistant_ip_hmac_secret,
        settings.assistant_session_hmac_secret,
        settings.assistant_csrf_hmac_secret,
        settings.assistant_readiness_hmac_secret,
    }
    if len(control_secrets) != 4:
        raise RuntimeError(
            "session, CSRF, IP, and readiness HMAC secrets must be independent"
        )
    proxy_configured = bool(
        settings.assistant_trusted_proxy_cidrs
        or settings.assistant_client_ip_header
        or settings.assistant_proxy_hmac_secret
        or settings.assistant_proxy_max_clock_skew_seconds
    )
    if settings.environment == "production" or proxy_configured:
        import ipaddress

        if not settings.assistant_trusted_proxy_cidrs:
            raise RuntimeError("assistant_trusted_proxies is required for the production proxy")
        header = _identity(settings, "assistant_client_ip_header")
        if header.lower() in {"forwarded", "x-forwarded-for", "x-real-ip"}:
            raise RuntimeError("assistant_client_ip_header must be a dedicated proxy header")
        proxy_secret = _identity(settings, "assistant_proxy_hmac_secret")
        if len(proxy_secret) < 32:
            raise RuntimeError("assistant_proxy_hmac_secret must be at least 32 characters")
        if settings.assistant_proxy_max_clock_skew_seconds is None:
            raise RuntimeError("assistant_proxy_max_clock_skew_seconds is required")
        if settings.assistant_proxy_hmac_secret in control_secrets:
            raise RuntimeError(
                "session, CSRF, IP, proxy identity, and readiness HMAC secrets "
                "must be independent"
            )
        for cidr in settings.assistant_trusted_proxy_cidrs:
            try:
                network = ipaddress.ip_network(cidr, strict=False)
            except ValueError as exc:
                raise RuntimeError("assistant_trusted_proxies contains an invalid CIDR") from exc
            if not (network.is_private or network.is_loopback):
                raise RuntimeError(
                    "assistant_trusted_proxies must contain private or loopback CIDRs"
                )
    heartbeat = int(settings.assistant_sse_heartbeat_seconds or 0)
    if heartbeat >= int(settings.assistant_provider_timeout_seconds or 0):
        raise RuntimeError("assistant SSE heartbeat must be below the provider timeout")
    for price_field in (
        "assistant_chat_input_price_cny_per_million",
        "assistant_chat_output_price_cny_per_million",
        "assistant_chat_daily_budget_cny",
        "assistant_query_embedding_daily_budget_cny",
        "assistant_index_embedding_daily_budget_cny",
        "assistant_embedding_input_price_cny_per_million",
    ):
        price = getattr(settings, price_field)
        if not isinstance(price, Decimal) or price < Decimal("0"):
            raise RuntimeError(f"{price_field} must be an explicit non-negative CNY decimal")
    if settings.assistant_langsmith_tracing:
        raise RuntimeError("LangSmith raw-content tracing cannot be enabled in this stage")
    if settings.environment == "production" or chat_provider != PROVIDER_TEST:
        from ..assistant_index.embeddings import validate_qdrant_settings

        validate_qdrant_settings(settings, allow_embedded=settings.environment != "production")
    if settings.environment == "production":
        from ..assistant_qualification.runtime_binding import (
            validate_runtime_profile_binding,
        )

        validate_runtime_profile_binding(settings)
