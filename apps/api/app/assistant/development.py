"""Strictly local assembly for the tracked assistant development command."""

from __future__ import annotations

import secrets
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.engine import make_url

from ..assistant_index.constants import (
    TEST_EMBEDDING_MODEL,
    TEST_EMBEDDING_MODEL_VERSION,
    TEST_EMBEDDING_PROVIDER,
)
from ..assistant_index.worker import rebuild_generation
from ..config import Settings
from ..db import Database
from ..models import AssistantIndexCommand
from .admin_operations import finalize_rebuild, update_availability
from .constants import POLICY_VERSION, PROVIDER_TEST, TEST_CHAT_MODEL, TEST_CHAT_MODEL_VERSION
from .readiness import write_receipt


def _loopback_origin(value: str) -> str:
    parsed = urlparse(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or not parsed.port
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError("assistant development origin must be a canonical loopback HTTP origin")
    return value.rstrip("/")


def build_development_settings(
    base: Settings,
    *,
    run_root: Path,
    web_origin: str,
    proxy_secret: str,
) -> Settings:
    """Overlay safe offline assistant settings on the project's development Settings."""

    if base.environment != "development":
        raise RuntimeError("npm run dev:assistant requires GAVIN_ENVIRONMENT=development")
    database = make_url(base.database_url)
    if database.get_backend_name() != "sqlite" or database.database in {None, "", ":memory:"}:
        raise RuntimeError("assistant development mode requires the project's file-backed SQLite")
    if not run_root.is_absolute():
        raise RuntimeError("assistant development run root must be absolute")
    origin = _loopback_origin(web_origin)
    if len(proxy_secret) < 32:
        raise RuntimeError("assistant development proxy secret must be at least 32 characters")

    values = {name: getattr(base, name) for name in Settings.model_fields}
    values.update(
        {
            "cookie_secure": False,
            "cors_origins": origin,
            "assistant_index_worker_enabled": True,
            "assistant_embedding_provider": TEST_EMBEDDING_PROVIDER,
            "assistant_embedding_model": TEST_EMBEDDING_MODEL,
            "assistant_embedding_model_version": TEST_EMBEDDING_MODEL_VERSION,
            "assistant_embedding_dimension": 512,
            "assistant_embedding_max_batch_items": 64,
            "assistant_embedding_provider_max_concurrency": 1,
            "assistant_embedding_endpoint": "https://offline-development.invalid/v1",
            "assistant_embedding_api_key": "offline-development-embedding",
            "assistant_qdrant_url": None,
            "assistant_qdrant_api_key": None,
            "assistant_qdrant_path": None,
            "assistant_qdrant_volume": None,
            "assistant_online_enabled": True,
            "assistant_runtime_path": str(run_root / "assistant_runtime.db"),
            "assistant_single_process_confirmed": True,
            "assistant_public_origin": origin,
            "assistant_trusted_proxies": "127.0.0.1/32,::1/128",
            "assistant_client_ip_header": "X-Gavin-Client-IP",
            "assistant_proxy_hmac_secret": proxy_secret,
            "assistant_proxy_max_clock_skew_seconds": 10,
            "assistant_sse_heartbeat_seconds": 1,
            "assistant_ip_hmac_secret": secrets.token_urlsafe(32),
            "assistant_session_hmac_secret": secrets.token_urlsafe(32),
            "assistant_csrf_hmac_secret": secrets.token_urlsafe(32),
            "assistant_readiness_hmac_secret": secrets.token_urlsafe(32),
            "assistant_qualification_profile_path": None,
            "assistant_qualification_profile_digest": None,
            "assistant_provider_probe_sha256": None,
            "assistant_release_id": "assistant-local-development-v1",
            "assistant_policy_version": POLICY_VERSION,
            "assistant_chat_provider": PROVIDER_TEST,
            "assistant_chat_model": TEST_CHAT_MODEL,
            "assistant_chat_model_version": TEST_CHAT_MODEL_VERSION,
            "assistant_chat_provider_max_concurrency": 1,
            "assistant_chat_endpoint": "https://offline-development.invalid/v1",
            "assistant_chat_api_key": "offline-development-chat",
            "assistant_chat_max_input_tokens": 8000,
            "assistant_chat_max_output_tokens": 400,
            "assistant_chat_context_window_tokens": 16384,
            "assistant_chat_input_price_cny_per_million": Decimal("0"),
            "assistant_chat_output_price_cny_per_million": Decimal("0"),
            "assistant_chat_reports_usage": True,
            "assistant_chat_reports_finish_reason": True,
            "assistant_chat_daily_budget_cny": Decimal("0"),
            "assistant_query_embedding_daily_budget_cny": Decimal("0"),
            "assistant_index_embedding_daily_budget_cny": Decimal("0"),
            "assistant_embedding_input_price_cny_per_million": Decimal("0"),
            "assistant_provider_timeout_seconds": 30,
            "assistant_runner_cleanup_grace_seconds": 5,
            "assistant_langsmith_tracing": False,
            "assistant_test_startup_bootstrap": False,
            "assistant_local_dev_mode": True,
        }
    )
    settings = Settings(**values, _env_file=None)
    settings.validate_runtime()
    return settings


def bootstrap_development_assistant(
    settings: Settings,
    database: Database,
    online,
) -> None:
    """Rebuild the in-memory index from existing public content before serving requests."""

    if settings.environment != "development" or not settings.assistant_local_dev_mode:
        raise RuntimeError("assistant development bootstrap refused outside local development")
    generation_id = rebuild_generation(online.index_runtime)
    with database.session_factory() as db:
        command = db.scalar(
            select(AssistantIndexCommand).where(
                AssistantIndexCommand.generation_id == generation_id
            )
        )
        if command is None:
            raise RuntimeError("assistant development rebuild command is missing")
        operation_id = command.id
        operation_version = command.version
    finalize_rebuild(
        online,
        operation_id=operation_id,
        expected_version=operation_version,
        idempotency_key=f"development-finalize-{generation_id}",
    )
    write_receipt(settings, probe_live=False, lock=online.lock)
    gate = online.control.read(
        lambda conn: conn.execute(
            "SELECT version FROM assistant_operational_gate WHERE id = 1"
        ).fetchone()
    )
    if gate is None:
        raise RuntimeError("assistant development operational gate is missing")
    update_availability(online, enabled=True, expected_version=int(gate["version"]))


def validate_real_development_settings(settings: Settings) -> None:
    from ..local_embedding.artifact import MODEL
    from ..local_embedding.client import validate_e5_settings

    if (
        settings.environment != "development"
        or not settings.assistant_online_enabled
        or settings.assistant_local_dev_mode
        or settings.assistant_test_startup_bootstrap
        or settings.assistant_chat_provider != "openai-compatible"
        or settings.assistant_embedding_provider != "openai-compatible"
        or settings.assistant_embedding_model != MODEL
        or settings.assistant_qualification_profile_path
        or settings.assistant_qualification_profile_digest
        or not Path(settings.assistant_runtime_path or "").is_absolute()
        or settings.assistant_release_id != "assistant-local-real-v1"
    ):
        raise RuntimeError("real assistant requires the explicit local development configuration")
    _loopback_origin(str(settings.assistant_public_origin))
    validate_e5_settings(settings)
    for endpoint in (settings.assistant_embedding_endpoint, settings.assistant_qdrant_url):
        if urlparse(str(endpoint)).hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise RuntimeError("real development dependencies must use loopback")


def build_real_development_settings(
    base: Settings,
    chat: Settings,
    *,
    run_root: Path,
    web_origin: str,
    proxy_secret: str,
    probe_path: Path,
) -> Settings:
    from ..assistant_qualification.provider_probe import (
        provider_probe_digest,
        validate_local_chat_probe_artifact,
    )

    if base.environment != "development" or chat.environment != "development":
        raise RuntimeError("real development cannot overlay another environment")
    if not run_root.is_absolute() or len(proxy_secret) < 32:
        raise RuntimeError("real development needs a persistent absolute root and proxy secret")
    database = make_url(base.database_url)
    if database.get_backend_name() != "sqlite" or database.database in {None, "", ":memory:"}:
        raise RuntimeError("real development requires a file-backed content database")
    values = {name: getattr(base, name) for name in Settings.model_fields}
    for name in Settings.model_fields:
        if name.startswith("assistant_chat_") or name in {
            "assistant_readiness_hmac_secret",
            "assistant_ip_hmac_secret",
            "assistant_session_hmac_secret",
            "assistant_csrf_hmac_secret",
            "assistant_provider_timeout_seconds",
        }:
            values[name] = getattr(chat, name)
    origin = _loopback_origin(web_origin)
    values.update(
        {
            "cookie_secure": False,
            "cors_origins": origin,
            "assistant_online_enabled": True,
            "assistant_local_dev_mode": False,
            "assistant_test_startup_bootstrap": False,
            "assistant_runtime_path": str(run_root / "assistant_runtime.db"),
            "assistant_single_process_confirmed": True,
            "assistant_public_origin": origin,
            "assistant_trusted_proxies": "127.0.0.1/32,::1/128",
            "assistant_client_ip_header": "X-Gavin-Client-IP",
            "assistant_proxy_hmac_secret": proxy_secret,
            "assistant_proxy_max_clock_skew_seconds": 10,
            "assistant_sse_heartbeat_seconds": 1,
            "assistant_runner_cleanup_grace_seconds": 5,
            "assistant_release_id": "assistant-local-real-v1",
            "assistant_policy_version": POLICY_VERSION,
            "assistant_qualification_profile_path": None,
            "assistant_qualification_profile_digest": None,
            "assistant_provider_probe_sha256": provider_probe_digest(probe_path),
            "assistant_langsmith_tracing": False,
        }
    )
    settings = Settings(**values, _env_file=None)
    settings.validate_runtime()
    validate_real_development_settings(settings)
    validate_local_chat_probe_artifact(probe_path, settings)
    return settings


def revalidate_local_readiness(online, probe_path: Path, *, content_fence_held=False) -> None:
    """Validate the current local generation under the content fence, without Chat."""
    from contextlib import nullcontext

    from sqlalchemy import text

    from ..assistant_index.integrity import active_generation, audit_generation
    from ..assistant_qualification.provider_probe import validate_local_chat_probe_artifact
    from ..content_write_fence import content_write_fence
    from ..http_errors import ApiException
    from .errors import AssistantNotReadyError
    from .readiness import verify_receipt

    settings = online.settings
    try:
        validate_real_development_settings(settings)
        validate_local_chat_probe_artifact(probe_path, settings)
        fence = nullcontext() if content_fence_held else content_write_fence(settings)
        with fence:
            with online.database.session_factory() as db:
                db.execute(text("BEGIN"))
                audit_generation(db, online.index_runtime, active_generation(db)).require_passed()
            generation = online.active_generation()
            try:
                online.control.read(lambda conn: verify_receipt(settings, conn, generation))
            except AssistantNotReadyError:
                write_receipt(
                    settings, probe_live=True, provider_probe=probe_path,
                    local_development=True, lock=online.lock,
                )
            online.control.read(lambda conn: verify_receipt(settings, conn, generation))
    except Exception as exc:
        # Provider/config exceptions may contain credentials; expose no raw detail.
        raise ApiException(
            503, "local_readiness_invalid",
            "本机运行验证未通过：请检查索引完整性、模型验证凭据及旧会话清理状态。",
        ) from exc


def attach_real_development_lifespan(app, settings: Settings, probe_path: Path) -> None:
    """Validate local dependencies while preserving the operator's persisted choices."""
    from .operational import gate_row, validate_enabled_binding

    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        validate_real_development_settings(settings)
        async with original(application):
            online = application.state.assistant
            from ..local_embedding.client import E5Embeddings

            if not isinstance(online.embeddings, E5Embeddings):
                raise RuntimeError("real development requires the E5 adapter")
            online.embeddings.embed_query_metered("本机启动检查")
            revalidate_local_readiness(online, probe_path)
            gate = online.control.read(gate_row)
            if gate and gate["requested_state"] == "enabled":
                # Usually no write is needed. Rebind only when startup legitimately
                # renewed the receipt; a closed gate is never implicitly opened.
                try:
                    online.control.read(lambda conn: validate_enabled_binding(
                        conn, settings=settings, generation=online.active_generation(),
                        now=online.now(), block_on_drift=False,
                    ))
                except Exception:
                    closed = update_availability(online, enabled=False, expected_version=0)
                    update_availability(online, enabled=True, expected_version=closed.version)
            application.state.assistant_local_revalidate = (
                # POST middleware already owns the content fence through response.
                lambda: revalidate_local_readiness(online, probe_path, content_fence_held=True)
            )
            try:
                yield
            finally:
                del application.state.assistant_local_revalidate
                # Runtime shutdown cancels execution; it must not rewrite operator intent.

    app.router.lifespan_context = lifespan
