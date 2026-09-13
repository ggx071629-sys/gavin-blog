"""Exact index reconciliation; no embedding calls and no vector writes.

Callers hold the content write fence and a SQLite snapshot while auditing. Reports
contain identities and defect codes, never document bodies or credentials.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import asdict, dataclass, field

from sqlalchemy import select, text

from ..content_write_fence import content_write_fence
from ..models import AssistantChunk, AssistantIndexGeneration, AssistantIndexPointer
from .chunker import chunk_source
from .fts import lexical_index_text
from .projector import iter_public_sources
from .qdrant_store import point_uuid


@dataclass
class IntegrityReport:
    generation_id: int
    expected_sources: int = 0
    expected_chunks: int = 0
    canonical_chunks: int = 0
    fts_rows: int = 0
    fts_lexical_rows: int = 0
    vector_points: int = 0
    issues: list[dict[str, str]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.issues

    def defect(self, layer: str, code: str, identity: str = "") -> None:
        self.issues.append({"layer": layer, "code": code, "identity": identity})

    def as_dict(self) -> dict:
        return {**asdict(self), "status": "passed" if self.passed else "failed"}

    def require_passed(self) -> None:
        if not self.passed:
            raise IndexIntegrityError(self)


class IndexIntegrityError(RuntimeError):
    def __init__(self, report: IntegrityReport):
        self.report = report
        super().__init__("index integrity failed; run the read-only integrity audit")


def audit_generation(db, runtime, generation: AssistantIndexGeneration) -> IntegrityReport:
    report = IntegrityReport(generation.id)
    settings = runtime.settings
    db.info["settings"] = settings
    identity_fields = {
        "embedding_provider": settings.assistant_embedding_provider,
        "embedding_model": settings.assistant_embedding_model,
        "embedding_model_version": settings.assistant_embedding_model_version,
        "pipeline_version": settings.assistant_pipeline_version,
        "vector_dimension": settings.assistant_embedding_dimension,
    }
    for name, expected in identity_fields.items():
        if getattr(generation, name) != expected:
            report.defect("canonical", "generation_identity", name)
    # Public projection does not depend on an existing canonical or FTS entry;
    # in particular project_resume uses current_version, not usable_version.
    documents = iter_public_sources(db)
    report.expected_sources = len(documents)
    expected_rows = {}
    for document in documents:
        for draft in chunk_source(
            document, chunk_size=settings.assistant_chunk_size,
            chunk_overlap=settings.assistant_chunk_overlap,
            tokenizer=getattr(runtime.embeddings, "tokenizer", None),
        ):
            expected_rows[draft.chunk_id] = {
                "source_type": document.source_type, "source_id": document.source_id,
                "source_version": document.source_version,
                "pipeline_version": document.pipeline_version,
                "ordinal": draft.ordinal, "heading_path": draft.heading_path,
                "page_content": draft.page_content, "content_hash": draft.content_hash,
                "title": document.title, "public_path": document.public_path,
            }
    report.expected_chunks = len(expected_rows)
    chunks = list(db.scalars(select(AssistantChunk).where(
        AssistantChunk.generation_id == generation.id
    )))
    report.canonical_chunks = len(chunks)
    canonical = {row.chunk_id: row for row in chunks}
    if len(canonical) != len(chunks):
        report.defect("canonical", "duplicate")
    for chunk_id in sorted(expected_rows.keys() - canonical.keys()):
        report.defect("canonical", "missing", chunk_id)
    for chunk_id in sorted(canonical.keys() - expected_rows.keys()):
        report.defect("canonical", "extra_or_stale", chunk_id)
    for chunk_id in expected_rows.keys() & canonical.keys():
        if any(getattr(canonical[chunk_id], k) != v for k, v in expected_rows[chunk_id].items()):
            report.defect("canonical", "content_or_binding_mismatch", chunk_id)

    fts = defaultdict(list)
    try:
        rows = db.execute(text(
            "SELECT chunk_id, title, heading_path, body FROM assistant_chunk_fts "
            "WHERE generation_id=:g"
        ), {"g": generation.id}).all()
        report.fts_rows = len(rows)
        for row in rows:
            fts[row[0]].append(tuple(row[1:]))
    except Exception:
        report.defect("fts", "unavailable")
    for chunk_id, chunk in canonical.items():
        actual = fts.get(chunk_id, [])
        if not actual:
            report.defect("fts", "missing", chunk_id)
        elif len(actual) != 1:
            report.defect("fts", "duplicate", chunk_id)
        else:
            # Both the original text and the CJK-separated lexical projection are
            # valid, so an existing generation stays auditable until it is rebuilt.
            original = (chunk.title, chunk.heading_path, chunk.page_content)
            if actual[0] == original:
                continue
            if actual[0] == tuple(lexical_index_text(value) for value in original):
                report.fts_lexical_rows += 1
                continue
            report.defect("fts", "content_mismatch", chunk_id)
    for chunk_id in sorted(fts.keys() - canonical.keys()):
        report.defect("fts", "extra", chunk_id)

    expected_points = {point_uuid(generation.id, row.chunk_id): row for row in chunks}
    seen = set()
    try:
        client = runtime.store.client
        info = client.get_collection(generation.collection_name)
        vector_config = info.config.params.vectors
        if (getattr(vector_config, "size", None) != generation.vector_dimension
                or getattr(vector_config, "distance", None) != generation.distance_metric):
            report.defect("vector", "collection_config")
        offset = None
        while True:
            records, offset = client.scroll(
                collection_name=generation.collection_name, limit=256,
                offset=offset, with_payload=True, with_vectors=True,
            )
            for record in records:
                report.vector_points += 1
                point_id = str(record.id)
                if point_id in seen:
                    report.defect("vector", "duplicate", point_id)
                seen.add(point_id)
                chunk = expected_points.get(point_id)
                if chunk is None:
                    report.defect("vector", "extra_or_wrong_id", point_id)
                    continue
                payload = {
                    "chunk_id": chunk.chunk_id, "source_type": chunk.source_type,
                    "source_id": chunk.source_id, "source_version": chunk.source_version,
                    "generation": generation.id, "pipeline_version": chunk.pipeline_version,
                }
                if record.payload != payload:
                    report.defect("vector", "payload_mismatch", chunk.chunk_id)
                vector = record.vector
                if (not isinstance(vector, list) or len(vector) != generation.vector_dimension
                        or any(not isinstance(v, (int, float)) or not math.isfinite(v)
                               for v in vector) or not any(vector)):
                    report.defect("vector", "invalid_vector", chunk.chunk_id)
            if offset is None:
                break
        for point_id in sorted(expected_points.keys() - seen):
            report.defect("vector", "missing", expected_points[point_id].chunk_id)
    except Exception:
        report.defect("vector", "unavailable")
    return report


def active_generation(db):
    pointer = db.get(AssistantIndexPointer, 1)
    generation = db.get(AssistantIndexGeneration, pointer.active_generation_id) if (
        pointer and pointer.active_generation_id is not None
    ) else None
    if generation is None or generation.status != "active":
        raise RuntimeError("active index generation is missing")
    return generation


def require_active_integrity(runtime) -> IntegrityReport:
    with content_write_fence(runtime.settings), runtime.database.session_factory() as db:
        db.execute(text("BEGIN"))
        report = audit_generation(db, runtime, active_generation(db))
        report.require_passed()
        return report
