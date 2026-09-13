"""Run from apps/api: python -m app.reset_admin_password --database PATH --confirm-stopped."""

from __future__ import annotations

import argparse
import getpass
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import inspect

from .account import replace_password, validate_password
from .config import Settings
from .db import Database
from .models import AdminCredential
from .security import AdminPassword, begin_auth_write


def reset(settings: Settings, new_password: str) -> None:
    validate_password(new_password, settings.admin_username)
    database = Database(settings.database_url)
    try:
        if not {"admin_credentials", "admin_sessions", "account_challenges"} <= set(
            inspect(database.engine).get_table_names()
        ):
            raise RuntimeError("Database requires account migrations before reset")
        with database.session_factory() as db:
            begin_auth_write(db)
            passwords = AdminPassword(settings)
            credential: AdminCredential = passwords.credential(db)
            if passwords.verify(settings.admin_username, new_password, db):
                raise HTTPException(422, "password_unchanged")
            replace_password(db, credential, new_password)
            db.commit()
    finally:
        database.engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reset administrator password and revoke all sessions"
    )
    parser.add_argument(
        "--database", type=Path, required=True, help="Existing migrated SQLite file"
    )
    parser.add_argument("--confirm-stopped", action="store_true", help="Confirm API is stopped")
    args = parser.parse_args()
    if not args.confirm_stopped:
        parser.error("Stop the API, back up the database, then pass --confirm-stopped")
    path = args.database.resolve(strict=True)
    if not path.is_file():
        parser.error("Database must be an existing file")
    settings = Settings(database_url=f"sqlite:///{path.as_posix()}")
    first = getpass.getpass("New password (15-128 characters): ")
    second = getpass.getpass("Repeat new password: ")
    if first != second:
        print("Passwords do not match; nothing changed.")
        return 1
    try:
        reset(settings, first)
    except HTTPException:
        print("Password rejected by policy; nothing changed.")
        return 1
    print("Password updated. All sessions and verification codes revoked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
