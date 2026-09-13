from __future__ import annotations

from pathlib import Path

from ..assistant.providers import EmbeddingUsage, OpenAICompatibleMeteredEmbeddings
from .artifact import DIMENSION, MAX_TOKENS, MODEL, PIPELINE, VERSION
from .tokenization import E5Tokenizer


def validate_e5_settings(settings) -> None:
    if (
        settings.assistant_embedding_dimension != DIMENSION
        or settings.assistant_embedding_model_version != VERSION
        or settings.assistant_pipeline_version != PIPELINE
        or settings.assistant_embedding_max_batch_items != 1
        or settings.assistant_embedding_provider_max_concurrency != 1
        or settings.assistant_chunk_size != 384
        or settings.assistant_chunk_overlap != 64
        or not settings.assistant_e5_model_dir
    ):
        raise ValueError(
            "E5 requires pinned identity, tokenizer, 384/64 chunks and batch/concurrency 1"
        )
    if settings.environment == "production":
        from ..assistant_qualification.runtime_binding import validate_runtime_profile_binding

        validate_runtime_profile_binding(settings)


class E5Embeddings(OpenAICompatibleMeteredEmbeddings):
    def __init__(self, *, model_directory: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.tokenizer = E5Tokenizer(Path(model_directory))

    def prepare_retrieval_query(self, current: str, history: list[str]) -> tuple[str, bool]:
        return self.tokenizer.retrieval_query(current, history)

    def _embed_role(self, texts: list[str], role: str) -> EmbeddingUsage:
        # Public methods accept raw content. Literal prefixes in source text remain content.
        encoded = [f"{role}: {text}" for text in texts]
        if any(not text.strip() for text in texts):
            raise ValueError("E5 input cannot be empty")
        if any(self.tokenizer.count(text) > MAX_TOKENS for text in encoded):
            raise ValueError("E5 input exceeds 512 tokens")
        vectors = []
        total = 0
        for text in encoded:
            response = self._client.embeddings.create(
                model=MODEL,
                input=[text],
                dimensions=DIMENSION,
                encoding_format="float",
            )
            metadata = response.model_extra or {}
            if (
                response.model != MODEL
                or metadata.get("model_version") != VERSION
                or metadata.get("prefix_scheme") != "client-query-passage-v1"
                or metadata.get("pooling") != "attention-mask-mean"
                or metadata.get("normalization") != "l2"
                or len(response.data) != 1
                or response.data[0].index != 0
            ):
                raise RuntimeError("E5 service identity or response index mismatch")
            import math

            vector = response.data[0].embedding
            if (
                len(vector) != DIMENSION
                or not all(math.isfinite(v) for v in vector)
                or abs(sum(v * v for v in vector) - 1) > 0.001
            ):
                raise RuntimeError("invalid E5 vector")
            tokens = self.tokenizer.count(text)
            if response.usage.prompt_tokens != tokens or response.usage.total_tokens != tokens:
                raise RuntimeError("E5 tokenizer usage mismatch")
            total += tokens
            vectors.append(vector)
        return EmbeddingUsage(
            vectors,
            total,
            "provider-response",
            MODEL,
            "provider-response",
            VERSION,
            "provider-response",
        )

    def embed_documents_metered(self, texts: list[str]) -> EmbeddingUsage:
        return self._embed_role(texts, "passage")

    def embed_query_metered(self, text: str) -> EmbeddingUsage:
        return self._embed_role([text], "query")
