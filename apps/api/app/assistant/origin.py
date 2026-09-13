from __future__ import annotations

from urllib.parse import urlparse

from fastapi import Request

from ..config import Settings
from .errors import origin_rejected


def canonical_origin(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise origin_rejected()
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise origin_rejected()
    return f"{parsed.scheme}://{parsed.netloc}"


def expected_origin(settings: Settings) -> str:
    return canonical_origin(str(settings.assistant_public_origin))


def _check_fetch_metadata(request: Request, *, require_same_origin: bool) -> None:
    site = request.headers.get("sec-fetch-site")
    if require_same_origin:
        if site != "same-origin":
            raise origin_rejected()
    elif site and site not in {"same-origin", "none"}:
        raise origin_rejected()
    mode = request.headers.get("sec-fetch-mode")
    if mode and mode not in {"cors", "same-origin", "navigate"}:
        raise origin_rejected()


def require_origin(request: Request, settings: Settings, *, require_fetch_metadata: bool) -> str:
    origin = request.headers.get("origin")
    if not origin:
        raise origin_rejected()
    expected = expected_origin(settings)
    actual = canonical_origin(origin)
    if actual != expected:
        raise origin_rejected()
    _check_fetch_metadata(request, require_same_origin=require_fetch_metadata)
    return actual


def _header_host(value: str | None) -> str:
    return (value or "").split(",", 1)[0].strip().lower()


def request_public_host(request: Request, settings: Settings) -> str:
    """Resolve the browser-facing host.

    Same-origin Nuxt fetch rewrites Host to the API listen address. Trust
    X-Forwarded-Host only when it exactly matches the configured public origin.
    """
    expected_host = urlparse(expected_origin(settings)).netloc.lower()
    forwarded = _header_host(request.headers.get("x-forwarded-host"))
    if forwarded == expected_host:
        return forwarded
    return _header_host(request.headers.get("host"))


def require_read_metadata(request: Request, settings: Settings) -> None:
    """GET status: production requires same-origin Fetch Metadata and the public host.

    Browsers usually omit Origin on GET; this check must not require it.
    """
    expected_host = urlparse(expected_origin(settings)).netloc.lower()
    host = request_public_host(request, settings)
    production = settings.environment == "production"
    if production:
        if host != expected_host:
            raise origin_rejected()
        _check_fetch_metadata(request, require_same_origin=True)
        return
    if host and host != expected_host and host != "testserver":
        raise origin_rejected()
    _check_fetch_metadata(request, require_same_origin=False)
