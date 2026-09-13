from __future__ import annotations

from datetime import timedelta, timezone

POLICY_VERSION = "assistant-online-v2"
ESTIMATOR_VERSION = "assistant-token-estimator-v2"
PREFLIGHT_VERSION = "assistant-preflight-v1"
SCHEMA_VERSION = "assistant-runtime-control-v4"
BEIJING_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")

SESSION_COOKIE = "gavin_assistant_session"
CSRF_COOKIE = "gavin_assistant_csrf"
CSRF_HEADER = "x-assistant-csrf"

PROVIDER_TEST = "test"
PROVIDER_OPENAI_COMPATIBLE = "openai-compatible"
CHAT_PROVIDERS = (PROVIDER_TEST, PROVIDER_OPENAI_COMPATIBLE)
EMBEDDING_PROVIDERS = (PROVIDER_TEST, PROVIDER_OPENAI_COMPATIBLE)

ATTEMPT_PREPARED = "prepared"
ATTEMPT_SENDING = "sending"
ATTEMPT_SUCCEEDED = "succeeded"
ATTEMPT_UNKNOWN = "unknown"
ATTEMPT_FAILED = "failed"
ATTEMPT_DEFERRED = "deferred"

KIND_CHAT = "chat"
KIND_QUERY_EMBEDDING = "query_embedding"
KIND_INDEX_EMBEDDING = "index_embedding"

STAGE_CHECKING = "checking"
STAGE_RETRIEVING = "retrieving"
STAGE_COMPOSING = "composing"
STAGE_VALIDATING = "validating"
STAGE_EVENTS = (STAGE_CHECKING, STAGE_RETRIEVING, STAGE_COMPOSING, STAGE_VALIDATING)
TERMINAL_ANSWER = "answer"
TERMINAL_REFUSAL = "refusal"
TERMINAL_ERROR = "error"
TERMINAL_EVENTS = (TERMINAL_ANSWER, TERMINAL_REFUSAL, TERMINAL_ERROR)

CODE_INVALID_REQUEST = "invalid_request"
CODE_SESSION_MISSING = "assistant_session_missing"
CODE_SESSION_EXPIRED = "assistant_session_expired"
CODE_ORIGIN_REJECTED = "origin_rejected"
CODE_CSRF_FAILED = "csrf_failed"
CODE_IDEMPOTENCY_CONFLICT = "idempotency_conflict"
CODE_EVENT_CURSOR_INVALID = "event_cursor_invalid"
CODE_IDEMPOTENCY_EXPIRED = "idempotency_result_expired"
CODE_RATE_LIMITED = "rate_limited"
CODE_CONCURRENCY_LIMITED = "concurrency_limited"
CODE_BUDGET_EXHAUSTED = "budget_exhausted"
CODE_STREAM_LIMITED = "stream_connection_limited"
CODE_ASSISTANT_DISABLED = "assistant_disabled"
CODE_ASSISTANT_NOT_READY = "assistant_not_ready"
CODE_PROMPT_BLOCKED = "prompt_blocked"
CODE_OUT_OF_SCOPE = "out_of_scope"
CODE_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
CODE_PROVIDER_UNKNOWN = "provider_result_unknown"
CODE_INPUT_BUDGET_EXCEEDED = "input_budget_exceeded"
CODE_SESSION_REVOKING = "session_revoking"

UNAVAILABLE_MESSAGE = "Public assistant is unavailable"
GENERIC_REFUSAL_MESSAGE = "I can only discuss this site's published content and public profile."
GENERIC_ERROR_MESSAGE = "The assistant could not complete this answer."
INSUFFICIENT_EVIDENCE_MESSAGE = (
    "Published evidence on this site is not sufficient to answer that question."
)

SAVER_TABLES = frozenset({"checkpoints", "writes"})
CONTROL_TABLES = frozenset(
    {
        "assistant_control_alembic_version",
        "assistant_runtime_meta",
        "assistant_sessions",
        "assistant_turns",
        "assistant_attempts",
        "assistant_chat_budgets",
        "assistant_query_embedding_budgets",
        "assistant_rate_events",
        "assistant_leases",
        "assistant_event_journal",
        "assistant_readiness_receipts",
        "assistant_history",
        "assistant_cleanup_state",
        "assistant_cleanup_retries",
        "assistant_operational_gate",
        "assistant_metered_events",
        "assistant_provider_facts",
        "assistant_activity_events",
    }
)

MAX_EVENTS_PER_TURN = 16
MAX_HISTORY_TURNS = 4
MAX_COMPLETED_TURNS_RETAINED = 100
SESSION_BYTE_LIMIT = 256 * 1024
IDEMPOTENCY_TOMBSTONE_HOURS = 48
RATE_EVENT_GRACE_MINUTES = 20
MIDNIGHT_OVERLAP_MINUTES = 10
CLEANUP_SWEEP_SECONDS = 300
PURGE_SLA_SECONDS = 900
BODY_RETENTION_SECONDS = PURGE_SLA_SECONDS
HEARTBEAT_SECONDS = 2
ENVELOPE_LIMIT = 30
ENVELOPE_WINDOW_SECONDS = 60
SESSION_CREATE_LIMIT = 5
SESSION_CREATE_WINDOW_SECONDS = 600
QUESTION_LIMIT_PER_MINUTE = 3
QUESTION_LIMIT_PER_10_MIN = 10
LEASE_SESSION = 1
LEASE_IP = 2
LEASE_GLOBAL = 3
SSE_SUBSCRIBERS_PER_TURN = 1
SSE_SUBSCRIBERS_PER_IP = 3
BUSY_RETRY_LIMIT = 8

TEST_CHAT_MODEL = "deterministic-chat"
TEST_CHAT_MODEL_VERSION = "test-v1"
