from __future__ import annotations

import hashlib
import math

from langchain_core.embeddings import Embeddings

from ..config import Settings
from .constants import (
    FORBIDDEN_IDENTITY_VALUES,
    TEST_EMBEDDING_PROVIDER,
)


class AssistantIndexConfigurationError(RuntimeError):
    """Raised when the worker is enabled without a usable, explicit configuration."""


def _identity(value: str | None, field: str) -> str:
    if value is None or value.strip().lower() in FORBIDDEN_IDENTITY_VALUES:
        raise AssistantIndexConfigurationError(f"{field} is missing or a placeholder")
    return value.strip()


class DeterministicHashEmbeddings(Embeddings):
    """Offline test double. Not a production embedding provider."""

    def __init__(self, *, dimension: int, model: str, version: str) -> None:
        if dimension < 8:
            raise AssistantIndexConfigurationError("embedding dimension must be >= 8")
        self.dimension = dimension
        self.model = model
        self.version = version

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        seed = hashlib.sha256(f"{self.model}:{self.version}:{text}".encode()).digest()
        values: list[float] = []
        while len(values) < self.dimension:
            seed = hashlib.sha256(seed).digest()
            for offset in range(0, 32, 4):
                number = int.from_bytes(seed[offset : offset + 4], "big")
                values.append((number / 2**32) * 2 - 1)
                if len(values) == self.dimension:
                    break
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]


def validate_assistant_worker_settings(settings: Settings) -> None:
    if not settings.assistant_index_worker_enabled:
        raise AssistantIndexConfigurationError("assistant index worker is disabled")
    provider = _identity(settings.assistant_embedding_provider, "assistant_embedding_provider")
    _identity(settings.assistant_embedding_model, "assistant_embedding_model")
    _identity(settings.assistant_embedding_model_version, "assistant_embedding_model_version")
    if settings.assistant_embedding_dimension is None:
        raise AssistantIndexConfigurationError("assistant_embedding_dimension is required")
    if settings.assistant_chunk_overlap >= settings.assistant_chunk_size:
        raise AssistantIndexConfigurationError("chunk overlap must be smaller than chunk size")
    if provider == TEST_EMBEDDING_PROVIDER:
        if settings.environment == "production":
            raise AssistantIndexConfigurationError(
                "test embedding provider is not allowed in production"
            )
        _validate_qdrant_settings(settings, allow_embedded=True)
        return
    if provider != "openai-compatible":
        raise AssistantIndexConfigurationError(
            f"embedding provider {provider!r} is not implemented; refusing to emit fake vectors"
        )
    endpoint = _identity(settings.assistant_embedding_endpoint, "assistant_embedding_endpoint")
    _identity(settings.assistant_embedding_api_key, "assistant_embedding_api_key")
    if settings.environment == "production" and not endpoint.startswith("https://"):
        raise AssistantIndexConfigurationError("production embedding endpoint must be https")
    _validate_qdrant_settings(settings, allow_embedded=False)
    if settings.environment == "production":
        from ..assistant_qualification.runtime_binding import (
            QualificationBindingError,
            validate_runtime_profile_binding,
        )

        try:
            validate_runtime_profile_binding(settings)
        except QualificationBindingError as exc:
            raise AssistantIndexConfigurationError(str(exc)) from exc


def _validate_qdrant_settings(settings: Settings, *, allow_embedded: bool) -> None:
    if settings.environment == "production" or not allow_embedded:
        url = _identity(settings.assistant_qdrant_url, "assistant_qdrant_url")
        _identity(settings.assistant_qdrant_api_key, "assistant_qdrant_api_key")
        if not url.startswith(("http://", "https://")):
            raise AssistantIndexConfigurationError(
                "production Qdrant must be an authenticated private http(s) URL"
            )
        if settings.assistant_qdrant_path:
            raise AssistantIndexConfigurationError(
                "embedded Qdrant paths are not allowed when a remote Qdrant URL is required"
            )
        return
    if settings.assistant_qdrant_url:
        if not settings.assistant_qdrant_url.startswith(("http://", "https://")):
            raise AssistantIndexConfigurationError("assistant_qdrant_url must be http(s)")
        return
    # Local/dev/test: in-memory or a process-private path. A shared embedded
    # directory is rejected because multiple processes cannot own it safely.
    if settings.assistant_qdrant_path in {".", "./", "/"}:
        raise AssistantIndexConfigurationError("embedded Qdrant path is not process-private")


def build_embeddings(settings: Settings) -> Embeddings:
    validate_assistant_worker_settings(settings)
    from ..assistant.providers import build_metered_embeddings

    return build_metered_embeddings(settings)


def validate_qdrant_settings(settings: Settings, *, allow_embedded: bool) -> None:
    _validate_qdrant_settings(settings, allow_embedded=allow_embedded)
