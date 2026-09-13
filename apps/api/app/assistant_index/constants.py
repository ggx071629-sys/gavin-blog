from __future__ import annotations

DEFAULT_PIPELINE_VERSION = "assistant-index-v1"
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 120
DISTANCE_COSINE = "Cosine"
TEST_EMBEDDING_PROVIDER = "test"
TEST_EMBEDDING_MODEL = "deterministic-hash"
TEST_EMBEDDING_MODEL_VERSION = "test-v1"
RRF_K = 60
POINTER_ID = 1
SOURCE_ARTICLE = "article"
SOURCE_PROJECT = "project"
SOURCE_BOOK = "book"
SOURCE_PROFILE = "profile"
SOURCE_ABOUT = "about"
SOURCE_RESUME = "resume"
SOURCE_TYPES = (
    SOURCE_ARTICLE, SOURCE_PROJECT, SOURCE_BOOK, SOURCE_PROFILE, SOURCE_ABOUT, SOURCE_RESUME,
)
OP_UPSERT = "upsert"
OP_DELETE = "delete"
OP_PURGE = "purge"
STATUS_PENDING = "pending"
STATUS_LEASED = "leased"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"
GEN_STAGING = "staging"
GEN_ACTIVE = "active"
GEN_PREVIOUS = "previous"
GEN_FAILED = "failed"
GEN_ABANDONED = "abandoned"
PAYLOAD_ALLOWLIST = (
    "chunk_id",
    "source_type",
    "source_id",
    "source_version",
    "generation",
    "pipeline_version",
)
FORBIDDEN_IDENTITY_VALUES = frozenset(
    {
        "",
        "none",
        "null",
        "placeholder",
        "fake",
        "dummy",
        "todo",
        "changeme",
        "change-me",
        "example",
    }
)
