from __future__ import annotations

import os
import socket
from pathlib import Path

import pytest

from app.assistant import deepseek_tokenizer as tokenizer
from app.assistant.prompt import estimate_tokens
from app.assistant.providers import build_chat_model
from app.config import Settings


def settings(environment="development"):
    return Settings(
        _env_file=None, environment=environment, admin_password="test-only-password",
        assistant_chat_provider="openai-compatible",
        assistant_chat_endpoint="https://api.deepseek.com",
        assistant_chat_model="deepseek-flash",
        assistant_chat_output_protocol="deepseek-json-object",
        assistant_chat_api_key="test-only-key",
        assistant_chat_max_output_tokens=512,
    )


@pytest.fixture(autouse=True)
def isolated_cache():
    tokenizer._load.cache_clear()
    yield
    tokenizer._load.cache_clear()


def test_production_rejects_missing_or_corrupt_tokenizer(tmp_path, monkeypatch):
    path = tmp_path / "tokenizer.json"
    monkeypatch.setenv(tokenizer.PATH_ENV, str(path))
    with pytest.raises(RuntimeError, match="missing or unreadable"):
        build_chat_model(settings("production"))
    path.write_text("{}")
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        build_chat_model(settings("production"))


def test_development_fallback_is_conservative_and_never_downloads(tmp_path, monkeypatch):
    monkeypatch.setenv(tokenizer.PATH_ENV, str(tmp_path / "missing.json"))

    def forbidden(*args, **kwargs):
        pytest.fail("token counting attempted network access")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    chat = build_chat_model(settings())
    messages = [("human", "开放 HTTP 80 与 HTTPS 443。")]
    assert estimate_tokens(messages, chat) > len(messages[0][1].encode("utf-8"))


def test_official_tokenizer_and_langchain_are_offline(monkeypatch):
    path = os.environ.get(tokenizer.PATH_ENV)
    if not path or not Path(path).is_file():
        pytest.skip("set DEEPSEEK_V41_TOKENIZER_PATH to the hash-verified build artifact")
    # Construct HTTP clients first; this does not send a request. Tokenizer initialization
    # and every count below must work with network access forbidden and an empty cache.
    chat = build_chat_model(settings())

    def forbidden(*args, **kwargs):
        pytest.fail("token counting attempted network access")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    tokenizer._load.cache_clear()
    samples = [
        "", "Hello", "配置SSL", "HTTP 80 HTTPS 443", "certbot renew --dry-run", "🙂<｜image｜>",
    ]
    for text in samples:
        ids = tokenizer.token_ids(text)
        assert chat.get_token_ids(text) == ids
        assert chat.get_num_tokens(text) == len(ids)
        assert tokenizer._load(path).decode(ids, skip_special_tokens=False) == text
    assert tokenizer.token_ids("Hello") == [19923]
    assert tokenizer._load.cache_info().misses == 1
    assert build_chat_model(settings("production")).custom_get_token_ids is tokenizer.token_ids
    messages = [("human", "端口 80/443，certbot renew --dry-run")]
    assert estimate_tokens(messages, chat) > len(messages[0][1].encode("utf-8"))
