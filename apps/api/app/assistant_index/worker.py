from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import timedelta

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from ..assistant.crypto import random_id
from ..assistant.errors import AssistantOwnerLockError
from ..config import Settings, get_settings
from ..content_write_fence import content_write_fence
from ..db import Database
from ..models import (
    AssistantChunk,
    AssistantIndexCommand,
    AssistantIndexGeneration,
    AssistantIndexPointer,
    AssistantIndexRebuildProgress,
    AssistantIndexTask,
)
from ..time_utils import utc_now
from .chunker import chunk_source
from .constants import (
    DISTANCE_COSINE,
    FORBIDDEN_IDENTITY_VALUES,
    GEN_FAILED,
    GEN_STAGING,
    OP_DELETE,
    OP_PURGE,
    POINTER_ID,
    STATUS_FAILED,
    STATUS_LEASED,
    STATUS_PENDING,
    STATUS_SUCCEEDED,
)
from .embeddings import AssistantIndexConfigurationError, validate_assistant_worker_settings
from .fts import delete_fts_ids, ensure_assistant_fts, upsert_chunk_fts
from .projector import (
    SourceDocument,
    iter_public_sources,
    pipeline_version_from,
    project_source,
    source_revision_set_digest,
)
from .runtime import AssistantIndexRuntime, build_runtime
from .worker_control import (
    FenceHeartbeat,
    WorkerFenceLost,
    acquire_worker_owner,
    new_lease_token,
    record_provider_fact,
    record_repair_intent,
    require_source_revision,
    require_worker_fence,
)

logger = logging.getLogger("gavin.assistant_index")


def ensure_pointer(db: Session) -> AssistantIndexPointer:
    pointer = db.get(AssistantIndexPointer, POINTER_ID)
    if pointer is None:
        pointer = AssistantIndexPointer(id=POINTER_ID, updated_at=utc_now())
        db.add(pointer)
        db.flush()
    return pointer


def safe_error_summary(exc: BaseException, settings: Settings) -> str:
    text = f"{type(exc).__name__}: {exc}"
    secrets = [
        settings.assistant_embedding_api_key,
        settings.assistant_qdrant_api_key,
        settings.admin_password,
    ]
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[redacted]")
    return text.replace("\n", " ")[:240]


def reclaim_expired_leases(db: Session, now) -> int:
    tasks = list(
        db.scalars(
            select(AssistantIndexTask).where(
                AssistantIndexTask.status == STATUS_LEASED,
                AssistantIndexTask.lease_expires_at.is_not(None),
                AssistantIndexTask.lease_expires_at < now,
            )
        ).all()
    )
    for task in tasks:
        logger.info("reclaiming expired assistant index lease task_id=%s", task.id)
        unsafe = (
            task.operation == "upsert" and task.provider_state in {"sending", "unknown"}
        )
        task.status = STATUS_FAILED if unsafe else STATUS_PENDING
        task.lease_owner = None
        task.lease_expires_at = None
        task.lease_token = None
        task.worker_fence = None
        task.safe_error_code = "provider_result_unknown" if unsafe else task.safe_error_code
        task.version += 1
        task.updated_at = now
    return len(tasks)


def lease_next_task(
    db: Session, runtime: AssistantIndexRuntime, fence: int
) -> AssistantIndexTask | None:
    now = runtime.now()
    task = db.scalar(
        select(AssistantIndexTask)
        .where(
            AssistantIndexTask.status == STATUS_PENDING,
            AssistantIndexTask.available_at <= now,
        )
        .order_by(AssistantIndexTask.id.asc())
        .limit(1)
    )
    if task is None:
        return None
    task.status = STATUS_LEASED
    task.lease_owner = runtime.owner
    task.worker_fence = fence
    task.lease_token = new_lease_token()
    task.provider_state = "prepared"
    task.attempt_count += 1
    task.version += 1
    task.lease_expires_at = now + timedelta(seconds=runtime.settings.assistant_index_lease_seconds)
    task.updated_at = now
    db.flush()
    logger.info(
        "leased assistant index task_id=%s source=%s/%s op=%s attempt=%s",
        task.id,
        task.source_type,
        task.source_id,
        task.operation,
        task.attempt_count,
    )
    return task


def _succeed(task: AssistantIndexTask, runtime: AssistantIndexRuntime) -> None:
    task.status = STATUS_SUCCEEDED
    task.lease_owner = None
    task.lease_expires_at = None
    task.lease_token = None
    task.worker_fence = None
    task.provider_state = "succeeded"
    task.last_error_summary = None
    task.safe_error_code = None
    task.version += 1
    task.updated_at = runtime.now()


def _fail_or_retry(
    task: AssistantIndexTask,
    runtime: AssistantIndexRuntime,
    exc: BaseException,
) -> None:
    from .index_ledger import UnavailableIndexVectorsError, UnknownIndexEmbeddingError

    intervention = isinstance(exc, UnknownIndexEmbeddingError)
    summary = safe_error_summary(exc, runtime.settings)
    logger.warning("assistant index task_id=%s error=%s", task.id, summary)
    now = runtime.now()
    if intervention or task.attempt_count >= runtime.settings.assistant_index_max_attempts:
        task.status = STATUS_FAILED
        task.available_at = now
    else:
        delay = min(300, 2 ** min(task.attempt_count, 8))
        task.status = STATUS_PENDING
        task.available_at = now + timedelta(seconds=delay)
    task.lease_owner = None
    task.lease_expires_at = None
    task.lease_token = None
    task.worker_fence = None
    task.safe_error_code = (
        "worker_fence_lost" if isinstance(exc, WorkerFenceLost) else "index_task_failed"
    )
    if intervention:
        known_success = isinstance(exc, UnavailableIndexVectorsError)
        task.safe_error_code = (
            "index_vectors_unavailable" if known_success else "provider_result_unknown"
        )
        task.provider_state = "succeeded" if known_success else "unknown"
    task.version += 1
    task.last_error_summary = summary
    task.updated_at = now


def _active_generation(db: Session) -> AssistantIndexGeneration | None:
    pointer = ensure_pointer(db)
    if pointer.active_generation_id is None:
        return None
    return db.get(AssistantIndexGeneration, pointer.active_generation_id)


def _chunk_payload(chunk: AssistantChunk, generation_id: int) -> dict:
    return {
        "chunk_id": chunk.chunk_id,
        "source_type": chunk.source_type,
        "source_id": chunk.source_id,
        "source_version": chunk.source_version,
        "generation": generation_id,
        "pipeline_version": chunk.pipeline_version,
    }


def _source_chunk_ids(
    db: Session,
    generation_id: int,
    source_type: str,
    source_id: int,
) -> list[str]:
    return list(
        db.scalars(
            select(AssistantChunk.chunk_id).where(
                AssistantChunk.generation_id == generation_id,
                AssistantChunk.source_type == source_type,
                AssistantChunk.source_id == source_id,
            )
        ).all()
    )


def replace_source_index(
    db: Session,
    runtime: AssistantIndexRuntime,
    generation: AssistantIndexGeneration,
    document: SourceDocument,
    drafts,
    vectors: list[list[float]],
    *,
    fence: int,
    task_id: int | None,
    lease_token: str | None,
) -> None:
    if len(drafts) != len(vectors):
        raise RuntimeError("embedding count does not match chunk count")
    for vector in vectors:
        if len(vector) != generation.vector_dimension:
            raise RuntimeError("embedding dimension does not match generation")
    old_ids = _source_chunk_ids(db, generation.id, document.source_type, document.source_id)
    require_worker_fence(runtime, fence, task_id=task_id, token=lease_token)
    require_source_revision(
        runtime,
        source_type=document.source_type,
        source_id=document.source_id,
        expected_version=document.source_version,
    )
    try:
        if runtime.store.collection_exists(generation.collection_name):
            with FenceHeartbeat(
                runtime, fence, task_id=task_id, token=lease_token
            ):
                runtime.store.delete_chunks(
                    generation.collection_name,
                    generation_id=generation.id,
                    chunk_ids=old_ids,
                )
                runtime.store.upsert_points(
                    generation.collection_name,
                    generation_id=generation.id,
                    items=[
                        (
                            draft.chunk_id,
                            vector,
                            {
                                "chunk_id": draft.chunk_id,
                                "source_type": document.source_type,
                                "source_id": document.source_id,
                                "source_version": document.source_version,
                                "generation": generation.id,
                                "pipeline_version": document.pipeline_version,
                            },
                        )
                        for draft, vector in zip(drafts, vectors, strict=True)
                    ],
                )
        require_worker_fence(runtime, fence, task_id=task_id, token=lease_token)
        require_source_revision(
            runtime,
            source_type=document.source_type,
            source_id=document.source_id,
            expected_version=document.source_version,
        )
    except WorkerFenceLost:
        record_repair_intent(
            runtime,
            source_type=document.source_type,
            source_id=document.source_id,
            generation_id=generation.id,
            reason_code="worker_fence_lost",
        )
        raise
    delete_fts_ids(db, old_ids, generation_id=generation.id)
    db.execute(
        delete(AssistantChunk).where(
            AssistantChunk.generation_id == generation.id,
            AssistantChunk.source_type == document.source_type,
            AssistantChunk.source_id == document.source_id,
        )
    )
    rows: list[tuple[AssistantChunk, list[float]]] = []
    for draft, vector in zip(drafts, vectors, strict=True):
        row = AssistantChunk(
            chunk_id=draft.chunk_id,
            source_type=document.source_type,
            source_id=document.source_id,
            source_version=document.source_version,
            generation_id=generation.id,
            pipeline_version=document.pipeline_version,
            ordinal=draft.ordinal,
            heading_path=draft.heading_path,
            content_hash=draft.content_hash,
            page_content=draft.page_content,
            title=document.title,
            public_path=document.public_path,
            created_at=runtime.now(),
        )
        db.add(row)
        rows.append((row, vector))
    db.flush()
    for row, _vector in rows:
        upsert_chunk_fts(db, row)
    if document.source_type == "resume":
        from ..models import AssistantResumeSource

        resume = db.get(AssistantResumeSource, 1)
        if resume and resume.enabled and resume.current_version_id == document.source_version:
            resume.last_indexed_at = runtime.now()


def delete_source_index(
    db: Session,
    runtime: AssistantIndexRuntime,
    generation: AssistantIndexGeneration,
    source_type: str,
    source_id: int,
    *,
    fence: int,
    task_id: int | None,
    lease_token: str | None,
    permanent: bool = False,
) -> None:
    old_ids = _source_chunk_ids(db, generation.id, source_type, source_id)
    require_worker_fence(runtime, fence, task_id=task_id, token=lease_token)
    require_source_revision(
        runtime,
        source_type=source_type,
        source_id=source_id,
        expected_version="0",
    )
    try:
        if runtime.store.collection_exists(generation.collection_name):
            with FenceHeartbeat(
                runtime, fence, task_id=task_id, token=lease_token
            ):
                if permanent:
                    runtime.store.delete_source(
                        generation.collection_name,
                        source_type=source_type,
                        source_id=source_id,
                    )
                else:
                    runtime.store.delete_chunks(
                        generation.collection_name,
                        generation_id=generation.id,
                        chunk_ids=old_ids,
                    )
        require_worker_fence(runtime, fence, task_id=task_id, token=lease_token)
        require_source_revision(
            runtime,
            source_type=source_type,
            source_id=source_id,
            expected_version="0",
        )
    except WorkerFenceLost:
        record_repair_intent(
            runtime,
            source_type=source_type,
            source_id=source_id,
            generation_id=generation.id,
            reason_code="worker_fence_lost",
        )
        raise
    delete_fts_ids(db, old_ids, generation_id=generation.id)
    db.execute(
        delete(AssistantChunk).where(
            AssistantChunk.generation_id == generation.id,
            AssistantChunk.source_type == source_type,
            AssistantChunk.source_id == source_id,
        )
    )


def _index_document(
    db: Session,
    runtime: AssistantIndexRuntime,
    generation: AssistantIndexGeneration,
    document: SourceDocument,
    *,
    fence: int,
    task_id: int | None,
    lease_token: str | None,
) -> None:
    from ..local_embedding.artifact import MODEL

    settings = runtime.settings
    if MODEL in {generation.embedding_model, settings.assistant_embedding_model} and (
        generation.embedding_model != settings.assistant_embedding_model
        or generation.embedding_model_version != settings.assistant_embedding_model_version
        or generation.vector_dimension != settings.assistant_embedding_dimension
        or generation.pipeline_version != settings.assistant_pipeline_version
    ):
        raise RuntimeError(
            "E5 generation identity mismatch; drain old outbox before model migration"
        )
    drafts = chunk_source(
        document,
        chunk_size=runtime.settings.assistant_chunk_size,
        chunk_overlap=runtime.settings.assistant_chunk_overlap,
        tokenizer=getattr(runtime.embeddings, "tokenizer", None),
    )
    if not drafts:
        replace_source_index(
            db,
            runtime,
            generation,
            document,
            [],
            [],
            fence=fence,
            task_id=task_id,
            lease_token=lease_token,
        )
        return
    # Same text under a new publish revision needs new metadata, not new embeddings.
    # Restrict reuse to this generation, source and exact embedding/pipeline identity.
    identity_matches = (
        generation.embedding_provider == settings.assistant_embedding_provider
        and generation.embedding_model == settings.assistant_embedding_model
        and generation.embedding_model_version == settings.assistant_embedding_model_version
        and generation.vector_dimension == settings.assistant_embedding_dimension
        and generation.pipeline_version == document.pipeline_version
    )
    old = list(db.scalars(select(AssistantChunk).where(
        AssistantChunk.generation_id == generation.id,
        AssistantChunk.source_type == document.source_type,
        AssistantChunk.source_id == document.source_id,
        AssistantChunk.pipeline_version == document.pipeline_version,
    ).order_by(AssistantChunk.ordinal)))
    if identity_matches and [c.page_content for c in old] == [d.page_content for d in drafts]:
        with FenceHeartbeat(runtime, fence, task_id=task_id, token=lease_token):
            reused = runtime.store.reusable_vectors(
                generation.collection_name, generation_id=generation.id,
                payloads=[_chunk_payload(c, generation.id) for c in old],
                dimension=generation.vector_dimension,
            )
        if reused is not None:
            replace_source_index(
                db, runtime, generation, document, drafts, reused,
                fence=fence, task_id=task_id, lease_token=lease_token,
            )
            return
    texts = [draft.page_content for draft in drafts]
    embeddings = runtime.embeddings
    if runtime.settings.assistant_index_embedding_daily_budget_cny is not None:
        from .index_ledger import (
            DeferredIndexEmbeddingError,
            LedgeredIndexEmbeddings,
        )

        ledgered = LedgeredIndexEmbeddings(
            embeddings,
            runtime,
            db,
            generation_id=generation.id,
            task_id=task_id,
            worker_fence=fence,
            lease_token=lease_token,
        )
        try:
            usage = ledgered.embed_documents_metered(texts)
            vectors = usage.vectors
        except DeferredIndexEmbeddingError:
            raise
    else:
        vectors = embeddings.embed_documents(texts)
    replace_source_index(
        db,
        runtime,
        generation,
        document,
        drafts,
        vectors,
        fence=fence,
        task_id=task_id,
        lease_token=lease_token,
    )


def apply_task(
    db: Session,
    runtime: AssistantIndexRuntime,
    task: AssistantIndexTask,
    generation: AssistantIndexGeneration | None,
    *,
    fence: int,
) -> None:
    lease_token = task.lease_token
    require_worker_fence(runtime, fence, task_id=task.id, token=lease_token)
    if task.source_type == "resume" and task.operation == OP_PURGE:
        from ..assistant_resume.index_cleanup import purge_version

        task.provider_state = "sending"
        db.commit()
        purge_version(db, runtime, task, fence)
        _succeed(task, runtime)
        return
    if generation is None:
        if task.operation in {OP_DELETE, OP_PURGE}:
            _succeed(task, runtime)
            return
        raise RuntimeError("no active generation for incremental upsert")
    if task.operation in {OP_DELETE, OP_PURGE}:
        current = project_source(db, task.source_type, task.source_id)
        if task.operation == OP_PURGE and current is not None:
            _succeed(task, runtime)
            return
        task.provider_state = "sending"
        db.commit()
        delete_source_index(
            db,
            runtime,
            generation,
            task.source_type,
            task.source_id,
            fence=fence,
            task_id=task.id,
            lease_token=lease_token,
            permanent=task.operation == OP_PURGE,
        )
        _succeed(task, runtime)
        return
    document = project_source(db, task.source_type, task.source_id)
    if document is None:
        task.provider_state = "sending"
        db.commit()
        delete_source_index(
            db,
            runtime,
            generation,
            task.source_type,
            task.source_id,
            fence=fence,
            task_id=task.id,
            lease_token=lease_token,
        )
        _succeed(task, runtime)
        return
    if document.source_version != task.target_version:
        logger.info(
            "skipping superseded assistant index task_id=%s current=%s target=%s",
            task.id,
            document.source_version,
            task.target_version,
        )
        _succeed(task, runtime)
        return
    already = db.scalar(
        select(func.count())
        .select_from(AssistantChunk)
        .where(
            AssistantChunk.generation_id == generation.id,
            AssistantChunk.source_type == document.source_type,
            AssistantChunk.source_id == document.source_id,
            AssistantChunk.source_version == document.source_version,
        )
    )
    if already:
        _succeed(task, runtime)
        return
    try:
        task.provider_state = "sending"
        db.commit()
        _index_document(
            db,
            runtime,
            generation,
            document,
            fence=fence,
            task_id=task.id,
            lease_token=lease_token,
        )
    except Exception as exc:
        from .index_ledger import DeferredIndexEmbeddingError

        if isinstance(exc, DeferredIndexEmbeddingError):
            from ..assistant.time_beijing import next_beijing_midnight

            task.status = STATUS_PENDING
            task.available_at = next_beijing_midnight(runtime.now())
            task.lease_owner = None
            task.lease_expires_at = None
            task.lease_token = None
            task.worker_fence = None
            task.provider_state = "deferred"
            task.version += 1
            task.last_error_summary = "index embedding budget deferred"
            task.updated_at = runtime.now()
            return
        raise
    _succeed(task, runtime)


def _identity(value: str | None, field: str) -> str:
    if value is None or value.strip().lower() in FORBIDDEN_IDENTITY_VALUES:
        raise RuntimeError(f"{field} is missing or a placeholder")
    return value.strip()


def _manifest(generation: AssistantIndexGeneration) -> dict:
    built_at = generation.built_at.isoformat() if generation.built_at is not None else None
    return {
        "collection_name": generation.collection_name,
        "embedding_provider": generation.embedding_provider,
        "embedding_model": generation.embedding_model,
        "embedding_model_version": generation.embedding_model_version,
        "vector_dimension": generation.vector_dimension,
        "distance_metric": generation.distance_metric,
        "pipeline_version": generation.pipeline_version,
        "source_revision_set_digest": generation.source_revision_set_digest,
        "chunk_count": generation.chunk_count,
        "vector_count": generation.vector_count,
        "outbox_high_water": generation.outbox_high_water,
        "built_at": built_at,
    }


def _validate_switch(
    db: Session,
    runtime: AssistantIndexRuntime,
    generation: AssistantIndexGeneration,
) -> None:
    from .index_ledger import has_blocking_index_attempts

    if has_blocking_index_attempts(db, generation.id):
        raise RuntimeError("index embedding attempts require operator intervention")
    if generation.status != GEN_STAGING:
        raise RuntimeError("generation is not a complete staging build")
    _identity(generation.embedding_provider, "embedding_provider")
    _identity(generation.embedding_model, "embedding_model")
    _identity(generation.embedding_model_version, "embedding_model_version")
    _identity(generation.collection_name, "collection_name")
    if generation.vector_dimension != runtime.settings.assistant_embedding_dimension:
        raise RuntimeError("generation dimension does not match settings")
    if generation.pipeline_version != runtime.settings.assistant_pipeline_version:
        raise RuntimeError("generation pipeline version does not match settings")
    sqlite_count = (
        db.scalar(
            select(func.count())
            .select_from(AssistantChunk)
            .where(AssistantChunk.generation_id == generation.id)
        )
        or 0
    )
    sqlite_ids = set(
        db.scalars(
            select(AssistantChunk.chunk_id).where(AssistantChunk.generation_id == generation.id)
        ).all()
    )
    vector_count = runtime.store.count(generation.collection_name)
    qdrant_ids = runtime.store.chunk_ids(generation.collection_name)
    if sqlite_count != vector_count:
        raise RuntimeError("chunk count does not match vector count")
    if sqlite_ids != qdrant_ids:
        raise RuntimeError("qdrant contains unknown or missing chunks")
    if generation.chunk_count != sqlite_count or generation.vector_count != vector_count:
        raise RuntimeError("generation counts do not match stored rows")
    probe = [0.0] * generation.vector_dimension
    probe[0] = 1.0
    runtime.store.probe(generation.collection_name, probe)
    if generation.built_at is None or generation.source_revision_set_digest is None:
        raise RuntimeError("generation manifest is incomplete")
    from .integrity import audit_generation

    audit_generation(db, runtime, generation).require_passed()


def switch_generation(db: Session, runtime: AssistantIndexRuntime, staging_id: int) -> None:
    del db, runtime, staging_id
    raise RuntimeError("generation activation requires API-owner finalize")


def _open_rebuild(db: Session) -> AssistantIndexCommand | None:
    return db.scalar(
        select(AssistantIndexCommand)
        .where(
            AssistantIndexCommand.status.in_(
                ("pending", "running", "waiting", "catch_up")
            )
        )
        .order_by(AssistantIndexCommand.created_at.asc(), AssistantIndexCommand.id.asc())
        .limit(1)
    )


def _initialize_rebuild(db: Session, runtime: AssistantIndexRuntime, command, fence: int) -> None:
    dimension = runtime.settings.assistant_embedding_dimension
    if dimension is None:
        raise AssistantIndexConfigurationError("assistant_embedding_dimension is required")
    pointer = ensure_pointer(db)
    generation = AssistantIndexGeneration(
        status=GEN_STAGING,
        collection_name=f"{runtime.settings.assistant_qdrant_collection_prefix}_pending",
        embedding_provider=_identity(
            runtime.settings.assistant_embedding_provider, "assistant_embedding_provider"
        ),
        embedding_model=_identity(
            runtime.settings.assistant_embedding_model, "assistant_embedding_model"
        ),
        embedding_model_version=_identity(
            runtime.settings.assistant_embedding_model_version,
            "assistant_embedding_model_version",
        ),
        vector_dimension=dimension,
        distance_metric=DISTANCE_COSINE,
        pipeline_version=pipeline_version_from(db),
        outbox_high_water=db.scalar(select(func.max(AssistantIndexTask.id))) or 0,
        created_at=runtime.now(),
        updated_at=runtime.now(),
    )
    db.add(generation)
    db.flush()
    generation.collection_name = (
        f"{runtime.settings.assistant_qdrant_collection_prefix}_{generation.id}"
    )
    command.generation_id = generation.id
    command.previous_generation_id = pointer.active_generation_id
    command.worker_fence = fence
    command.outbox_high_water = generation.outbox_high_water
    command.status = "running"
    command.version += 1
    command.updated_at = runtime.now()
    documents = iter_public_sources(db)
    for document in documents:
        db.add(
            AssistantIndexRebuildProgress(
                command_id=command.id,
                source_type=document.source_type,
                source_id=document.source_id,
                source_version=document.source_version,
                status="pending",
                available_at=runtime.now(),
                updated_at=runtime.now(),
            )
        )
    db.commit()
    require_worker_fence(runtime, fence)
    if not runtime.store.collection_exists(generation.collection_name):
        runtime.store.create_collection(
            generation.collection_name,
            dimension=dimension,
            distance=DISTANCE_COSINE,
        )
    require_worker_fence(runtime, fence)
    record_provider_fact(
        runtime,
        kind="qdrant",
        status="healthy",
        reason="local_mutation_succeeded",
        outcome="success",
    )


def _sync_rebuild_progress(db: Session, runtime, command) -> list[SourceDocument]:
    documents = iter_public_sources(db)
    current = {(item.source_type, item.source_id): item for item in documents}
    rows = list(
        db.scalars(
            select(AssistantIndexRebuildProgress).where(
                AssistantIndexRebuildProgress.command_id == command.id
            )
        ).all()
    )
    seen = {(row.source_type, row.source_id): row for row in rows}
    for key, document in current.items():
        row = seen.get(key)
        if row is None:
            db.add(
                AssistantIndexRebuildProgress(
                    command_id=command.id,
                    source_type=document.source_type,
                    source_id=document.source_id,
                    source_version=document.source_version,
                    status="pending",
                    available_at=runtime.now(),
                    updated_at=runtime.now(),
                )
            )
        elif row.source_version != document.source_version:
            row.source_version = document.source_version
            row.status = "dirty"
            row.available_at = runtime.now()
            row.updated_at = runtime.now()
    for key, row in seen.items():
        if key not in current and row.source_version != "0":
            row.source_version = "0"
            row.status = "dirty"
            row.available_at = runtime.now()
            row.updated_at = runtime.now()
    db.flush()
    return documents


def _finish_rebuild_if_ready(db: Session, runtime, command, generation, fence: int) -> bool:
    open_progress = int(
        db.scalar(
            select(func.count())
            .select_from(AssistantIndexRebuildProgress)
            .where(
                AssistantIndexRebuildProgress.command_id == command.id,
                AssistantIndexRebuildProgress.status != "succeeded",
            )
        )
        or 0
    )
    task_query = select(func.count()).select_from(AssistantIndexTask).where(
        AssistantIndexTask.status.in_((STATUS_PENDING, STATUS_LEASED))
    )
    if command.previous_generation_id is None:
        task_query = task_query.where(
            AssistantIndexTask.id > int(command.outbox_high_water or 0)
        )
    open_tasks = int(db.scalar(task_query) or 0)
    if open_progress or open_tasks:
        return False
    require_worker_fence(runtime, fence)
    documents = iter_public_sources(db)
    digest_value = source_revision_set_digest(documents)
    generation.source_revision_set_digest = digest_value
    generation.outbox_high_water = db.scalar(select(func.max(AssistantIndexTask.id))) or 0
    generation.chunk_count = int(
        db.scalar(
            select(func.count())
            .select_from(AssistantChunk)
            .where(AssistantChunk.generation_id == generation.id)
        )
        or 0
    )
    generation.vector_count = runtime.store.count(generation.collection_name)
    generation.built_at = runtime.now()
    generation.updated_at = runtime.now()
    generation.manifest_json = json.dumps(_manifest(generation), sort_keys=True)
    with FenceHeartbeat(runtime, fence):
        _validate_switch(db, runtime, generation)
    require_worker_fence(runtime, fence)
    command.status = "ready_to_switch"
    command.worker_fence = fence
    command.source_revision_set_digest = digest_value
    command.outbox_high_water = generation.outbox_high_water
    command.manifest_json = generation.manifest_json
    command.safe_error_code = None
    command.version += 1
    command.updated_at = runtime.now()
    db.commit()
    return True


def process_rebuild_command(runtime: AssistantIndexRuntime, fence: int) -> bool:
    with runtime.database.session_factory() as db:
        db.info["settings"] = runtime.settings
        command = _open_rebuild(db)
        if command is None:
            return False
        if command.generation_id is None:
            _initialize_rebuild(db, runtime, command, fence)
            return True
        generation = db.get(AssistantIndexGeneration, command.generation_id)
        if generation is None or generation.status != GEN_STAGING:
            command.status = "failed"
            command.safe_error_code = "rebuild_failed"
            command.version += 1
            command.updated_at = runtime.now()
            command.terminal_at = runtime.now()
            db.commit()
            return True
        if not runtime.store.collection_exists(generation.collection_name):
            require_worker_fence(runtime, fence)
            runtime.store.create_collection(
                generation.collection_name,
                dimension=generation.vector_dimension,
                distance=DISTANCE_COSINE,
            )
        documents = _sync_rebuild_progress(db, runtime, command)
        current = {(item.source_type, item.source_id): item for item in documents}
        progress = db.scalar(
            select(AssistantIndexRebuildProgress)
            .where(
                AssistantIndexRebuildProgress.command_id == command.id,
                AssistantIndexRebuildProgress.status.in_(("pending", "dirty", "waiting")),
                AssistantIndexRebuildProgress.available_at <= runtime.now(),
            )
            .order_by(AssistantIndexRebuildProgress.id.asc())
            .limit(1)
        )
        if progress is None:
            if _finish_rebuild_if_ready(db, runtime, command, generation, fence):
                return True
            command.status = "waiting"
            command.updated_at = runtime.now()
            db.commit()
            return False
        progress.status = "running"
        command.status = "running"
        command.source_cursor = f"{progress.source_type}:{progress.source_id}"
        command.worker_fence = fence
        command.updated_at = runtime.now()
        db.commit()
        document = current.get((progress.source_type, progress.source_id))
        try:
            if document is None:
                delete_source_index(
                    db,
                    runtime,
                    generation,
                    progress.source_type,
                    progress.source_id,
                    fence=fence,
                    task_id=None,
                    lease_token=None,
                )
            else:
                _index_document(
                    db,
                    runtime,
                    generation,
                    document,
                    fence=fence,
                    task_id=None,
                    lease_token=None,
                )
            progress.status = "succeeded"
            progress.updated_at = runtime.now()
            command.status = "running"
            command.version += 1
            command.updated_at = runtime.now()
            db.commit()
            return True
        except Exception as exc:
            from .index_ledger import DeferredIndexEmbeddingError

            if isinstance(exc, DeferredIndexEmbeddingError):
                from ..assistant.time_beijing import next_beijing_midnight

                progress.status = "waiting"
                progress.available_at = next_beijing_midnight(runtime.now())
                progress.updated_at = runtime.now()
                command.status = "waiting"
                command.version += 1
                command.updated_at = runtime.now()
                db.commit()
                return False
            db.rollback()
            with runtime.database.session_factory() as failure_db:
                failed_command = failure_db.get(AssistantIndexCommand, command.id)
                failed_generation = failure_db.get(AssistantIndexGeneration, generation.id)
                failed_progress = failure_db.get(AssistantIndexRebuildProgress, progress.id)
                if failed_command is not None:
                    failed_command.status = "failed"
                    failed_command.safe_error_code = (
                        "worker_fence_lost"
                        if isinstance(exc, WorkerFenceLost)
                        else "rebuild_failed"
                    )
                    failed_command.version += 1
                    failed_command.updated_at = runtime.now()
                    failed_command.terminal_at = runtime.now()
                if failed_generation is not None:
                    failed_generation.status = GEN_FAILED
                    failed_generation.updated_at = runtime.now()
                if failed_progress is not None:
                    failed_progress.status = "failed"
                    failed_progress.updated_at = runtime.now()
                failure_db.commit()
            return True


def rebuild_generation(runtime: AssistantIndexRuntime) -> int:
    with runtime.database.session_factory() as db:
        db.execute(text("BEGIN IMMEDIATE"))
        active = db.scalar(
            select(AssistantIndexCommand)
            .where(AssistantIndexCommand.status.in_(
                ("pending", "running", "waiting", "catch_up", "ready_to_switch")
            ))
            .order_by(AssistantIndexCommand.created_at.desc())
        )
        if active is None:
            now = runtime.now()
            active = AssistantIndexCommand(
                id=random_id(),
                kind="rebuild",
                idempotency_key_hash=random_id(),
                status="pending",
                version=1,
                manifest_json="{}",
                created_at=now,
                updated_at=now,
            )
            db.add(active)
            db.commit()
            operation_id = active.id
        else:
            operation_id = active.id
            if active.status == "ready_to_switch" and active.generation_id is not None:
                return active.generation_id
    for _ in range(100000):
        process_once(runtime)
        with runtime.database.session_factory() as db:
            operation = db.get(AssistantIndexCommand, operation_id)
            if operation is None:
                raise RuntimeError("rebuild operation disappeared")
            if operation.status == "ready_to_switch" and operation.generation_id is not None:
                return operation.generation_id
            if operation.status in {"failed", "abandoned"}:
                raise RuntimeError("rebuild operation failed")
            if operation.status == "waiting":
                raise RuntimeError("rebuild operation is waiting for budget")
    raise RuntimeError("rebuild operation did not reach ready_to_switch")


def process_once(runtime: AssistantIndexRuntime) -> bool:
    from ..assistant_resume.queue import process_resume_once

    if process_resume_once(runtime):
        return True
    lock = content_write_fence(runtime.settings)
    try:
        lock.acquire()
    except AssistantOwnerLockError:
        return False
    try:
        return _process_once_fenced(runtime)
    finally:
        lock.release()


def _process_once_fenced(runtime: AssistantIndexRuntime) -> bool:
    with runtime.database.session_factory() as db:
        db.info["settings"] = runtime.settings
        db.execute(text("BEGIN IMMEDIATE"))
        ensure_assistant_fts(db)
        fence = acquire_worker_owner(db, runtime)
        if fence is None:
            db.rollback()
            return False
        reclaim_expired_leases(db, runtime.now())
        pointer = ensure_pointer(db)
        task = (
            lease_next_task(db, runtime, fence)
            if pointer.active_generation_id is not None
            else None
        )
        task_id = task.id if task is not None else None
        db.commit()
    if task_id is not None:
        with runtime.database.session_factory() as db:
            db.info["settings"] = runtime.settings
            task = db.get(AssistantIndexTask, task_id)
            if task is None:
                return True
            generation = _active_generation(db)
            try:
                apply_task(db, runtime, task, generation, fence=fence)
                db.commit()
            except Exception as exc:
                db.rollback()
                with runtime.database.session_factory() as fail_db:
                    fail_db.info["settings"] = runtime.settings
                    leased = fail_db.get(AssistantIndexTask, task_id)
                    if (
                        leased is not None
                        and leased.worker_fence == fence
                        and leased.lease_owner == runtime.owner
                    ):
                        _fail_or_retry(leased, runtime, exc)
                        fail_db.commit()
                logger.warning("assistant index incremental task_id=%s failed", task_id)
            return True
    return process_rebuild_command(runtime, fence)


def run_forever(runtime: AssistantIndexRuntime) -> None:
    while True:
        worked = process_once(runtime)
        if not worked:
            time.sleep(runtime.settings.assistant_index_poll_seconds)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gavin assistant hybrid-index worker")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    settings = get_settings()
    if not settings.assistant_index_worker_enabled:
        print("assistant index worker is disabled", file=sys.stderr)
        return 1
    try:
        validate_assistant_worker_settings(settings)
        runtime = build_runtime(settings, Database(settings.database_url))
        if args.rebuild:
            rebuild_generation(runtime)
            return 0
        if args.once:
            process_once(runtime)
            return 0
        run_forever(runtime)
        return 0
    except AssistantIndexConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
