"""Explicit real retrieval commands. No Chat model or online admission is created."""

from __future__ import annotations

import argparse
import json
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select

from ..assistant.admin_operations import finalize_rebuild, recover_switch_pending
from ..assistant.owner_lock import ExclusiveFileLock, lock_path_for
from ..assistant.provisioning import provision_runtime
from ..assistant.runtime_db import open_control
from ..assistant_index.retriever import retrieve
from ..assistant_index.runtime import build_runtime
from ..assistant_index.worker import rebuild_generation
from ..config import Settings
from ..content_write_fence import content_write_fence
from ..db import Database
from ..models import AssistantChunk, AssistantIndexCommand, AssistantIndexGeneration
from ..time_utils import utc_now
from .artifact import MODEL, PIPELINE, VERSION
from .client import validate_e5_settings


def load_settings(env_file: str) -> Settings:
    settings = Settings(_env_file=env_file)
    if settings.environment != "development" or settings.assistant_online_enabled:
        raise ValueError("real retrieval requires development and assistant_online_enabled=false")
    if settings.assistant_embedding_model != MODEL:
        raise ValueError("real retrieval requires the pinned E5 model")
    validate_e5_settings(settings)
    return settings


def finalize_local(
    settings: Settings, database: Database, generation_id: int, runtime,
    *, content_fence_held: bool = False,
) -> None:
    # API owner maintenance operation, never executed by the Worker process.
    if not settings.assistant_runtime_path:
        raise ValueError("a dedicated local runtime path is required")
    path = Path(settings.assistant_runtime_path)
    provision_runtime(settings)
    fence = nullcontext() if content_fence_held else content_write_fence(settings)
    with ExclusiveFileLock(lock_path_for(path)), fence:
        control = open_control(runtime_path=path, owner="api")
        try:
            online = SimpleNamespace(
                settings=settings, database=database, control=control, now=utc_now,
                index_runtime=runtime,
            )
            recover_switch_pending(online)
            with database.session_factory() as db:
                command = db.scalar(
                    select(AssistantIndexCommand).where(
                        AssistantIndexCommand.generation_id == generation_id,
                    )
                )
                if command is None:
                    raise ValueError("generation has no rebuild command")
                operation_id, version = command.id, command.version
            finalize_rebuild(
                online,
                operation_id=operation_id,
                expected_version=version,
                idempotency_key=f"local-e5-finalize-{operation_id}",
            )
        finally:
            control.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Real local E5 retrieval; Chat and gate stay off")
    parser.add_argument("--env-file", default=".env.e5")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("smoke")
    sub.add_parser("rebuild")
    finalize = sub.add_parser("finalize")
    finalize.add_argument("generation", type=int)
    query = sub.add_parser("query")
    query.add_argument("question")
    args = parser.parse_args(argv)
    settings = load_settings(args.env_file)
    database = Database(settings.database_url)
    runtime = build_runtime(settings, database)
    from .client import E5Embeddings

    if not isinstance(runtime.embeddings, E5Embeddings):
        raise ValueError("real retrieval requires E5 embeddings")
    try:
        if args.command == "smoke":
            for text in ["作者的项目使用了哪些技术？", "What technologies does the author use?"]:
                usage = runtime.embeddings.embed_query_metered(text)
                print(
                    json.dumps(
                        {
                            "mode": "real-local-e5",
                            "model": usage.model,
                            "version": usage.version,
                            "tokens": usage.input_tokens,
                            "dimensions": len(usage.vector),
                            "chat_called": False,
                        }
                    )
                )
        elif args.command == "rebuild":
            generation = rebuild_generation(runtime)
            print(
                json.dumps(
                    {
                        "generation": generation,
                        "status": "ready_to_switch",
                        "gate": "disabled",
                        "next": "finalize",
                    }
                )
            )
        elif args.command == "finalize":
            finalize_local(settings, database, args.generation, runtime)
            print(json.dumps({"generation": args.generation, "gate": "disabled"}))
        else:
            with database.session_factory() as db:
                db.info["settings"] = settings
                active = db.scalar(
                    select(AssistantIndexGeneration).where(
                        AssistantIndexGeneration.status == "active"
                    )
                )
                if (
                    active is None
                    or active.embedding_model != MODEL
                    or active.embedding_model_version != VERSION
                    or active.pipeline_version != PIPELINE
                    or active.vector_dimension != 384
                ):
                    raise ValueError("rebuild and finalize a matching E5 generation first")
                question, skip = runtime.embeddings.prepare_retrieval_query(args.question, [])
                result = retrieve(db, runtime, question, limit=5, skip_dense=skip)
                rows = []
                for candidate in result.candidates:
                    chunk = db.scalar(
                        select(AssistantChunk).where(
                            AssistantChunk.chunk_id == candidate.chunk_id,
                            AssistantChunk.generation_id == active.id,
                        )
                    )
                    if chunk is None:
                        raise RuntimeError("retrieval source disappeared")
                    rows.append(
                        {
                            "chunk_id": candidate.chunk_id,
                            "rank": candidate.rank,
                            "sources": candidate.sources,
                            "title": chunk.title,
                            "path": chunk.public_path,
                            "version": chunk.source_version,
                        }
                    )
                print(
                    json.dumps(
                        {
                            "mode": "real-local-e5",
                            "status": result.status,
                            "degraded": result.degraded,
                            "results": rows,
                            "chat_called": False,
                        },
                        ensure_ascii=False,
                    )
                )
    finally:
        runtime.store.client.close()
        database.engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
