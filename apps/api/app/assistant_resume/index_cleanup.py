from __future__ import annotations

from sqlalchemy import delete, select

from ..assistant_index.fts import delete_fts_ids
from ..assistant_index.worker_control import FenceHeartbeat, require_worker_fence
from ..models import AssistantChunk, AssistantIndexGeneration


def purge_version(db, runtime, task, fence: int) -> None:
    """A tombstone can never delete a later resume version, even after URL reuse."""
    from ..models import AssistantResumeSource
    from .storage import current_version

    row = db.get(AssistantResumeSource, 1, populate_existing=True)
    current = current_version(db, row) if row else None
    if current is not None and current.id == task.target_version:
        raise RuntimeError("refusing_current_resume_purge")
    for generation in db.scalars(select(AssistantIndexGeneration)).all():
        ids = list(
            db.scalars(
                select(AssistantChunk.chunk_id).where(
                    AssistantChunk.generation_id == generation.id,
                    AssistantChunk.source_type == "resume",
                    AssistantChunk.source_version == task.target_version,
                )
            )
        )
        require_worker_fence(runtime, fence, task_id=task.id, token=task.lease_token)
        if runtime.store.collection_exists(generation.collection_name):
            with FenceHeartbeat(runtime, fence, task_id=task.id, token=task.lease_token):
                runtime.store.delete_source_version(
                    generation.collection_name,
                    source_type="resume",
                    source_id=1,
                    source_version=task.target_version,
                )
        require_worker_fence(runtime, fence, task_id=task.id, token=task.lease_token)
        delete_fts_ids(db, ids, generation_id=generation.id)
        db.execute(
            delete(AssistantChunk).where(
                AssistantChunk.generation_id == generation.id,
                AssistantChunk.source_type == "resume",
                AssistantChunk.source_version == task.target_version,
            )
        )
