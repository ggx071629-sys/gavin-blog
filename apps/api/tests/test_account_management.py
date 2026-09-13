from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from argon2 import PasswordHasher
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import account
from app.models import AccountAttempt, AccountChallenge, AdminCredential
from app.security import AdminPassword, begin_auth_write
from app.time_utils import utc_now

from .conftest import login


def test_password_change_requires_both_factors_and_revokes_every_session(client):
    configure_mail(client)
    codes = []
    client.app.state.account_sender = lambda s, c, p: codes.append(c)
    login(client)
    with TestClient(client.app) as other:
        login(other)
        headers = {"X-CSRF-Token": client.cookies.get("gavin_csrf")}
        assert (
            client.post(
                "/api/v1/auth/account/code", json={"current_password": "correct-horse"}
            ).status_code
            == 403
        )
        issued = client.post(
            "/api/v1/auth/account/code", headers=headers, json={"current_password": "correct-horse"}
        )
        assert issued.status_code == 202 and issued.headers["cache-control"] == "no-store"
        payload = dict(
            current_password="wrong",
            new_password="new-password-long-enough",
            challenge_id=issued.json()["challenge_id"],
            code=codes[0],
        )
        assert (
            client.post("/api/v1/auth/account/password", headers=headers, json=payload).status_code
            == 400
        )
        payload["current_password"] = "correct-horse"
        payload["code"] = "999999" if codes[0] != "999999" else "000000"
        assert (
            client.post("/api/v1/auth/account/password", headers=headers, json=payload).status_code
            == 400
        )
        payload["code"] = codes[0]
        changed = client.post("/api/v1/auth/account/password", headers=headers, json=payload)
        assert changed.status_code == 204
        assert client.get("/api/v1/auth/session").status_code == 401
        assert other.get("/api/v1/auth/session").status_code == 401
    from app.main import create_app

    restarted = create_app(client.app.state.settings)
    with TestClient(restarted) as fresh:
        csrf = fresh.get("/api/v1/auth/csrf").json()["csrf_token"]
        headers = {"X-CSRF-Token": csrf}
        assert (
            fresh.post(
                "/api/v1/auth/login",
                headers=headers,
                json={"username": "gavin", "password": "correct-horse"},
            ).status_code
            == 401
        )
        assert (
            fresh.post(
                "/api/v1/auth/login",
                headers=headers,
                json={"username": "gavin", "password": payload["new_password"]},
            ).status_code
            == 200
        )
    restarted.state.database.engine.dispose()


def test_credential_persists_across_password_service_restart(client):
    login(client)
    settings = client.app.state.settings
    with client.app.state.database.session_factory() as db:
        record = db.get(AdminCredential, 1)
        assert record.password_hash.startswith("$argon2id$")
        record.password_hash = PasswordHasher().hash("a-new-persistent-password")
        record.version += 1
        db.commit()

    settings.admin_password = "changed-config-must-not-win"
    restarted = AdminPassword(settings)
    with client.app.state.database.session_factory() as db:
        begin_auth_write(db)
        assert restarted.verify("gavin", "a-new-persistent-password", db)
        assert not restarted.verify("gavin", "correct-horse", db)
        assert not restarted.verify("gavin", settings.admin_password, db)
        db.commit()


def configure_mail(client):
    settings = client.app.state.settings
    settings.admin_email = "owner@163.com"
    settings.smtp_username = "owner@163.com"
    from pydantic import SecretStr

    settings.smtp_password = SecretStr("test-only-authorization")
    settings.account_code_secret = SecretStr("test-only-independent-code-secret-32")
    return settings


def test_anonymous_recovery_revokes_sessions_and_rejects_reuse(client):
    configure_mail(client)
    codes = []
    client.app.state.account_sender = lambda s, c, p: codes.append(c)
    login(client)
    with TestClient(client.app) as anonymous:
        assert anonymous.post("/api/v1/auth/recovery/code").status_code == 403
        csrf = anonymous.get("/api/v1/auth/csrf").json()["csrf_token"]
        headers = {"X-CSRF-Token": csrf}
        issued = anonymous.post("/api/v1/auth/recovery/code", headers=headers)
        assert issued.status_code == 202
        assert "owner@163.com" not in issued.text and codes[0] not in issued.text
        payload = dict(
            new_password="recovered-password-long-enough",
            challenge_id=issued.json()["challenge_id"],
            code=codes[0],
        )
        assert (
            anonymous.post(
                "/api/v1/auth/recovery/password", headers=headers, json=payload
            ).status_code
            == 204
        )
        assert client.get("/api/v1/auth/session").status_code == 401
        headers = {"X-CSRF-Token": anonymous.get("/api/v1/auth/csrf").json()["csrf_token"]}
        assert (
            anonymous.post(
                "/api/v1/auth/recovery/password",
                headers=headers,
                json={**payload, "new_password": "another-password-long-enough"},
            ).status_code
            == 400
        )


def test_session_list_activity_and_revoke_scopes(client):
    login(client)
    headers = {"X-CSRF-Token": client.cookies.get("gavin_csrf")}
    with TestClient(client.app) as other:
        login(other)
        listed = client.get("/api/v1/auth/sessions")
        assert listed.status_code == 200
        rows = listed.json()["items"]
        assert len(rows) == 2 and sum(r["is_current"] for r in rows) == 1
        assert all(r["last_seen_at"] >= r["created_at"] for r in rows)
        assert "token_hash" not in listed.text and "csrf" not in listed.text
        current_id = next(r["id"] for r in rows if r["is_current"])
        other_id = next(r["id"] for r in rows if not r["is_current"])
        assert client.delete(f"/api/v1/auth/sessions/{other_id}").status_code == 403
        assert (
            client.delete(f"/api/v1/auth/sessions/{other_id}", headers=headers).status_code == 204
        )
        assert other.get("/api/v1/auth/session").status_code == 401
        assert client.get("/api/v1/auth/session").status_code == 200
        login(other)
        assert client.delete("/api/v1/auth/sessions/others", headers=headers).status_code == 204
        assert other.get("/api/v1/auth/session").status_code == 401
        assert (
            client.delete(f"/api/v1/auth/sessions/{current_id}", headers=headers).status_code == 204
        )
        assert client.get("/api/v1/auth/session").status_code == 401


def test_terminal_reset_without_mail_revokes_all_sessions(client, monkeypatch, capsys):
    from app.reset_admin_password import main

    login(client)
    with TestClient(client.app) as other:
        login(other)
        path = client.app.state.settings.database_url.removeprefix("sqlite:///")
        monkeypatch.setattr("sys.argv", ["reset", "--database", path, "--confirm-stopped"])
        monkeypatch.setattr("getpass.getpass", lambda prompt: "terminal-recovery-password")
        assert main() == 0
        assert "terminal-recovery-password" not in capsys.readouterr().out
        assert client.get("/api/v1/auth/session").status_code == 401
        assert other.get("/api/v1/auth/session").status_code == 401
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        assert (
            client.post(
                "/api/v1/auth/login",
                headers={"X-CSRF-Token": csrf},
                json={"username": "gavin", "password": "terminal-recovery-password"},
            ).status_code
            == 200
        )


def test_concurrent_recovery_consumes_code_once(client):
    settings = configure_mail(client)
    passwords = client.app.state.admin_password
    captured = []
    with client.app.state.database.session_factory() as db:
        cid = account.issue_code(
            db, settings, passwords, "recovery", "local", lambda s, c, p: captured.append(c)
        )

    def worker(number):
        with client.app.state.database.session_factory() as db:
            try:
                account.change_password(
                    db,
                    settings,
                    passwords,
                    "recovery",
                    "local",
                    f"concurrent-password-{number}",
                    cid,
                    captured[0],
                )
                return 204
            except HTTPException as exc:
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(worker, [1, 2]))
    assert sorted(outcomes) == [204, 400]
    with client.app.state.database.session_factory() as db:
        assert db.get(AdminCredential, 1).version == 2


def test_concurrent_old_login_cannot_leave_session_after_reset(client):
    from threading import Barrier

    from app.reset_admin_password import reset

    login(client)
    barrier = Barrier(2)

    def attempt_login():
        with TestClient(client.app) as contender:
            csrf = contender.get("/api/v1/auth/csrf").json()["csrf_token"]
            barrier.wait(timeout=5)
            response = contender.post(
                "/api/v1/auth/login",
                headers={"X-CSRF-Token": csrf},
                json={"username": "gavin", "password": "correct-horse"},
            )
            return response.status_code, dict(contender.cookies)

    def do_reset():
        barrier.wait(timeout=5)
        reset(client.app.state.settings, "concurrent-reset-password")

    with ThreadPoolExecutor(max_workers=2) as pool:
        login_future = pool.submit(attempt_login)
        reset_future = pool.submit(do_reset)
        result, cookies = login_future.result(timeout=10)
        reset_future.result(timeout=10)
    assert result in {200, 401}
    if result == 200:
        with TestClient(client.app) as old:
            old.cookies.update(cookies)
            assert old.get("/api/v1/auth/session").status_code == 401
    assert client.get("/api/v1/auth/session").status_code == 401


def test_inflight_mail_cannot_survive_emergency_reset(client):
    from app.reset_admin_password import reset

    settings = configure_mail(client)

    def sender(*args):
        reset(settings, "emergency-password-inflight")

    with client.app.state.database.session_factory() as db:
        with pytest.raises(HTTPException) as error:
            account.issue_code(
                db, settings, client.app.state.admin_password, "recovery", "local", sender
            )
        assert error.value.status_code == 503
        from sqlalchemy import select

        assert not list(
            db.scalars(select(AccountChallenge).where(AccountChallenge.state == "active"))
        )


def test_recovery_does_not_reveal_password_match_without_code(client):
    configure_mail(client)
    from app.reset_admin_password import reset

    reset(client.app.state.settings, "current-password-long-enough")
    headers = {"X-CSRF-Token": client.get("/api/v1/auth/csrf").json()["csrf_token"]}
    response = client.post(
        "/api/v1/auth/recovery/password",
        headers=headers,
        json={
            "new_password": "current-password-long-enough",
            "challenge_id": "unknown",
            "code": "123456",
        },
    )
    assert response.status_code == 400 and response.json()["detail"] == "invalid_code"


def test_account_contract_matches_generated_snapshot(client):
    import json
    from pathlib import Path

    snapshot = json.loads(
        (Path(__file__).resolve().parents[3] / "packages/contracts/openapi.json").read_text(
            encoding="utf-8"
        )
    )
    actual = client.app.openapi()
    for path, operations in actual["paths"].items():
        if path.startswith("/api/v1/auth/"):
            assert snapshot["paths"][path] == operations
    for name in [
        "AccountInfo",
        "CodeIssued",
        "PasswordChange",
        "NewPassword",
        "SessionList",
        "SessionItem",
        "RecoveryCodeRequest",
    ]:
        assert snapshot["components"]["schemas"][name] == actual["components"]["schemas"][name]


def test_populated_legacy_database_upgrade(client, tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text

    from app.config import get_settings
    from app.main import create_app

    url = f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}"
    monkeypatch.setenv("GAVIN_DATABASE_URL", url)
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "20260910_0025")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO admin_sessions (token_hash,csrf_hash,expires_at,created_at) "
                "VALUES ('old','old','2099-01-01','2026-01-01')"
            )
        )
    command.upgrade(Config("alembic.ini"), "head")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM admin_sessions")).scalar() == 0
        assert conn.execute(text("SELECT count(*) FROM admin_credentials")).scalar() == 0
    settings = client.app.state.settings.model_copy(update={"database_url": url})
    app = create_app(settings)
    with TestClient(app) as migrated:
        login(migrated)
        assert migrated.get("/api/v1/auth/session").status_code == 200
    app.state.database.engine.dispose()
    engine.dispose()
    get_settings.cache_clear()


def test_durable_send_budget_and_secret_rotation(client):
    settings = configure_mail(client)
    captured = []
    passwords = client.app.state.admin_password
    with client.app.state.database.session_factory() as db:
        cid = account.issue_code(
            db, settings, passwords, "recovery", "local", lambda s, c, p: captured.append(c)
        )
    from pydantic import SecretStr

    settings.account_code_secret = SecretStr("a-different-secret-at-least-32-characters")
    with client.app.state.database.session_factory() as db:
        begin_auth_write(db)
        with pytest.raises(HTTPException):
            account.consume_code(
                db, settings, passwords.credential(db), "recovery", cid, captured[0]
            )
        db.add_all(
            [
                AccountAttempt(
                    kind="send",
                    purpose="recovery",
                    ip_hash="x",
                    created_at=utc_now() - timedelta(minutes=5),
                )
                for _ in range(9)
            ]
        )
        db.commit()
    with client.app.state.database.session_factory() as db:
        with pytest.raises(HTTPException) as error:
            account.issue_code(
                db,
                settings,
                AdminPassword(settings),
                "change",
                "new-ip",
                lambda *a: None,
                current_password="correct-horse",
            )
        assert error.value.status_code == 429


def test_smtp_adapter_uses_verified_tls_and_fixed_recipient(client, monkeypatch):
    settings = configure_mail(client)
    observed = {}

    class FakeSMTP:
        def __init__(self, host, port, *, timeout, context):
            observed.update(host=host, port=port, timeout=timeout, context=context)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def login(self, username, password):
            observed["username"] = username

        def send_message(self, message):
            observed["to"] = message["To"]
            return {}

    monkeypatch.setattr(account.smtplib, "SMTP_SSL", FakeSMTP)
    account.send_mail(settings, "123456", "recovery")
    assert observed["to"] == settings.admin_email == observed["username"]
    assert observed["context"].check_hostname and observed["timeout"] == 10


def test_code_lifecycle_and_limits(client):
    settings = configure_mail(client)
    captured = []
    passwords = client.app.state.admin_password
    with client.app.state.database.session_factory() as db:
        cid = account.issue_code(
            db, settings, passwords, "recovery", "local", lambda s, c, p: captured.append(c)
        )
        record = db.get(AccountChallenge, cid)
        assert record.state == "active" and captured[0] not in record.digest
        with pytest.raises(HTTPException) as error:
            account.issue_code(db, settings, passwords, "recovery", "local", lambda *a: None)
        assert error.value.status_code == 429
        db.rollback()
        for _ in range(5):
            begin_auth_write(db)
            with pytest.raises(HTTPException):
                account.consume_code(
                    db,
                    settings,
                    passwords.credential(db),
                    "recovery",
                    cid,
                    "999999" if captured[0] != "999999" else "000000",
                )
        begin_auth_write(db)
        with pytest.raises(HTTPException):
            account.consume_code(
                db, settings, passwords.credential(db), "recovery", cid, captured[0]
            )
        assert db.get(AccountChallenge, cid).attempts == 5


def test_code_purpose_expiry_reuse_and_delivery_failure(client):
    settings = configure_mail(client)
    passwords = client.app.state.admin_password
    captured = []
    with client.app.state.database.session_factory() as db:
        cid = account.issue_code(
            db, settings, passwords, "recovery", "local", lambda s, c, p: captured.append(c)
        )
        begin_auth_write(db)
        with pytest.raises(HTTPException):
            account.consume_code(db, settings, passwords.credential(db), "change", cid, captured[0])
        begin_auth_write(db)
        account.consume_code(db, settings, passwords.credential(db), "recovery", cid, captured[0])
        db.commit()
        begin_auth_write(db)
        with pytest.raises(HTTPException):
            account.consume_code(
                db, settings, passwords.credential(db), "recovery", cid, captured[0]
            )
        begin_auth_write(db)
        record = db.get(AccountChallenge, cid)
        record.state = "active"
        record.expires_at = utc_now() - timedelta(seconds=1)
        db.commit()
        begin_auth_write(db)
        with pytest.raises(HTTPException):
            account.consume_code(
                db, settings, passwords.credential(db), "recovery", cid, captured[0]
            )
        db.rollback()

        def failing_sender(*args):
            raise RuntimeError("sensitive-provider-error-must-not-escape")

        with pytest.raises(HTTPException) as error:
            account.issue_code(
                db,
                settings,
                passwords,
                "change",
                "local",
                failing_sender,
                current_password="correct-horse",
            )
        assert error.value.status_code == 503 and error.value.detail == "mail_unavailable"
