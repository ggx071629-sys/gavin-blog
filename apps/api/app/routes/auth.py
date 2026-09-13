from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select

from ..config import Settings
from ..dependencies import DbSession, require_admin, require_login_csrf, require_session_csrf
from ..models import AdminSession
from ..schemas import LoginRequest, SessionResponse
from ..security import CSRF_COOKIE, SESSION_COOKIE, begin_auth_write, expires_at, token, token_hash
from ..time_utils import utc_now

router = APIRouter(prefix="/auth", tags=["auth"])


class _CookieSettings(TypedDict):
    secure: bool
    samesite: Literal["lax"]
    path: str


def _cookie_settings(settings: Settings) -> _CookieSettings:
    return {
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "path": "/",
    }


@router.get("/csrf")
def issue_csrf(request: Request, response: Response) -> dict[str, str]:
    csrf = token()
    settings: Settings = request.app.state.settings
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        httponly=False,
        max_age=3600,
        **_cookie_settings(settings),
    )
    return {"csrf_token": csrf}


@router.post("/login", response_model=SessionResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: DbSession,
    _: Annotated[None, Depends(require_login_csrf)],
) -> SessionResponse:
    settings: Settings = request.app.state.settings
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{payload.username.lower()}"
    limiter = request.app.state.login_limiter
    if not limiter.allow(key):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="try later")
    begin_auth_write(db)
    if not request.app.state.admin_password.verify(payload.username, payload.password, db):
        db.commit()  # Preserve first initialization even if credentials are incorrect.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

    limiter.clear(key)
    db.execute(delete(AdminSession).where(AdminSession.expires_at <= utc_now()))
    oldest = list(
        db.scalars(
            select(AdminSession)
            .order_by(AdminSession.created_at.desc(), AdminSession.public_id.desc())
            .offset(99)
        )
    )
    for old_session in oldest:
        db.delete(old_session)
    session_token = token()
    csrf = token()
    db.add(
        AdminSession(
            token_hash=token_hash(session_token),
            csrf_hash=token_hash(csrf),
            expires_at=expires_at(settings),
        )
    )
    db.commit()
    max_age = settings.session_ttl_hours * 3600
    response.set_cookie(
        SESSION_COOKIE,
        session_token,
        httponly=True,
        max_age=max_age,
        **_cookie_settings(settings),
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        httponly=False,
        max_age=max_age,
        **_cookie_settings(settings),
    )
    return SessionResponse(username=settings.admin_username)


@router.get("/session", response_model=SessionResponse)
def session(
    request: Request,
    _: Annotated[AdminSession, Depends(require_admin)],
) -> SessionResponse:
    return SessionResponse(username=request.app.state.settings.admin_username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: DbSession,
    session_record: Annotated[AdminSession, Depends(require_session_csrf)],
) -> Response:
    db.delete(session_record)
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
