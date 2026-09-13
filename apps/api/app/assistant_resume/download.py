from __future__ import annotations

import base64
import hashlib
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit

MAX_BYTES = 10 * 1024 * 1024
MAX_REDIRECTS = 3
TOTAL_SECONDS = 30
HOST_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
ERROR_CODES = frozenset(
    {
        "blocked_host",
        "download_timeout",
        "download_failed",
        "too_large",
        "not_pdf",
    }
)


class DownloadError(Exception):
    def __init__(self, code: str, *, transient: bool = False, retry_after: int | None = None):
        super().__init__(code)
        self.code = code
        self.transient = transient
        self.retry_after = retry_after


@dataclass(frozen=True)
class DownloadedPdf:
    body: bytes
    sha256: str


def _host(value: str) -> str:
    try:
        host = value.encode("idna").decode("ascii").lower()
        if len(host) > 253 or not all(HOST_LABEL.fullmatch(part) for part in host.split(".")):
            raise ValueError
        try:
            ipaddress.ip_address(host)
        except ValueError:
            return host
    except (UnicodeError, ValueError):
        pass
    raise DownloadError("blocked_host")


def checked_url(url: str, trusted_hosts: tuple[str, ...]) -> tuple[str, str]:
    try:
        if len(url) > 2048 or any(ord(c) < 33 or ord(c) == 127 for c in url) or "\\" in url:
            raise ValueError
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.port not in (None, 443)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise ValueError
        host = _host(parsed.hostname or "")
        allowed = {_host(item) for item in trusted_hosts}
        if host not in allowed:
            raise ValueError
        target = parsed.path or "/"
        if parsed.query:
            target += "?" + parsed.query
        target.encode("ascii")  # URLs must percent-encode non-ASCII path/query characters.
        return host, target
    except (ValueError, UnicodeError):
        raise DownloadError("blocked_host") from None


def _public_addresses(host: str, resolver) -> list[str]:
    records = resolver(host, 443, type=socket.SOCK_STREAM)
    addresses: list[str] = []
    for record in records:
        address = record[4][0]
        ip = ipaddress.ip_address(address)
        if (
            not ip.is_global
            or ip.is_multicast
            or ip.is_reserved
            or "%" in address
            or getattr(ip, "sixtofour", None)
            or getattr(ip, "teredo", None)
        ):
            raise DownloadError("blocked_host")
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise DownloadError("download_failed", transient=True)
    return addresses


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str, timeout: float):
        context = ssl.create_default_context()
        context.set_alpn_protocols(["http/1.1"])
        super().__init__(host, port=443, timeout=timeout, context=context)
        self.address = address
        self.tls_context = context

    def connect(self) -> None:
        ip = ipaddress.ip_address(self.address)
        raw = socket.socket(
            socket.AF_INET6 if ip.version == 6 else socket.AF_INET, socket.SOCK_STREAM
        )
        try:
            raw.settimeout(self.timeout)
            raw.connect((self.address, 443))
            self.sock = self.tls_context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def _retry_after(value: str | None) -> int | None:
    if not value:
        return None
    try:
        if value.isdecimal():
            seconds = int(value)
            if seconds > 2**31 - 1:
                raise DownloadError("download_failed")
            return seconds
        stamp = parsedate_to_datetime(value)
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=UTC)
        return max(0, int((stamp - datetime.now(UTC)).total_seconds()) + 1)
    except (ValueError, OverflowError):
        return None


def fetch_pdf(
    url: str,
    trusted_hosts: tuple[str, ...],
    *,
    force_refresh: bool = False,
    resolver=socket.getaddrinfo,
    connection_factory=PinnedHTTPSConnection,
    clock=time.monotonic,
) -> bytes:
    """Core IO; production callers use download_pdf for an independent total deadline."""
    deadline = clock() + TOTAL_SECONDS

    def remaining() -> float:
        value = deadline - clock()
        if value <= 0:
            raise DownloadError("download_timeout", transient=True)
        return min(5.0, value)

    try:
        for hop in range(MAX_REDIRECTS + 1):
            host, target = checked_url(url, trusted_hosts)
            addresses = _public_addresses(host, resolver)
            conn = connection_factory(host, addresses[0], remaining())
            try:
                headers = {"Accept": "application/pdf", "Accept-Encoding": "identity"}
                if force_refresh:
                    headers["Cache-Control"] = "no-cache"
                conn.request("GET", target, headers=headers)
                response = conn.getresponse()
                if response.status in (301, 302, 303, 307, 308):
                    location = response.getheader("Location")
                    if not location or len(location) > 2048 or hop == MAX_REDIRECTS:
                        raise DownloadError("download_failed")
                    url = urljoin(url, location)
                    continue
                if response.status != 200:
                    raise DownloadError(
                        "download_failed",
                        transient=response.status == 429 or response.status >= 500,
                        retry_after=_retry_after(response.getheader("Retry-After")),
                    )
                content_type = (
                    (response.getheader("Content-Type") or "").split(";")[0].strip().lower()
                )
                if content_type not in ("application/pdf", "application/octet-stream"):
                    raise DownloadError("not_pdf")
                if (
                    response.getheader("Content-Encoding") or "identity"
                ).strip().lower() != "identity":
                    raise DownloadError("not_pdf")
                length = response.getheader("Content-Length")
                if length is not None:
                    if not length.isdecimal():
                        raise DownloadError("download_failed")
                    if int(length) > MAX_BYTES:
                        raise DownloadError("too_large")
                body = bytearray()
                while True:
                    timeout = remaining()
                    if conn.sock is not None:
                        conn.sock.settimeout(timeout)
                    piece = response.read(min(65536, MAX_BYTES + 1 - len(body)))
                    if not piece:
                        break
                    body.extend(piece)
                    if len(body) > MAX_BYTES:
                        raise DownloadError("too_large")
                if not body.startswith(b"%PDF-"):
                    raise DownloadError("not_pdf")
                remaining()
                return bytes(body)
            finally:
                conn.close()
    except DownloadError:
        raise
    except TimeoutError:
        raise DownloadError("download_timeout", transient=True) from None
    except (OSError, ValueError, http.client.HTTPException):
        raise DownloadError("download_failed", transient=True) from None
    raise DownloadError("download_failed")


def worker_environment() -> dict[str, str]:
    env = {"PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
    for key in ("SystemRoot", "WINDIR"):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def download_pdf(
    url: str, trusted_hosts: tuple[str, ...], *, force_refresh: bool = False
) -> DownloadedPdf:
    checked_url(url, trusted_hosts)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "app.assistant_resume.download"],
            input=json.dumps(
                {"url": url, "trusted_hosts": trusted_hosts, "force_refresh": force_refresh}
            ).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=TOTAL_SECONDS,
            cwd=Path(__file__).resolve().parents[2],
            env=worker_environment(),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise DownloadError("download_timeout", transient=True) from None
    except OSError:
        raise DownloadError("download_failed") from None
    try:
        if result.returncode != 0 or len(result.stdout) > MAX_BYTES * 2:
            raise ValueError
        payload = json.loads(result.stdout)
        if "error" in payload:
            code = payload["error"] if payload["error"] in ERROR_CODES else "download_failed"
            raise DownloadError(
                code,
                transient=bool(payload.get("transient")),
                retry_after=payload.get("retry_after"),
            )
        body = base64.b64decode(payload["body"], validate=True)
        if len(body) > MAX_BYTES or not body.startswith(b"%PDF-"):
            raise ValueError
        return DownloadedPdf(body, hashlib.sha256(body).hexdigest())
    except (ValueError, TypeError, KeyError):
        raise DownloadError("download_failed") from None


def main() -> None:
    try:
        request = json.loads(sys.stdin.buffer.read(8192))
        body = fetch_pdf(
            request["url"],
            tuple(request["trusted_hosts"]),
            force_refresh=bool(request.get("force_refresh")),
        )
        result = {"body": base64.b64encode(body).decode("ascii")}
    except DownloadError as exc:
        result = {"error": exc.code, "transient": exc.transient, "retry_after": exc.retry_after}
    except Exception:
        result = {"error": "download_failed", "transient": False}
    sys.stdout.write(json.dumps(result))


if __name__ == "__main__":
    main()
