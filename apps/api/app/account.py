"""Single-admin account transactions. Never log credentials or delivery exceptions."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import smtplib
import ssl
from collections.abc import Callable
from datetime import timedelta
from email.message import EmailMessage
from typing import Literal

from argon2 import PasswordHasher
from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from .config import Settings
from .models import AccountAttempt, AccountChallenge, AdminCredential, AdminSession
from .security import AdminPassword, begin_auth_write, token, token_hash
from .time_utils import utc_now

Purpose = Literal["change", "recovery"]
Sender = Callable[[Settings, str, Purpose], None]


def mail_available(settings: Settings) -> bool:
    return bool(
        "@" in settings.admin_email
        and "@" in settings.smtp_username
        and settings.smtp_host
        and settings.smtp_password.get_secret_value()
        and len(settings.account_code_secret.get_secret_value()) >= 32
        and not any(c in settings.admin_email + settings.smtp_username for c in "\r\n")
    )


def send_mail(settings: Settings, code: str, purpose: Purpose) -> None:
    message = EmailMessage()
    message["Subject"] = "写作台修改密码验证码" if purpose == "change" else "写作台密码恢复验证码"
    message["From"] = settings.smtp_username
    message["To"] = settings.admin_email
    message.set_content(f"验证码：{code}\n10 分钟内有效，仅用于本次密码操作。若非本人操作请忽略。")
    with smtplib.SMTP_SSL(
        settings.smtp_host, settings.smtp_port, timeout=10, context=ssl.create_default_context()
    ) as smtp:
        smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        refused = smtp.send_message(message)
        if refused:
            raise RuntimeError("delivery refused")


def masked_email(value: str) -> str | None:
    if "@" not in value:
        return None
    local, domain = value.rsplit("@", 1)
    return f"{local[:1]}***@{domain}"


def require_live_session(db: Session, session_hash: str | None) -> None:
    if session_hash is None:
        return
    session = db.get(AdminSession, session_hash)
    if session is None or session.expires_at <= utc_now():
        raise HTTPException(401, "not authenticated")


def reserve_attempt(db: Session, kind: str, purpose: str, ip: str) -> None:
    now = utc_now()
    db.execute(delete(AccountAttempt).where(AccountAttempt.created_at <= now - timedelta(days=1)))
    rows = list(db.scalars(select(AccountAttempt).where(AccountAttempt.kind == kind)))
    ip_digest = token_hash(ip)
    hour = [r for r in rows if r.created_at > now - timedelta(hours=1)]
    waits: list[int] = []
    if kind == "send":
        same = [r for r in rows if r.purpose == purpose]
        if same:
            remaining = 60 - int((now - max(r.created_at for r in same)).total_seconds())
            if remaining > 0:
                waits.append(remaining)
        if len(rows) >= 20:
            waits.append(
                int((min(r.created_at for r in rows) + timedelta(days=1) - now).total_seconds()) + 1
            )
        if len(hour) >= 10:
            waits.append(
                int((min(r.created_at for r in hour) + timedelta(hours=1) - now).total_seconds())
                + 1
            )
    elif len(hour) >= 30:
        waits.append(3600)
    if len([r for r in hour if r.ip_hash == ip_digest]) >= 20:
        waits.append(3600)
    if waits:
        raise HTTPException(429, "try later", headers={"Retry-After": str(max(waits))})
    db.add(AccountAttempt(kind=kind, purpose=purpose, ip_hash=ip_digest, created_at=now))


def challenge_digest(settings: Settings, record: AccountChallenge, code: str) -> str:
    data = f"{record.id}:{record.purpose}:{record.credential_version}:{settings.admin_email}:{code}"
    return hmac.new(
        settings.account_code_secret.get_secret_value().encode(), data.encode(), hashlib.sha256
    ).hexdigest()


def check_current_password(
    db: Session, passwords: AdminPassword, current_password: str | None, purpose: Purpose
) -> None:
    if purpose == "change" and (
        current_password is None or not passwords.verify(passwords.username, current_password, db)
    ):
        db.commit()
        raise HTTPException(400, "invalid_current_password")


def issue_code(
    db: Session,
    settings: Settings,
    passwords: AdminPassword,
    purpose: Purpose,
    ip: str,
    sender: Sender,
    session_hash: str | None = None,
    current_password: str | None = None,
) -> str:
    if not mail_available(settings):
        raise HTTPException(503, "mail_unavailable")
    begin_auth_write(db)
    require_live_session(db, session_hash)
    reserve_attempt(db, "verify", purpose, ip)
    check_current_password(db, passwords, current_password, purpose)
    reserve_attempt(db, "send", purpose, ip)
    credential = passwords.credential(db)
    now = utc_now()
    db.execute(
        delete(AccountChallenge).where(AccountChallenge.expires_at < now - timedelta(days=1))
    )
    code = f"{secrets.randbelow(1_000_000):06d}"
    pending = AccountChallenge(
        id=token(),
        purpose=purpose,
        credential_version=credential.version,
        digest="",
        state="pending",
        attempts=0,
        created_at=now,
        expires_at=now + timedelta(minutes=10),
    )
    pending.digest = challenge_digest(settings, pending, code)
    challenge_id = pending.id
    db.add(pending)
    db.commit()
    delivered = False
    try:
        sender(settings, code, purpose)
        delivered = True
    except Exception:
        pass  # SMTP exception strings can contain private addresses or credentials.
    begin_auth_write(db)
    record = db.get(AccountChallenge, challenge_id)
    credential = db.get(AdminCredential, 1)
    newer = db.scalar(
        select(AccountChallenge.id)
        .where(
            AccountChallenge.purpose == purpose,
            AccountChallenge.created_at > now,
        )
        .limit(1)
    )
    valid = bool(
        record
        and credential
        and delivered
        and newer is None
        and record.credential_version == credential.version
        and record.state == "pending"
        and record.expires_at > utc_now()
    )
    if record is not None:
        if valid:
            db.execute(
                update(AccountChallenge)
                .where(
                    AccountChallenge.purpose == purpose,
                    AccountChallenge.state == "active",
                )
                .values(state="superseded")
            )
        record.state = "active" if valid else "failed"
    db.commit()
    if not valid:
        raise HTTPException(503, "mail_unavailable")
    return challenge_id


def validate_password(value: str, username: str) -> None:
    weak = {"passwordpassword", "correcthorsebatterystaple", "123456789012345", "password123456789"}
    if (
        not 15 <= len(value) <= 128
        or not value.strip()
        or len(set(value)) == 1
        or value.casefold() == username.casefold()
        or value.casefold() in weak
    ):
        raise HTTPException(422, "invalid_new_password")


def consume_code(
    db: Session,
    settings: Settings,
    credential: AdminCredential,
    purpose: Purpose,
    challenge_id: str,
    code: str,
) -> None:
    record = db.get(AccountChallenge, challenge_id)
    valid = bool(
        mail_available(settings)
        and record
        and record.purpose == purpose
        and record.credential_version == credential.version
        and record.state == "active"
        and record.expires_at > utc_now()
        and record.attempts < 5
    )
    if not valid or record is None:
        db.commit()
        raise HTTPException(400, "invalid_code")
    if not hmac.compare_digest(record.digest, challenge_digest(settings, record, code)):
        record.attempts += 1
        if record.attempts >= 5:
            record.state = "exhausted"
        db.commit()
        raise HTTPException(400, "invalid_code")
    record.state = "used"


def replace_password(db: Session, credential: AdminCredential, new_password: str) -> None:
    credential.password_hash = PasswordHasher().hash(new_password)
    credential.version += 1
    db.execute(delete(AdminSession))
    db.execute(update(AccountChallenge).values(state="invalidated"))


def change_password(
    db: Session,
    settings: Settings,
    passwords: AdminPassword,
    purpose: Purpose,
    ip: str,
    new_password: str,
    challenge_id: str,
    code: str,
    session_hash: str | None = None,
    current_password: str | None = None,
) -> None:
    validate_password(new_password, settings.admin_username)
    begin_auth_write(db)
    require_live_session(db, session_hash)
    reserve_attempt(db, "verify", purpose, ip)
    check_current_password(db, passwords, current_password, purpose)
    credential = passwords.credential(db)
    consume_code(db, settings, credential, purpose, challenge_id, code)
    if passwords.verify(passwords.username, new_password, db):
        used = db.get(AccountChallenge, challenge_id)
        if used is not None:
            used.state = "active"
        db.commit()
        raise HTTPException(422, "password_unchanged")
    replace_password(db, credential, new_password)
    db.commit()
