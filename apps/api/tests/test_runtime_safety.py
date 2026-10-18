from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.config import Settings


def test_operator_env_example_tracks_settings_fields() -> None:
    internal_test_fields = {"assistant_test_startup_bootstrap"}
    expected = {
        f"GAVIN_{field.upper()}"
        for field in Settings.model_fields
        if field not in internal_test_fields
    }
    example = Path(__file__).resolve().parents[1] / ".env.example"
    documented = set(re.findall(r"\bGAVIN_[A-Z0-9_]+\b", example.read_text(encoding="utf-8")))

    assert documented == expected


def test_runtime_settings_fail_closed() -> None:
    assert Settings.model_fields["admin_password"].is_required()
    safe_defaults = Settings(
        environment="production",
        admin_password="a-strong-production-password",
        _env_file=None,
    )
    assert safe_defaults.environment == "production"
    assert safe_defaults.cookie_secure is True

    with pytest.raises(ValidationError):
        Settings(admin_password="configured", session_ttl_hours=0, _env_file=None)
    with pytest.raises(ValidationError):
        Settings(admin_password="configured", media_max_pixels=-1, _env_file=None)


def test_production_rejects_insecure_cookie_and_default_password() -> None:
    with pytest.raises(RuntimeError, match="GAVIN_ADMIN_PASSWORD"):
        Settings(
            environment="production",
            admin_password="change-me",
            _env_file=None,
        ).validate_runtime()
    with pytest.raises(RuntimeError, match="GAVIN_COOKIE_SECURE"):
        Settings(
            environment="production",
            admin_password="a-strong-production-password",
            cookie_secure=False,
            _env_file=None,
        ).validate_runtime()
    with pytest.raises(RuntimeError, match="GAVIN_CORS_ORIGINS"):
        Settings(
            environment="production",
            admin_password="a-strong-production-password",
            cors_origins="*",
            _env_file=None,
        ).validate_runtime()


def test_sqlite_connections_enforce_foreign_keys(client: TestClient) -> None:
    engine = client.app.state.database.engine
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text("INSERT INTO article_tags(article_id, tag_id) VALUES (999999, 999999)")
        )
