from __future__ import annotations

from ..http_errors import ApiException
from .constants import (
    CODE_ASSISTANT_DISABLED,
    CODE_ASSISTANT_NOT_READY,
    CODE_BUDGET_EXHAUSTED,
    CODE_CONCURRENCY_LIMITED,
    CODE_CSRF_FAILED,
    CODE_EVENT_CURSOR_INVALID,
    CODE_IDEMPOTENCY_CONFLICT,
    CODE_IDEMPOTENCY_EXPIRED,
    CODE_INVALID_REQUEST,
    CODE_ORIGIN_REJECTED,
    CODE_RATE_LIMITED,
    CODE_SESSION_EXPIRED,
    CODE_SESSION_MISSING,
    CODE_STREAM_LIMITED,
    UNAVAILABLE_MESSAGE,
)


class AssistantOwnerLockError(RuntimeError):
    """Raised when the assistant_runtime owner lock cannot be taken."""


class AssistantSchemaError(RuntimeError):
    """Raised when the runtime schema is missing, damaged, or drifted."""


class AssistantNotReadyError(RuntimeError):
    """Raised when the online path cannot start or continue safely."""


def assistant_error(
    status_code: int,
    code: str,
    message: str,
    *,
    retry_after: int | None = None,
) -> ApiException:
    headers = {"Cache-Control": "no-store"}
    return ApiException(
        status_code,
        code,
        message,
        retry_after=retry_after,
        headers=headers,
    )


def disabled() -> ApiException:
    return assistant_error(503, CODE_ASSISTANT_DISABLED, UNAVAILABLE_MESSAGE)


def not_ready() -> ApiException:
    return assistant_error(503, CODE_ASSISTANT_NOT_READY, UNAVAILABLE_MESSAGE)


def invalid_request(message: str = "The assistant request is invalid.") -> ApiException:
    return assistant_error(400, CODE_INVALID_REQUEST, message)


def session_missing() -> ApiException:
    return assistant_error(401, CODE_SESSION_MISSING, "Assistant session is missing.")


def session_expired() -> ApiException:
    return assistant_error(401, CODE_SESSION_EXPIRED, "Assistant session has expired.")


def origin_rejected() -> ApiException:
    return assistant_error(403, CODE_ORIGIN_REJECTED, "Origin is not allowed.")


def csrf_failed() -> ApiException:
    return assistant_error(403, CODE_CSRF_FAILED, "Assistant CSRF validation failed.")


def idempotency_conflict() -> ApiException:
    return assistant_error(409, CODE_IDEMPOTENCY_CONFLICT, "Idempotency key conflicts.")


def event_cursor_invalid() -> ApiException:
    return assistant_error(409, CODE_EVENT_CURSOR_INVALID, "Event cursor is invalid.")


def idempotency_expired() -> ApiException:
    return assistant_error(
        410, CODE_IDEMPOTENCY_EXPIRED, "The stored answer is no longer available."
    )


def limited(code: str, retry_after: int) -> ApiException:
    labels = {
        CODE_RATE_LIMITED: "Rate limit exceeded.",
        CODE_CONCURRENCY_LIMITED: "Concurrency limit exceeded.",
        CODE_BUDGET_EXHAUSTED: "Daily assistant budget is exhausted.",
        CODE_STREAM_LIMITED: "Too many live assistant streams.",
    }
    return assistant_error(429, code, labels.get(code, "Limit exceeded."), retry_after=retry_after)
