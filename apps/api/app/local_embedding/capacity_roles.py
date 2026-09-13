"""Opt-in loopback benchmark processes; never imported by the normal application."""

from __future__ import annotations

import argparse
import hmac
import json
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import Settings


def read_configuration(path: Path) -> tuple[dict, Settings]:
    from ..config import Settings

    config = json.loads(path.read_text(encoding="utf-8"))
    settings = Settings.model_validate(config["settings"])
    root = path.resolve().parent
    from sqlalchemy.engine import make_url

    content = Path(make_url(settings.database_url).database or "").resolve()
    runtime = Path(settings.assistant_runtime_path or "").resolve()
    if (
        settings.environment != "development"
        or settings.assistant_online_enabled
        or settings.assistant_local_dev_mode
        or settings.assistant_test_startup_bootstrap
        or content != root / "content.db"
        or runtime != root / "runtime.db"
        or len(config["token"]) < 24
    ):
        raise ValueError("capacity requires isolated development databases and online disabled")
    return config, settings


def create_capacity_api(settings, token: str):
    from fastapi import Depends, Header, HTTPException, Query
    from sqlalchemy import select

    from ..assistant_index.retriever import retrieve
    from ..assistant_index.runtime import build_runtime
    from ..main import create_app
    from ..models import AssistantIndexCommand
    from .client import E5Embeddings
    from .evaluation import inspect_gate
    from .local import finalize_local

    if (
        settings.environment != "development"
        or settings.assistant_online_enabled
        or len(token) < 24
    ):
        raise ValueError("capacity API is development-only with online disabled")
    app = create_app(settings)
    runtime = build_runtime(settings, app.state.database)
    embeddings = runtime.embeddings
    if not isinstance(embeddings, E5Embeddings):
        raise ValueError("capacity requires pinned real E5 embeddings")

    def authorize(authorization: str | None = Header(default=None)):
        if not hmac.compare_digest(authorization or "", "Bearer " + token):
            raise HTTPException(401, "capacity authorization required")

    # Read-only GET does not enter the normal application's mutation write fence.
    def query(question: str = Query(min_length=1, max_length=20000)):
        started = time.perf_counter()
        prepared, overlong = embeddings.prepare_retrieval_query(question, [])
        if overlong:
            raise HTTPException(400, "capacity workload requires input within model limit")
        before = time.perf_counter()
        usage = embeddings.embed_query_metered(prepared)
        embedding_seconds = time.perf_counter() - before
        with runtime.database.session_factory() as db:
            db.info["settings"] = settings
            pending = db.scalar(
                select(AssistantIndexCommand).where(
                    AssistantIndexCommand.status.in_(("pending", "running", "catch_up"))
                )
            )
            result = retrieve(db, runtime, prepared, query_vector=usage.vector, limit=5)
        return {
            "status": result.status,
            "degraded": result.degraded,
            "overlong": overlong,
            "tokens": usage.input_tokens,
            "embedding_seconds": embedding_seconds,
            "retrieval_seconds": time.perf_counter() - started,
            "hits": len(result.candidates),
            "rebuild_active": pending is not None,
            "chat_called": False,
        }

    app.get("/__capacity/query", dependencies=[Depends(authorize)])(query)

    @app.post("/__capacity/finalize/{generation}", dependencies=[Depends(authorize)])
    def finalize(generation: int):
        # The ordinary API mutation middleware already owns the content fence.
        finalize_local(settings, app.state.database, generation, runtime, content_fence_held=True)
        return {"gate": inspect_gate(settings)}

    return app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--role", choices=["model", "api", "worker"], required=True)
    args = parser.parse_args(argv)
    if args.role == "model":
        config = json.loads(args.config.read_text(encoding="utf-8"))
        if (
            config["settings"]["environment"] != "development"
            or config["settings"]["assistant_online_enabled"]
        ):
            raise ValueError("capacity model requires development and online disabled")
        os.environ["GAVIN_E5_MODEL_DIR"] = config["model_directory"]
        os.environ["GAVIN_E5_API_KEY"] = config["model_key"]
        import uvicorn

        from .service import create_app

        app = create_app()

        @app.get("/__capacity/queue")
        def queue():
            return {"waiting": app.state.queue.qsize()}

        uvicorn.run(app, host="127.0.0.1", port=config["ports"]["model"], access_log=False)
    elif args.role == "api":
        config, settings = read_configuration(args.config)
        import uvicorn

        uvicorn.run(
            create_capacity_api(settings, config["token"]),
            host="127.0.0.1",
            port=config["ports"]["api"],
            access_log=False,
        )
    else:
        config, settings = read_configuration(args.config)
        from ..assistant_index.runtime import build_runtime
        from ..assistant_index.worker import process_once
        from ..db import Database

        runtime = build_runtime(settings, Database(settings.database_url))
        try:
            while not args.config.with_name("stop-worker").exists():
                if not process_once(runtime):
                    time.sleep(settings.assistant_index_poll_seconds)
        finally:
            runtime.store.client.close()
            runtime.database.engine.dispose()


if __name__ == "__main__":
    main()
