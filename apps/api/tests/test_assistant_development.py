from __future__ import annotations

import json
import time
from argparse import Namespace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.assistant.crypto import hmac_hex
from app.assistant.development import build_development_settings
from app.assistant.providers import DevelopmentEvidenceChatModel, ModelAnswer
from app.assistant.provisioning import provision_runtime
from app.config import Settings
from app.db import Base
from app.main import create_app

from .conftest import login, publish_article

ORIGIN = "http://127.0.0.1:3101"
PROXY_SECRET = "assistant-development-proxy-secret-value"


@pytest.mark.parametrize("environment", ["production", "test"])
def test_development_entry_rejects_environment_before_migration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    from scripts import run_assistant_dev

    monkeypatch.setattr(run_assistant_dev, "parse_args", lambda: Namespace(
        host="127.0.0.1", port=8101, web_origin=ORIGIN, real=False, probe=None
    ))
    monkeypatch.setattr(run_assistant_dev, "Settings", lambda: _base_settings(
        tmp_path, environment=environment
    ))
    monkeypatch.setenv("GAVIN_ASSISTANT_DEV_RUN_ROOT", str(tmp_path / "run"))
    monkeypatch.setenv("GAVIN_ASSISTANT_DEV_PROXY_SECRET", PROXY_SECRET)
    monkeypatch.setattr(run_assistant_dev.command, "upgrade", lambda *args: pytest.fail(
        "migration must not run before development validation"
    ))
    with pytest.raises(SystemExit, match="GAVIN_ENVIRONMENT=development"):
        run_assistant_dev.main()
    assert not (tmp_path / "content.db").exists()


def _base_settings(tmp_path: Path, *, environment: str = "development") -> Settings:
    return Settings(
        environment=environment,
        database_url=f"sqlite:///{(tmp_path / 'content.db').as_posix()}",
        admin_username="gavin",
        admin_password="correct-horse",
        cookie_secure=False,
        media_root=str(tmp_path / "media"),
        _env_file=None,
    )


def _proxy_headers(method: str, path: str, ip: str = "127.0.0.1") -> dict[str, str]:
    timestamp = str(int(time.time()))
    payload = "\n".join((method.upper(), path, ip, timestamp))
    return {
        "X-Gavin-Client-IP": ip,
        "X-Gavin-Client-IP-Timestamp": timestamp,
        "X-Gavin-Client-IP-Signature": hmac_hex(
            PROXY_SECRET,
            payload,
            context="assistant-proxy-identity-v1",
        ),
    }


def _publish_existing_content(settings: Settings) -> None:
    app = create_app(settings)
    Base.metadata.create_all(app.state.database.engine)
    with TestClient(app) as client:
        csrf = login(client)
        headers = {"X-CSRF-Token": csrf}
        articles = (
            {
                "title": "站点维护记录",
                "slug": "site-maintenance",
                "content": "# 站点维护\n\n这篇已发布文章记录颜色主题和页脚调整。",
            },
            {
                "title": "Python 并发笔记",
                "slug": "python-concurrency",
                "content": "# Python 并发\n\n这篇已发布文章介绍 FastAPI、任务队列和 SQLite。",
            },
        )
        for article in articles:
            created = client.post(
                "/api/v1/admin/articles",
                json=article,
                headers=headers,
            )
            assert created.status_code == 201
            published = publish_article(client, created.json(), headers)
            assert published.status_code == 200
    app.state.database.engine.dispose()


def test_local_development_settings_fail_closed_outside_development(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="GAVIN_ENVIRONMENT=development"):
        build_development_settings(
            _base_settings(tmp_path, environment="test"),
            run_root=(tmp_path / "run").resolve(),
            web_origin=ORIGIN,
            proxy_secret=PROXY_SECRET,
        )
    with pytest.raises(RuntimeError, match="loopback"):
        build_development_settings(
            _base_settings(tmp_path),
            run_root=(tmp_path / "run").resolve(),
            web_origin="http://0.0.0.0:3101",
            proxy_secret=PROXY_SECRET,
        )


def test_local_development_groups_chunks_from_the_same_source() -> None:
    model = DevelopmentEvidenceChatModel()
    prompt = """Current question (untrusted data):
<current-question>配置SSL讲了什么？</current-question>

Published evidence:
<untrusted-evidence descriptor={"id":"c1","path":"/notes/2026/08/ssl","heading":""}>
配置SSL 云服务器 配置SSL证书
</untrusted-evidence>
<untrusted-evidence descriptor={"id":"c2","path":"/notes/2026/08/ssl","heading":"HTTPS 测试"}>
打开 **HTTPS** 测试并确认 HTTP 自动跳转。<details>仅作说明</details>[2]
</untrusted-evidence>"""
    result = model.with_structured_output(
        ModelAnswer,
        method="json_schema",
        strict=True,
        include_raw=True,
    ).invoke([("human", prompt)])

    assert result["parsing_error"] is None
    assert len(result["parsed"].blocks) == 1
    assert result["parsed"].blocks[0].citation_ids == ["c1", "c2"]
    assert {s.citation_id for s in result["parsed"].blocks[0].supports} == {"c1", "c2"}
    assert "HTTPS" in result["parsed"].blocks[0].text
    assert "<" not in result["parsed"].blocks[0].text
    assert "[2]" not in result["parsed"].blocks[0].text


def test_local_development_uses_existing_content_and_returns_citations(tmp_path: Path) -> None:
    base = _base_settings(tmp_path)
    _publish_existing_content(base)
    settings = build_development_settings(
        base,
        run_root=(tmp_path / "run").resolve(),
        web_origin=ORIGIN,
        proxy_secret=PROXY_SECRET,
    )
    assert settings.database_url == base.database_url
    assert settings.assistant_chat_api_key == "offline-development-chat"
    assert settings.assistant_qdrant_url is None
    provision_runtime(settings)

    app = create_app(settings)
    with TestClient(app) as client:
        online = client.app.state.assistant
        assert isinstance(online.chat, DevelopmentEvidenceChatModel)
        gate = online.control.read(
            lambda conn: conn.execute(
                "SELECT effective_state, active_generation_id "
                "FROM assistant_operational_gate WHERE id = 1"
            ).fetchone()
        )
        assert gate["effective_state"] == "enabled"
        assert gate["active_generation_id"] is not None

        session = client.post(
            "/api/v1/assistant/sessions",
            headers={"Origin": ORIGIN, **_proxy_headers("POST", "/api/v1/assistant/sessions")},
        )
        assert session.status_code == 200, session.text
        csrf = session.json()["csrf_token"]
        with client.stream(
            "POST",
            "/api/v1/assistant/questions",
            json={"question": "Python 并发笔记讲了什么？"},
            headers={
                "Origin": ORIGIN,
                "X-Assistant-CSRF": csrf,
                "Idempotency-Key": "assistant-development-test-key",
                **_proxy_headers("POST", "/api/v1/assistant/questions"),
            },
        ) as response:
            body = "".join(response.iter_text())
        assert response.status_code == 200
        answer_payloads = [
            json.loads(line.removeprefix("data: "))
            for line in body.splitlines()
            if line.startswith("data: ") and '"answer"' in line
        ]
        assert answer_payloads
        answer = answer_payloads[-1]
        assert "根据本站已发布内容" in answer["answer"]
        assert answer["citations"]
        assert answer["sources"]
        assert answer["sources"][0]["path"] == "/notes/2026/09/python-concurrency"

    app.state.database.engine.dispose()
