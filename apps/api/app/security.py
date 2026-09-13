from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import Settings
from .time_utils import utc_now

SESSION_COOKIE = "gavin_session"
CSRF_COOKIE = "gavin_csrf"
CSRF_HEADER = "x-csrf-token"


def token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def expires_at(settings: Settings) -> datetime:
    return utc_now() + timedelta(hours=settings.session_ttl_hours)


class AdminPassword:
    def __init__(self, settings: Settings) -> None:
        self.username = settings.admin_username
        self._hasher = PasswordHasher()
        self._initial_password = settings.admin_password

    def credential(self, db: Session):
        from .models import AdminCredential

        record = db.get(AdminCredential, 1)
        if record is None:
            record = AdminCredential(
                id=1, password_hash=self._hasher.hash(self._initial_password), version=1
            )
            db.add(record)
            db.flush()
        return record

    def verify(self, username: str, password: str, db: Session) -> bool:
        if not hmac.compare_digest(username, self.username):
            return False
        try:
            return self._hasher.verify(self.credential(db).password_hash, password)
        except VerificationError:
            return False


def begin_auth_write(db: Session) -> None:
    """Serialize credential checks and session writes across SQLite processes."""
    db.rollback()
    db.expire_all()
    db.execute(text("BEGIN IMMEDIATE"))


class LoginRateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            attempts = self._attempts[key]
            while attempts and now - attempts[0] >= self.window_seconds:
                attempts.popleft()
            if len(attempts) >= self.limit:
                return False
            attempts.append(now)
            return True

    def clear(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)
