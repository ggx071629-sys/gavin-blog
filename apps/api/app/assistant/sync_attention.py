"""Read-only reconciliation of failed upserts against committed active-index facts.

This is not a live vector health probe or settlement of an old provider attempt.
Uncertain facts and failed removals remain actionable.
"""
from collections import defaultdict

from sqlalchemy import bindparam, select, text

from ..assistant_index.chunker import chunk_source
from ..assistant_index.fts import lexical_index_text
from ..assistant_index.projector import project_source
from ..models import (
    AssistantChunk,
    AssistantIndexCommand,
    AssistantIndexGeneration,
    AssistantIndexPointer,
    AssistantIndexTask,
)


def covered_failed_task_ids(db, runtime, tasks=None) -> set[int]:
    if runtime is None:
        return set()
    rows = list(tasks) if tasks is not None else list(db.scalars(
        select(AssistantIndexTask).where(AssistantIndexTask.status == "failed")
    ))
    candidates = [row for row in rows if row.status == "failed" and row.operation == "upsert"]
    if not candidates:
        return set()
    pointer = db.get(AssistantIndexPointer, 1)
    generation = db.get(AssistantIndexGeneration, pointer.active_generation_id) if (
        pointer and pointer.active_generation_id is not None
    ) else None
    if generation is None or generation.status != "active":
        return set()
    settings = runtime.settings
    if any(getattr(generation, field) != getattr(settings, setting) for field, setting in (
        ("embedding_provider", "assistant_embedding_provider"),
        ("embedding_model", "assistant_embedding_model"),
        ("embedding_model_version", "assistant_embedding_model_version"),
        ("vector_dimension", "assistant_embedding_dimension"),
        ("pipeline_version", "assistant_pipeline_version"),
    )):
        return set()
    db.info["settings"] = settings
    built = bool(generation.built_at and db.scalar(select(AssistantIndexCommand.id).where(
        AssistantIndexCommand.generation_id == generation.id,
        AssistantIndexCommand.status == "switched",
    ).limit(1)))
    covered_sources = set()
    for source_type, source_id in {(row.source_type, row.source_id) for row in candidates}:
        try:
            document = project_source(db, source_type, source_id)
            if document is None:
                continue
            succeeded = built or db.scalar(select(AssistantIndexTask.id).where(
                AssistantIndexTask.source_type == source_type,
                AssistantIndexTask.source_id == source_id,
                AssistantIndexTask.target_version == document.source_version,
                AssistantIndexTask.pipeline_version == document.pipeline_version,
                AssistantIndexTask.operation == "upsert",
                AssistantIndexTask.status == "succeeded",
                AssistantIndexTask.updated_at >= generation.created_at,
            ).limit(1))
            if not succeeded:
                continue
            drafts = chunk_source(
                document, chunk_size=settings.assistant_chunk_size,
                chunk_overlap=settings.assistant_chunk_overlap,
                tokenizer=getattr(runtime.embeddings, "tokenizer", None),
            )
            expected = {draft.chunk_id: draft for draft in drafts}
            chunks = list(db.scalars(select(AssistantChunk).where(
                AssistantChunk.generation_id == generation.id,
                AssistantChunk.source_type == source_type,
                AssistantChunk.source_id == source_id,
            )))
            if not expected or len(chunks) != len(expected):
                continue
            if any(
                chunk.chunk_id not in expected
                or chunk.source_version != document.source_version
                or chunk.pipeline_version != document.pipeline_version
                or chunk.title != document.title or chunk.public_path != document.public_path
                or any(getattr(chunk, field) != getattr(expected[chunk.chunk_id], field)
                       for field in ("ordinal", "heading_path", "page_content", "content_hash"))
                for chunk in chunks
            ):
                continue
            fts = defaultdict(list)
            query = text(
                "SELECT chunk_id,title,heading_path,body FROM assistant_chunk_fts "
                "WHERE generation_id=:g AND chunk_id IN :ids"
            ).bindparams(bindparam("ids", expanding=True))
            for row in db.execute(query, {"g": generation.id, "ids": list(expected)}):
                fts[row[0]].append(tuple(row[1:]))
            if any(fts[chunk.chunk_id] not in (
                [(chunk.title, chunk.heading_path, chunk.page_content)],
                [tuple(lexical_index_text(value) for value in (
                    chunk.title, chunk.heading_path, chunk.page_content,
                ))],
            ) for chunk in chunks):
                continue
            covered_sources.add((source_type, source_id))
        except Exception:
            # Missing projection/tokenizer/FTS facts must not hide a failure.
            continue
    return {row.id for row in candidates if (row.source_type, row.source_id) in covered_sources}
