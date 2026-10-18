from __future__ import annotations

import json
import sqlite3
from decimal import Decimal

import pytest

from app.assistant.development import build_real_development_settings
from app.assistant.provisioning import provision_runtime
from app.assistant.readiness import write_receipt
from app.assistant_qualification.provider_probe import (
    ProviderQualificationError,
    run_local_chat_probe,
    validate_local_chat_probe_artifact,
)
from app.db import Base, Database
from app.local_embedding.artifact import MODEL, PIPELINE, VERSION

from .test_assistant_development import ORIGIN, PROXY_SECRET, _base_settings
from .test_assistant_provider_qualification import _local_probe_inputs


def _inputs(tmp_path, monkeypatch):
    args, requests = _local_probe_inputs(tmp_path, monkeypatch)
    chat = args["settings"].model_copy(
        update={
            "assistant_chat_provider_max_concurrency": 3,
            "assistant_chat_reports_usage": True,
            "assistant_chat_reports_finish_reason": True,
            "assistant_ip_hmac_secret": "ip-secret-independent-000000000000000",
            "assistant_session_hmac_secret": "session-secret-independent-00000000",
            "assistant_csrf_hmac_secret": "csrf-secret-independent-000000000000",
        }
    )
    run_local_chat_probe(**{**args, "settings": chat})
    base = _base_settings(tmp_path).model_copy(
        update={
            "assistant_embedding_provider": "openai-compatible",
            "assistant_embedding_model": MODEL,
            "assistant_embedding_model_version": VERSION,
            "assistant_embedding_dimension": 384,
            "assistant_pipeline_version": PIPELINE,
            "assistant_chunk_size": 384,
            "assistant_chunk_overlap": 64,
            "assistant_embedding_max_batch_items": 1,
            "assistant_embedding_provider_max_concurrency": 1,
            "assistant_e5_model_dir": str(tmp_path / "model"),
            "assistant_embedding_endpoint": "http://127.0.0.1:8091/v1",
            "assistant_embedding_api_key": "synthetic-local-embedding-key-value",
            "assistant_qdrant_url": "http://127.0.0.1:8092",
            "assistant_qdrant_api_key": "synthetic-qdrant-key",
            "assistant_query_embedding_daily_budget_cny": Decimal("0"),
            "assistant_index_embedding_daily_budget_cny": Decimal("0"),
            "assistant_embedding_input_price_cny_per_million": Decimal("0"),
        }
    )
    return dict(
        base=base,
        chat=chat,
        run_root=tmp_path / "run",
        web_origin=ORIGIN,
        proxy_secret=PROXY_SECRET,
        probe_path=args["output_path"],
    ), requests


def test_real_development_boundary_and_signed_probe(tmp_path, monkeypatch):
    args, requests = _inputs(tmp_path, monkeypatch)
    settings = build_real_development_settings(**args)
    assert settings.assistant_online_enabled and not settings.assistant_local_dev_mode
    assert (
        settings.assistant_chat_provider
        == settings.assistant_embedding_provider
        == "openai-compatible"
    )
    assert len(requests) == 1  # settings/readiness never repeat the paid probe
    for change in (
        {"web_origin": "https://example.com"},
        {"base": args["base"].model_copy(update={"environment": "production"})},
        {"base": args["base"].model_copy(update={"assistant_embedding_provider": "test"})},
        {"chat": args["chat"].model_copy(update={"assistant_chat_max_output_tokens": 1024})},
    ):
        with pytest.raises((RuntimeError, ValueError)):
            build_real_development_settings(**{**args, **change})
    payload = json.loads(args["probe_path"].read_text())
    payload["chat"]["input_tokens"] += 1
    args["probe_path"].write_text(json.dumps(payload))
    with pytest.raises(ProviderQualificationError):
        validate_local_chat_probe_artifact(args["probe_path"], settings)
    assert len(requests) == 1


def test_real_development_receipt_and_budget_persist(tmp_path, monkeypatch):
    args, _ = _inputs(tmp_path, monkeypatch)
    settings = build_real_development_settings(**args)
    db = Database(settings.database_url)
    Base.metadata.create_all(db.engine)
    db.engine.dispose()
    provision_runtime(settings)
    receipt = write_receipt(
        settings, probe_live=True, provider_probe=args["probe_path"], local_development=True
    )
    assert receipt
    with sqlite3.connect(settings.assistant_runtime_path) as conn:
        conn.execute(
            "INSERT INTO assistant_chat_budgets (beijing_date, settled_micro) "
            "VALUES ('2026-09-06', 1234)"
        )
    again = build_real_development_settings(**args)
    assert again.assistant_runtime_path == settings.assistant_runtime_path
    provision_runtime(again)
    with sqlite3.connect(settings.assistant_runtime_path) as conn:
        assert (
            conn.execute("SELECT settled_micro FROM assistant_chat_budgets").fetchone()[0] == 1234
        )
    with pytest.raises((RuntimeError, ValueError)):
        write_receipt(settings, probe_live=True, provider_probe=args["probe_path"])
    with pytest.raises((RuntimeError, ValueError)):
        write_receipt(
            settings.model_copy(update={"environment": "production"}),
            probe_live=True,
            provider_probe=args["probe_path"],
            local_development=True,
        )


@pytest.mark.parametrize("dependency", ["embedding", "qdrant"])
def test_real_dependency_failure_preserves_fts_citation_contract(tmp_path, monkeypatch, dependency):
    from .test_assistant_deepseek import _model
    from .test_assistant_online import (
        _create_session,
        _online_client,
        _publish_and_index,
        _sse_body,
    )

    failures = []

    def fail(*args, **kwargs):
        failures.append(dependency)
        raise TimeoutError("synthetic dependency timeout")

    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        online = client.app.state.assistant
        online.chat, requests = _model()
        if dependency == "embedding":
            monkeypatch.setattr(online.embeddings, "embed_query_metered", fail)
        else:
            monkeypatch.setattr(online.index_runtime.store, "search", fail)
        csrf = _create_session(client)
        status, body = _sse_body(client, csrf, "FastAPI", idem="dependency-failure-qa")
        assert status == 200 and "event: answer" in body and '"alias":"c1"' in body
        assert len(requests) == 1
        assert failures == [dependency]


@pytest.mark.parametrize("seconds", [86400, 86401, 10 * 365 * 86400])
def test_local_probe_age_does_not_expire_or_spend(tmp_path, monkeypatch, seconds):
    from datetime import UTC, datetime, timedelta

    from app.assistant.readiness import verify_receipt
    from app.assistant_qualification import provider_probe

    args, requests = _inputs(tmp_path, monkeypatch)
    settings = build_real_development_settings(**args)
    payload = json.loads(args["probe_path"].read_text())
    completed = datetime.fromisoformat(payload["completed_at"])

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return (completed + timedelta(seconds=seconds)).astimezone(tz or UTC)

    monkeypatch.setattr(provider_probe, "datetime", Clock)
    original = args["probe_path"].read_bytes()
    db = Database(settings.database_url)
    Base.metadata.create_all(db.engine)
    db.engine.dispose()
    provision_runtime(settings)
    write_receipt(
        settings, probe_live=True, provider_probe=args["probe_path"], local_development=True
    )
    with sqlite3.connect(settings.assistant_runtime_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            "INSERT INTO assistant_chat_budgets (beijing_date, settled_micro) "
            "VALUES ('2026-09-08', 1234)"
        )
        verify_receipt(settings, conn)
        monkeypatch.setattr("app.assistant.readiness.utc_now", lambda: Clock.now(UTC))
        verify_receipt(settings, conn)
    restarted = build_real_development_settings(**args)
    provision_runtime(restarted)
    with sqlite3.connect(restarted.assistant_runtime_path) as conn:
        conn.row_factory = sqlite3.Row
        verify_receipt(restarted, conn)
        assert (
            conn.execute("SELECT settled_micro FROM assistant_chat_budgets").fetchone()[0] == 1234
        )
    assert args["probe_path"].read_bytes() == original
    assert len(requests) == 1


@pytest.mark.parametrize(
    "defect",
    [
        "missing",
        "null",
        "signature",
        "failed",
        "future",
        "naive",
        "schema",
        "price",
        "budget",
        "production",
    ],
)
def test_local_probe_invalid_evidence_stays_rejected(tmp_path, monkeypatch, defect):
    from datetime import UTC, datetime, timedelta

    from app.assistant.crypto import hmac_hex

    args, requests = _inputs(tmp_path, monkeypatch)
    settings = build_real_development_settings(**args)
    path = args["probe_path"]
    payload = json.loads(path.read_text())
    payload.pop("probe_hmac")
    if defect == "failed":
        payload["chat"]["status"] = "failed"
    if defect == "future":
        payload["completed_at"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    if defect == "naive":
        payload["completed_at"] = "2026-09-01T00:00:00"
    if defect == "schema":
        payload["schema_version"] = 999
    payload["probe_hmac"] = hmac_hex(
        str(settings.assistant_readiness_hmac_secret),
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
        context="local-chat-probe-artifact-v1",
    )
    if defect == "signature":
        payload["probe_hmac"] = "bad"
    path.write_text(json.dumps(None if defect == "null" else payload))
    if defect == "missing":
        path.unlink()
    if defect == "price":
        settings = settings.model_copy(
            update={"assistant_chat_input_price_cny_per_million": Decimal("-1")}
        )
    if defect == "budget":
        settings = settings.model_copy(update={"assistant_chat_daily_budget_cny": Decimal("3")})
    if defect == "production":
        settings = settings.model_copy(update={"environment": "production"})
    with pytest.raises(ProviderQualificationError):
        validate_local_chat_probe_artifact(path, settings)
    assert len(requests) == 1


def test_probe_notice_uses_only_validated_time(tmp_path, monkeypatch):
    from datetime import UTC, datetime, timedelta

    from app.assistant_qualification import provider_probe

    args, requests = _inputs(tmp_path, monkeypatch)
    settings = build_real_development_settings(**args)
    completed = json.loads(args["probe_path"].read_text())["completed_at"]

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return (datetime.fromisoformat(completed) + timedelta(days=2)).astimezone(tz or UTC)

    monkeypatch.setattr(provider_probe, "datetime", Clock)
    notice = provider_probe.local_chat_probe_notice(args["probe_path"], settings)
    assert completed in notice
    assert "年龄仅作提示，不要求付费复验" in notice
    assert "不保证供应商当前可用" in notice
    assert str(settings.assistant_chat_api_key) not in notice
    args["probe_path"].write_text('{"completed_at": "2000-01-01T00:00:00+00:00"}')
    with pytest.raises(ProviderQualificationError):
        provider_probe.local_chat_probe_notice(args["probe_path"], settings)
    assert len(requests) == 1


@pytest.mark.parametrize("boundary", ["ready", "embedding", "generation"])
def test_old_probe_lifespan_preserves_dependency_gates(tmp_path, monkeypatch, boundary):
    import asyncio
    from contextlib import asynccontextmanager
    from datetime import UTC, datetime, timedelta
    from types import SimpleNamespace

    from app.assistant import development
    from app.assistant_qualification import provider_probe

    args, requests = _inputs(tmp_path, monkeypatch)
    settings = build_real_development_settings(**args)
    completed = datetime.fromisoformat(json.loads(args["probe_path"].read_text())["completed_at"])

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return (completed + timedelta(days=2)).astimezone(tz or UTC)

    monkeypatch.setattr(provider_probe, "datetime", Clock)
    events = []

    class Embeddings:
        def embed_query_metered(self, query):
            events.append("embedding")
            if boundary == "embedding":
                raise RuntimeError("synthetic embedding failure")

    monkeypatch.setattr("app.local_embedding.client.E5Embeddings", Embeddings)
    online = SimpleNamespace(
        embeddings=Embeddings(),
        control=SimpleNamespace(read=lambda fn: {"requested_state": "disabled"}),
    )

    def revalidate(*a):
        validate_local_chat_probe_artifact(args["probe_path"], settings)
        events.append("integrity")
        if boundary == "generation":
            raise RuntimeError("missing generation")
        events.append("sign")

    monkeypatch.setattr(development, "revalidate_local_readiness", revalidate)
    monkeypatch.setattr(
        development, "update_availability", lambda *a, **kw: events.append(kw["enabled"])
    )

    @asynccontextmanager
    async def original(app):
        yield

    app = SimpleNamespace(
        router=SimpleNamespace(lifespan_context=original), state=SimpleNamespace(assistant=online)
    )
    development.attach_real_development_lifespan(app, settings, args["probe_path"])

    async def run():
        async with app.router.lifespan_context(app):
            events.append("serving")

    if boundary == "ready":
        asyncio.run(run())
        assert events == ["embedding", "integrity", "sign", "serving"]
    else:
        with pytest.raises(RuntimeError):
            asyncio.run(run())
        assert True not in events and "sign" not in events and "serving" not in events
        assert False not in events
    assert len(requests) == 1
