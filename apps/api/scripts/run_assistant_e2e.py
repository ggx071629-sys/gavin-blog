from __future__ import annotations

import argparse
import asyncio
import os
import sys
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path

import uvicorn

api_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(api_root))

from app.assistant.constants import (  # noqa: E402
    POLICY_VERSION,
    PROVIDER_TEST,
    TEST_CHAT_MODEL,
    TEST_CHAT_MODEL_VERSION,
)
from app.assistant.provisioning import provision_runtime  # noqa: E402
from app.assistant_index.constants import (  # noqa: E402
    TEST_EMBEDDING_MODEL,
    TEST_EMBEDDING_MODEL_VERSION,
    TEST_EMBEDDING_PROVIDER,
)
from app.config import Settings  # noqa: E402
from app.db import Base  # noqa: E402
from app.main import create_app  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an isolated assistant API for Playwright")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8101)
    parser.add_argument("--web-origin", default="http://127.0.0.1:3101")
    return parser.parse_args()


def build_app(run_root: Path, web_origin: str):
    runtime = run_root / "assistant_runtime.db"
    settings = Settings(
        environment="test",
        database_url="sqlite:///" + (run_root / "assistant-e2e.db").as_posix(),
        admin_username="gavin",
        admin_password="correct-horse",
        cookie_secure=False,
        cors_origins=web_origin,
        media_root=str(run_root / "media"),
        assistant_index_worker_enabled=True,
        assistant_embedding_provider=TEST_EMBEDDING_PROVIDER,
        assistant_embedding_model=TEST_EMBEDDING_MODEL,
        assistant_embedding_model_version=TEST_EMBEDDING_MODEL_VERSION,
        assistant_embedding_dimension=32,
        assistant_embedding_max_batch_items=64,
        assistant_embedding_provider_max_concurrency=4,
        assistant_embedding_endpoint="https://example.invalid/v1",
        assistant_embedding_api_key="test-embedding-key",
        assistant_online_enabled=True,
        assistant_test_startup_bootstrap=True,
        assistant_runtime_path=str(runtime),
        assistant_single_process_confirmed=True,
        assistant_public_origin=web_origin,
        assistant_ip_hmac_secret="assistant-ip-secret-value-32bytes-min",
        assistant_session_hmac_secret="assistant-session-secret-value-32bytes",
        assistant_csrf_hmac_secret="assistant-csrf-secret-value-32bytes-min",
        assistant_trusted_proxies="127.0.0.1/32",
        assistant_client_ip_header="X-Gavin-Client-IP",
        assistant_proxy_hmac_secret="assistant-proxy-secret-value-32bytes",
        assistant_proxy_max_clock_skew_seconds=10,
        assistant_sse_heartbeat_seconds=1,
        assistant_readiness_hmac_secret="assistant-ready-secret-value-32bytes",
        assistant_release_id="assistant-e2e",
        assistant_policy_version=POLICY_VERSION,
        assistant_chat_provider=PROVIDER_TEST,
        assistant_chat_model=TEST_CHAT_MODEL,
        assistant_chat_model_version=TEST_CHAT_MODEL_VERSION,
        assistant_chat_provider_max_concurrency=3,
        assistant_chat_endpoint="https://example.invalid/v1",
        assistant_chat_api_key="test-chat-key",
        assistant_chat_max_input_tokens=8000,
        assistant_chat_max_output_tokens=400,
        assistant_chat_context_window_tokens=16384,
        assistant_chat_input_price_cny_per_million=Decimal("1.00"),
        assistant_chat_output_price_cny_per_million=Decimal("2.00"),
        assistant_chat_reports_usage=True,
        assistant_chat_reports_finish_reason=True,
        assistant_chat_daily_budget_cny=Decimal("2.00"),
        assistant_query_embedding_daily_budget_cny=Decimal("10.00"),
        assistant_index_embedding_daily_budget_cny=Decimal("10.00"),
        assistant_embedding_input_price_cny_per_million=Decimal("0.10"),
        assistant_provider_timeout_seconds=30,
        assistant_runner_cleanup_grace_seconds=5,
        _env_file=None,
    )
    provision_runtime(settings)
    app = create_app(settings)
    Base.metadata.create_all(app.state.database.engine)
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def test_lifespan(application):
        async with original_lifespan(application):
            from app.assistant_index.worker import process_once

            stopping = asyncio.Event()

            async def work():
                while not stopping.is_set():
                    async with application.state.content_write_lock:
                        await asyncio.to_thread(
                            process_once, application.state.assistant.index_runtime,
                        )
                    try:
                        await asyncio.wait_for(stopping.wait(), timeout=0.5)
                    except TimeoutError:
                        pass

            worker = asyncio.create_task(work())
            try:
                yield
            finally:
                stopping.set()
                # Join before the owner closes the shared in-memory index/runtime.
                await worker

    app.router.lifespan_context = test_lifespan

    @app.post("/api/v1/assistant/_test/chat/hold", include_in_schema=False)
    def hold_chat() -> dict[str, bool]:
        app.state.assistant.chat.hold()
        return {"held": True}

    @app.post("/api/v1/assistant/_test/chat/release", include_in_schema=False)
    def release_chat() -> dict[str, bool]:
        app.state.assistant.chat.release()
        return {"released": True}

    @app.get("/api/v1/assistant/_test/chat/started", include_in_schema=False)
    def chat_started() -> dict[str, bool]:
        return {"started": app.state.assistant.chat.wait_until_started(0)}

    @app.post("/api/v1/assistant/_test/resume", include_in_schema=False)
    def seed_resume_attachment() -> dict[str, str]:
        """Transport-only fixture in the isolated test app, never a production route."""
        import hashlib
        import io
        from uuid import uuid4

        from pypdf import PdfWriter

        from app.assistant_resume.storage import bind
        from app.models import AssistantChunk, AssistantIndexPointer, AssistantResumeVersion

        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        output = io.BytesIO()
        writer.write(output)
        body = output.getvalue()
        version_id = uuid4().hex
        with app.state.database.session_factory() as db:
            row = bind(db, "https://fixture.invalid/transport.pdf")
            db.add(AssistantResumeVersion(
                id=version_id, binding_epoch=row.binding_epoch,
                sha256=hashlib.sha256(body).hexdigest(), parser_version="transport-fixture",
                pdf_bytes=body, pages_json='["transport fixture"]', body="transport fixture",
            ))
            row.current_version_id = version_id
            row.enabled = True
            row.state = "ready"
            pointer = db.get(AssistantIndexPointer, 1)
            db.add(AssistantChunk(
                chunk_id=uuid4().hex, source_type="resume", source_id=1, source_version=version_id,
                generation_id=pointer.active_generation_id, pipeline_version="transport-fixture",
                ordinal=0, heading_path="第 1 页", content_hash=hashlib.sha256(body).hexdigest(),
                page_content="transport fixture", title="Gavin 简历",
                public_path=f"/api/v1/assistant/resume/{version_id}",
            ))
            db.commit()
        return {"version_id": version_id, "sha256": hashlib.sha256(body).hexdigest()}

    return app


if __name__ == "__main__":
    args = parse_args()
    run_root_value = os.environ.get("GAVIN_E2E_RUN_ROOT", "").strip()
    if not run_root_value:
        raise SystemExit(
            "GAVIN_E2E_RUN_ROOT must point to an isolated run directory; "
            "refusing to write assistant e2e databases into the source tree"
        )
    run_root = Path(run_root_value)
    run_root.mkdir(parents=True, exist_ok=True)
    app = build_app(run_root, args.web_origin)
    uvicorn.run(app, host=args.host, port=args.port)
