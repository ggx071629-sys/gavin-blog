from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .db import get_db
from .models import AdminSession
from .security import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE, begin_auth_write, token_hash
from .time_utils import utc_now

DbSession = Annotated[Session, Depends(get_db)]


def require_admin(request: Request, db: DbSession) -> AdminSession:
    session_token = request.cookies.get(SESSION_COOKIE)
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    begin_auth_write(db)
    record = db.get(AdminSession, token_hash(session_token))
    if record is None or record.expires_at <= utc_now():
        if record is not None:
            db.delete(record)
            db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="session expired")
    record.last_seen_at = utc_now()
    db.commit()
    return record


def require_session_csrf(
    request: Request,
    session: Annotated[AdminSession, Depends(require_admin)],
) -> AdminSession:
    cookie = request.cookies.get(CSRF_COOKIE, "")
    header = request.headers.get(CSRF_HEADER, "")
    valid_pair = bool(cookie and header and hmac.compare_digest(cookie, header))
    valid_session = hmac.compare_digest(token_hash(header), session.csrf_hash) if header else False
    if not valid_pair or not valid_session:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid csrf token")
    return session


def require_login_csrf(request: Request) -> None:
    cookie = request.cookies.get(CSRF_COOKIE, "")
    header = request.headers.get(CSRF_HEADER, "")
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid csrf token")
