from __future__ import annotations

import logging
import os
import socket
from collections.abc import Generator
from ipaddress import ip_address
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.db import Base
from app.main import create_app


@pytest.fixture(autouse=True)
def keep_application_logging_capturable() -> None:
    """LangGraph/LangChain imports must not hide application ERROR logs from caplog."""
    logging.disable(logging.NOTSET)
    for name in ("", "app", "app.routes", "app.routes.media"):
        logger = logging.getLogger(name)
        logger.disabled = False
        logger.propagate = True


@pytest.fixture(autouse=True)
def isolate_gavin_settings(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Make every API test independent of the developer's environment and .env."""
    for key in tuple(os.environ):
        if key.startswith("GAVIN_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GAVIN_ADMIN_PASSWORD", "test-only-password")
    monkeypatch.setenv("GAVIN_ENVIRONMENT", "test")
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def deny_non_loopback_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep API tests hermetic while allowing explicit local test doubles."""
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def ensure_loopback(sock: socket.socket, address: Any) -> None:
        if sock.family not in (socket.AF_INET, socket.AF_INET6):
            return
        host = address[0]
        try:
            allowed = ip_address(host).is_loopback
        except ValueError:
            allowed = host == "localhost"
        if not allowed:
            raise RuntimeError(f"API tests cannot connect to non-loopback address: {host}")

    def guarded_connect(sock: socket.socket, address: Any) -> None:
        ensure_loopback(sock, address)
        return original_connect(sock, address)

    def guarded_connect_ex(sock: socket.socket, address: Any) -> int:
        ensure_loopback(sock, address)
        return original_connect_ex(sock, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)


@pytest.fixture
def client(tmp_path) -> Generator[TestClient, None, None]:
    database = tmp_path / "test.db"
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{database.as_posix()}",
        admin_username="gavin",
        admin_password="correct-horse",
        cookie_secure=False,
        login_limit=3,
        login_window_seconds=60,
        media_root=str(tmp_path / "media"),
        _env_file=None,
    )
    app = create_app(settings)
    Base.metadata.create_all(app.state.database.engine)
    with TestClient(app) as test_client:
        yield test_client
    app.state.database.engine.dispose()


def login(client: TestClient) -> str:
    csrf_response = client.get("/api/v1/auth/csrf")
    csrf = csrf_response.json()["csrf_token"]
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "gavin", "password": "correct-horse"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    return client.cookies["gavin_csrf"]


def publish_article(client: TestClient, article: dict, headers: dict[str, str]):
    return client.post(
        f"/api/v1/admin/articles/{article['id']}/publish",
        json={"version": article["version"]},
        headers=headers,
    )
