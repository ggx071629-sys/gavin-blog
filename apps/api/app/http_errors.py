from __future__ import annotations


class ApiException(Exception):
    """Structured API error whose body is exactly {"error": {"code", "message"}}."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        retry_after: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retry_after = retry_after
        self.headers = headers or {}
