from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlalchemy.orm import Session

from ..assistant_index.runtime import AssistantIndexRuntime, build_runtime, build_test_runtime
from ..config import Settings
from ..db import Database
from ..time_utils import utc_now
from .errors import AssistantNotReadyError, AssistantSchemaError
from .graph import build_graph
from .hub import TurnHub
from .owner_lock import ExclusiveFileLock
from .pragmas import apply_aiosqlite_pragmas
from .providers import MeteredEmbeddings, build_chat_model, build_metered_embeddings
from .retrieval_io import RetrievalIO
from .runtime_db import RuntimeControl, acquire_owner_lock
from .runtime_schema import sqlite_master_fingerprint, verify_provisioned_schema
from .serialization import SessionSerialization
from .time_beijing import beijing_date


@dataclass
class AssistantOnline:
    settings: Settings
    database: Database
    lock: ExclusiveFileLock
    control: RuntimeControl
    saver_conn: Any
    saver: Any
    chat: BaseChatModel
    embeddings: MeteredEmbeddings
    index_runtime: AssistantIndexRuntime
    graph: Any
    hub: TurnHub
    retrieval_io: RetrievalIO
    clock: Callable[[], datetime] = utc_now
    tasks: dict[str, asyncio.Task] = field(default_factory=dict)
    cleanup_task: asyncio.Task | None = None
    started_fingerprint: str = ""
    serialization: SessionSerialization = field(default_factory=SessionSerialization)

    def now(self) -> datetime:
        return self.clock()

    def beijing_day(self) -> str:
        return beijing_date(self.now()).isoformat()

    def content_session(self) -> Session:
        session = self.database.session_factory()
        session.info["settings"] = self.settings
        return session

    def active_generation(self):
        from ..assistant_index.worker import ensure_pointer
        from ..models import AssistantIndexGeneration
        from .readiness import _Gen

        db = self.content_session()
        try:
            pointer = ensure_pointer(db)
            if pointer.active_generation_id is None:
                return None
            generation = db.get(AssistantIndexGeneration, pointer.active_generation_id)
            if generation is None:
                return None
            return _Gen(
                {
                    "id": generation.id,
                    "collection_name": generation.collection_name,
                    "distance": generation.distance_metric,
                    "pipeline": generation.pipeline_version,
                    "embedding_provider": generation.embedding_provider,
                    "embedding_model": generation.embedding_model,
                    "embedding_model_version": generation.embedding_model_version,
                    "dimension": generation.vector_dimension,
                }
            )
        finally:
            db.close()


async def start_assistant_online(
    settings: Settings,
    database: Database,
    *,
    clock: Callable[[], datetime] | None = None,
    chat: BaseChatModel | None = None,
    embeddings: MeteredEmbeddings | None = None,
    index_runtime: AssistantIndexRuntime | None = None,
) -> AssistantOnline:
    if not settings.assistant_online_enabled:
        raise AssistantNotReadyError("assistant is disabled")
    if not settings.assistant_runtime_path:
        raise AssistantSchemaError("assistant_runtime_path is required")
    runtime_path = Path(settings.assistant_runtime_path)
    lock = acquire_owner_lock(runtime_path)
    retrieval_io = RetrievalIO(settings.assistant_embedding_provider_max_concurrency or 1)
    try:
        control = RuntimeControl(runtime_path)
        fingerprint = verify_provisioned_schema(control.engine)
        # A saver await must not leave an implicit write transaction blocking
        # synchronous control transactions on this same event loop. Each saver
        # statement is atomic; identity/session fencing still protects delivery
        # and cleanup across the delegate's multi-statement operations.
        saver_conn = await aiosqlite.connect(runtime_path.as_posix(), isolation_level=None)
        await apply_aiosqlite_pragmas(saver_conn, foreign_keys=False)
        raw_saver = AsyncSqliteSaver(saver_conn)
        await raw_saver.setup()
        after = sqlite_master_fingerprint(control.engine)
        if after != fingerprint:
            raise AssistantSchemaError("saver setup mutated assistant_runtime schema")
        embed = embeddings or build_metered_embeddings(settings)
        chat_model = chat or build_chat_model(settings)
        if index_runtime is None:
            if settings.assistant_embedding_provider == "test":
                index_runtime = build_test_runtime(settings, database)
            else:
                index_runtime = build_runtime(settings, database, embeddings=embed)
            index_runtime.embeddings = embed
        online = AssistantOnline(
            settings=settings,
            database=database,
            lock=lock,
            control=control,
            saver_conn=saver_conn,
            saver=raw_saver,
            chat=chat_model,
            embeddings=embed,
            index_runtime=index_runtime,
            graph=None,
            hub=TurnHub(),
            retrieval_io=retrieval_io,
            clock=clock or utc_now,
            started_fingerprint=fingerprint,
        )
        from .total_budget import sync_runtime
        control.read(lambda conn: sync_runtime(online, conn))
        control.after_commit = lambda conn: sync_runtime(online, conn)
        from .saver import IdentityAwareSaver

        online.saver = IdentityAwareSaver(online, raw_saver)
        online.graph = build_graph(online)
        from .admin_operations import recover_switch_pending

        recover_switch_pending(online)
        from .cleanup import recover_inflight, start_cleanup_loop, sweep

        await recover_inflight(online)
        await sweep(online)
        online.cleanup_task = asyncio.create_task(start_cleanup_loop(online))
        return online
    except Exception:
        await retrieval_io.aclose()
        lock.release()
        raise


async def stop_assistant_online(online: AssistantOnline) -> None:
    pending: list[asyncio.Task] = []
    if online.cleanup_task is not None:
        online.cleanup_task.cancel()
        pending.append(online.cleanup_task)
    for task in list(online.tasks.values()):
        task.cancel()
        pending.append(task)
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
    await online.retrieval_io.aclose()
    await online.saver_conn.close()
    online.control.dispose()
    online.lock.release()
