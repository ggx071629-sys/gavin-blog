from __future__ import annotations

import ipaddress
import time

from fastapi import Request

from ..config import Settings
from .crypto import compare, hmac_hex
from .errors import invalid_request

PROXY_TIMESTAMP_HEADER = "X-Gavin-Client-IP-Timestamp"
PROXY_SIGNATURE_HEADER = "X-Gavin-Client-IP-Signature"


def peer_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "0.0.0.0"


def _parse_ip(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    text = value.strip()
    if text in {"testclient", "localhost"}:
        return ipaddress.ip_address("127.0.0.1")
    try:
        return ipaddress.ip_address(text)
    except ValueError as exc:
        raise invalid_request("Client IP is malformed.") from exc


def _signature_payload(request: Request, ip: str, timestamp: str) -> str:
    return "\n".join((request.method.upper(), request.url.path, ip, timestamp))


def client_ip(request: Request, settings: Settings, *, now_seconds: int | None = None) -> str:
    peer = peer_ip(request)
    trusted = []
    for item in settings.assistant_trusted_proxy_cidrs:
        trusted.append(ipaddress.ip_network(item, strict=False))
    peer_addr = _parse_ip(peer)
    if not any(peer_addr in network for network in trusted):
        return str(peer_addr)
    header_name = settings.assistant_client_ip_header
    if not header_name:
        raise invalid_request("Trusted proxy identity is not configured.")
    raw = request.headers.get(header_name)
    if raw is None:
        raise invalid_request("Trusted proxy identity is missing.")
    if "," in raw:
        raise invalid_request("Client IP identity must contain exactly one address.")
    try:
        resolved_ip = str(_parse_ip(raw))
    except ValueError as exc:
        raise invalid_request("Client IP identity is malformed.") from exc
    timestamp = request.headers.get(PROXY_TIMESTAMP_HEADER)
    signature = request.headers.get(PROXY_SIGNATURE_HEADER)
    if not timestamp or not signature or not timestamp.isdigit():
        raise invalid_request("Trusted proxy signature is missing.")
    current = int(time.time()) if now_seconds is None else now_seconds
    maximum_skew = int(settings.assistant_proxy_max_clock_skew_seconds or 0)
    if maximum_skew <= 0 or abs(current - int(timestamp)) > maximum_skew:
        raise invalid_request("Trusted proxy signature is stale.")
    secret = str(settings.assistant_proxy_hmac_secret or "")
    expected = hmac_hex(
        secret,
        _signature_payload(request, resolved_ip, timestamp),
        context="assistant-proxy-identity-v1",
    )
    if not compare(signature, expected):
        raise invalid_request("Trusted proxy signature is invalid.")
    return resolved_ip
