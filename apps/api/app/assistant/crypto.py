from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import date
from typing import Any


def random_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def random_id() -> str:
    return secrets.token_hex(16)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hmac_hex(secret: str | bytes, value: str, *, context: str = "") -> str:
    key = secret.encode("utf-8") if isinstance(secret, str) else secret
    payload = f"{context}|{value}" if context else value
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def session_csrf_token(secret: str, session_id: str) -> str:
    """Session-bound deterministic CSRF using an independent HMAC domain."""
    return hmac_hex(secret, session_id, context="assistant-csrf-token")


def compare(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return hmac.compare_digest(left, right)


def daily_ip_key(master: str, day: date) -> bytes:
    return hmac.new(
        master.encode("utf-8"),
        f"assistant-ip|{day.isoformat()}".encode(),
        hashlib.sha256,
    ).digest()


def ip_hmac(master: str, ip: str, day: date) -> str:
    return hmac.new(daily_ip_key(master, day), ip.encode("utf-8"), hashlib.sha256).hexdigest()


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def payload_hmac(secret: str, payload: Any) -> str:
    return hmac_hex(secret, canonical_json(payload), context="assistant-payload")
