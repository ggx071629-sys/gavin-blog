from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="GAVIN_",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "production"
    database_url: str = "sqlite:///./data/gavin.db"
    content_write_fence_path: str | None = None
    admin_username: str = Field(default="gavin", min_length=1, max_length=80)
    admin_password: str = Field(min_length=1)
    admin_email: str = ""
    smtp_host: str = "smtp.163.com"
    smtp_port: int = Field(default=465, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    account_code_secret: SecretStr = SecretStr("")
    cookie_secure: bool = True
    cors_origins: str = ""
    session_ttl_hours: int = Field(default=24, gt=0)
    login_limit: int = Field(default=5, gt=0)
    login_window_seconds: int = Field(default=300, gt=0)
    media_root: str = "./data/media"
    media_max_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    media_max_pixels: int = Field(default=40_000_000, gt=0)
    assistant_index_worker_enabled: bool = False
    assistant_resume_trusted_hosts: str = ""
    assistant_embedding_provider: str | None = None
    assistant_embedding_model: str | None = None
    assistant_embedding_model_version: str | None = None
    assistant_embedding_dimension: int | None = Field(default=None, gt=0)
    assistant_embedding_max_batch_items: int | None = Field(default=None, gt=0, le=2048)
    assistant_embedding_provider_max_concurrency: int | None = Field(
        default=None, gt=0, le=8
    )
    assistant_embedding_endpoint: str | None = None
    assistant_embedding_api_key: str | None = None
    assistant_e5_model_dir: str | None = None
    assistant_qdrant_url: str | None = None
    assistant_qdrant_api_key: str | None = None
    assistant_qdrant_path: str | None = None
    assistant_qdrant_volume: str | None = None
    assistant_qdrant_timeout_seconds: int | None = Field(default=None, gt=0, le=120)
    assistant_qdrant_collection_prefix: str = Field(
        default="assistant_idx", pattern=r"^[a-z][a-z0-9_]{2,50}$"
    )
    assistant_pipeline_version: str = "assistant-index-v1"
    assistant_chunk_size: int = Field(default=800, ge=64, le=8000)
    assistant_chunk_overlap: int = Field(default=120, ge=0, le=2000)
    assistant_index_lease_seconds: int = Field(default=30, gt=0)
    assistant_index_max_attempts: int = Field(default=8, gt=0)
    assistant_index_poll_seconds: float = Field(default=0.5, gt=0)
    assistant_online_enabled: bool = False
    assistant_runtime_path: str | None = None
    assistant_single_process_confirmed: bool = False
    assistant_public_origin: str | None = None
    assistant_trusted_proxies: str = ""
    assistant_client_ip_header: str | None = None
    assistant_proxy_hmac_secret: str | None = None
    assistant_proxy_max_clock_skew_seconds: int | None = Field(default=None, gt=0, le=60)
    assistant_sse_heartbeat_seconds: int | None = Field(default=None, gt=0, le=300)
    assistant_ip_hmac_secret: str | None = None
    assistant_session_hmac_secret: str | None = None
    assistant_csrf_hmac_secret: str | None = None
    assistant_readiness_hmac_secret: str | None = None
    assistant_qualification_profile_path: str | None = None
    assistant_qualification_profile_digest: str | None = None
    assistant_provider_probe_sha256: str | None = None
    assistant_ntp_service: str | None = None
    assistant_max_clock_drift_seconds: int | None = Field(default=None, gt=0, le=60)
    assistant_release_id: str | None = None
    assistant_policy_version: str | None = None
    assistant_chat_provider: str | None = None
    assistant_chat_model: str | None = None
    assistant_chat_model_version: str | None = None
    assistant_chat_provider_max_concurrency: int | None = Field(default=None, gt=0, le=8)
    assistant_chat_endpoint: str | None = None
    assistant_chat_api_key: str | None = None
    assistant_chat_max_input_tokens: int | None = Field(default=None, gt=0)
    assistant_chat_max_output_tokens: int | None = Field(default=None, gt=0)
    assistant_chat_context_window_tokens: int | None = Field(default=None, gt=0)
    assistant_chat_input_price_cny_per_million: Decimal | None = None
    assistant_chat_output_price_cny_per_million: Decimal | None = None
    assistant_chat_reports_usage: bool | None = None
    assistant_chat_reports_finish_reason: bool | None = None
    assistant_chat_daily_budget_cny: Decimal | None = None
    assistant_query_embedding_daily_budget_cny: Decimal | None = None
    assistant_index_embedding_daily_budget_cny: Decimal | None = None
    assistant_embedding_input_price_cny_per_million: Decimal | None = None
    assistant_provider_timeout_seconds: int | None = Field(default=None, gt=0, le=120)
    assistant_runner_cleanup_grace_seconds: int | None = Field(default=None, gt=0, le=30)
    assistant_question_max_chars: int = Field(default=500, gt=0, le=2000)
    assistant_retrieve_limit: int = Field(default=32, gt=0, le=128)
    assistant_history_turns: int = Field(default=4, gt=0, le=4)
    assistant_session_idle_seconds: int = Field(default=1800, gt=0)
    assistant_session_absolute_seconds: int = Field(default=86400, gt=0)
    assistant_evidence_max_chars: int = Field(default=24000, gt=0)
    assistant_langsmith_tracing: bool = False
    assistant_test_startup_bootstrap: bool = False
    assistant_local_dev_mode: bool = False

    @computed_field  # type: ignore[prop-decorator]  # pydantic computed_field stacking
    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @computed_field  # type: ignore[prop-decorator]  # pydantic computed_field stacking
    @property
    def assistant_trusted_proxy_cidrs(self) -> list[str]:
        return [item.strip() for item in self.assistant_trusted_proxies.split(",") if item.strip()]

    def validate_runtime(self) -> None:
        if self.environment == "production" and self.admin_password == "change-me":
            raise RuntimeError("GAVIN_ADMIN_PASSWORD must be changed in production")
        if self.environment == "production" and not self.cookie_secure:
            raise RuntimeError("GAVIN_COOKIE_SECURE must be true in production")
        if "*" in self.allowed_origins:
            raise RuntimeError("GAVIN_CORS_ORIGINS cannot contain '*' when credentials are enabled")
        if self.assistant_test_startup_bootstrap and self.environment != "test":
            raise RuntimeError("assistant test startup bootstrap is only allowed in test")
        if self.assistant_local_dev_mode and self.environment != "development":
            raise RuntimeError("assistant local development mode is only allowed in development")
        if self.assistant_local_dev_mode and self.assistant_test_startup_bootstrap:
            raise RuntimeError(
                "assistant local development and test bootstraps are mutually exclusive"
            )
        if self.assistant_local_dev_mode and (
            self.assistant_chat_provider != "test"
            or self.assistant_embedding_provider != "test"
        ):
            raise RuntimeError("assistant local development mode requires offline test providers")
        if self.assistant_online_enabled:
            from .assistant.validation import validate_online_settings

            validate_online_settings(self)


def build_runtime_settings(**overrides: Any) -> Settings:
    settings = Settings(**overrides)
    settings.validate_runtime()
    return settings


@lru_cache
def get_settings() -> Settings:
    return build_runtime_settings()
