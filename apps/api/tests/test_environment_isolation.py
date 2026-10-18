from __future__ import annotations

import socket

import pytest

from app.config import Settings, get_settings


def test_global_test_settings_do_not_require_or_load_a_local_env_file(
    tmp_path, monkeypatch
) -> None:
    (tmp_path / ".env").write_text(
        "GAVIN_ADMIN_PASSWORD=developer-secret\nGAVIN_DATABASE_URL=sqlite:///polluted.db\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.admin_password == "test-only-password"
    assert settings.database_url == "sqlite:///./data/gavin.db"


def test_settings_ignore_a_polluted_local_env_file(tmp_path, monkeypatch) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(
            (
                "GAVIN_ENVIRONMENT=production",
                "GAVIN_DATABASE_URL=sqlite:///development.db",
                "GAVIN_MEDIA_ROOT=./development-media",
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    settings = Settings(
        environment="test",
        database_url="sqlite:///fixture.db",
        admin_password="test-only",
        cookie_secure=False,
        media_root="./fixture-media",
        _env_file=None,
    )

    assert settings.environment == "test"
    assert settings.database_url == "sqlite:///fixture.db"
    assert settings.media_root == "./fixture-media"


def test_non_loopback_network_is_denied_by_default() -> None:
    with pytest.raises(RuntimeError, match="non-loopback address"):
        socket.create_connection(("192.0.2.1", 80), timeout=0.01)
