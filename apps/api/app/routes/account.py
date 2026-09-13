from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select

from .. import account
from ..dependencies import DbSession, require_admin, require_login_csrf, require_session_csrf
from ..models import AdminSession
from ..security import CSRF_COOKIE, SESSION_COOKIE, begin_auth_write
from ..time_utils import utc_now

router = APIRouter(prefix="/auth", tags=["account"])


class AccountInfo(BaseModel):
    username: str
    email_masked: str | None
    mail_available: bool


class SessionItem(BaseModel):
    id: str
    created_at: datetime
    last_seen_at: datetime
    is_current: bool


class SessionList(BaseModel):
    items: list[SessionItem]


class CurrentPassword(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=512)


class RecoveryCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NewPassword(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_password: str = Field(min_length=15, max_length=128)
    challenge_id: str = Field(min_length=1, max_length=64)
    code: str = Field(pattern=r"^[0-9]{6}$")


class PasswordChange(NewPassword):
    current_password: str = Field(min_length=1, max_length=512)


class CodeIssued(BaseModel):
    challenge_id: str
    expires_in: int = 600
    retry_after: int = 60


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def clear_session(response: Response) -> Response:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    response.status_code = 204
    return response


@router.get("/account", response_model=AccountInfo)
def account_info(request: Request, _: Annotated[AdminSession, Depends(require_admin)]):
    settings = request.app.state.settings
    return AccountInfo(
        username=settings.admin_username,
        email_masked=account.masked_email(settings.admin_email),
        mail_available=account.mail_available(settings),
    )


@router.post("/account/code", status_code=202, response_model=CodeIssued)
def change_code(
    payload: CurrentPassword,
    request: Request,
    db: DbSession,
    session: Annotated[AdminSession, Depends(require_session_csrf)],
):
    cid = account.issue_code(
        db,
        request.app.state.settings,
        request.app.state.admin_password,
        "change",
        client_ip(request),
        getattr(request.app.state, "account_sender", account.send_mail),
        session.token_hash,
        payload.current_password,
    )
    return CodeIssued(challenge_id=cid)


@router.post("/account/password", status_code=204)
def update_password(
    payload: PasswordChange,
    request: Request,
    response: Response,
    db: DbSession,
    session: Annotated[AdminSession, Depends(require_session_csrf)],
):
    account.change_password(
        db,
        request.app.state.settings,
        request.app.state.admin_password,
        "change",
        client_ip(request),
        payload.new_password,
        payload.challenge_id,
        payload.code,
        session.token_hash,
        payload.current_password,
    )
    return clear_session(response)


@router.post("/recovery/code", status_code=202, response_model=CodeIssued)
def recovery_code(
    request: Request,
    db: DbSession,
    _: Annotated[None, Depends(require_login_csrf)],
    payload: RecoveryCodeRequest | None = None,
):
    cid = account.issue_code(
        db,
        request.app.state.settings,
        request.app.state.admin_password,
        "recovery",
        client_ip(request),
        getattr(request.app.state, "account_sender", account.send_mail),
    )
    return CodeIssued(challenge_id=cid)


@router.post("/recovery/password", status_code=204)
def recover_password(
    payload: NewPassword,
    request: Request,
    response: Response,
    db: DbSession,
    _: Annotated[None, Depends(require_login_csrf)],
):
    account.change_password(
        db,
        request.app.state.settings,
        request.app.state.admin_password,
        "recovery",
        client_ip(request),
        payload.new_password,
        payload.challenge_id,
        payload.code,
    )
    return clear_session(response)


@router.get("/sessions", response_model=SessionList)
def list_sessions(db: DbSession, current: Annotated[AdminSession, Depends(require_admin)]):
    records = db.scalars(
        select(AdminSession)
        .where(AdminSession.expires_at > utc_now())
        .order_by(AdminSession.created_at.desc(), AdminSession.public_id.desc())
        .limit(100)
    )
    return SessionList(
        items=[
            SessionItem(
                id=r.public_id,
                created_at=r.created_at,
                last_seen_at=r.last_seen_at,
                is_current=r.token_hash == current.token_hash,
            )
            for r in records
        ]
    )


@router.delete("/sessions/others", status_code=204)
def revoke_others(db: DbSession, current: Annotated[AdminSession, Depends(require_session_csrf)]):
    current_hash = current.token_hash
    begin_auth_write(db)
    account.require_live_session(db, current_hash)
    db.execute(delete(AdminSession).where(AdminSession.token_hash != current_hash))
    db.commit()
    return Response(status_code=204)


@router.delete("/sessions/{session_id}", status_code=204)
def revoke_session(
    session_id: str,
    response: Response,
    db: DbSession,
    current: Annotated[AdminSession, Depends(require_session_csrf)],
):
    current_hash, current_id = current.token_hash, current.public_id
    begin_auth_write(db)
    account.require_live_session(db, current_hash)
    db.execute(delete(AdminSession).where(AdminSession.public_id == session_id))
    db.commit()
    if session_id == current_id:
        return clear_session(response)
    return Response(status_code=204)
