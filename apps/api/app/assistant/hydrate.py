from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from sqlalchemy.orm import Session

from ..assistant_index.projector import SourceDocument, project_source
from ..assistant_index.retriever import RetrievalResult, retrieve
from ..assistant_index.runtime import AssistantIndexRuntime
from ..models import ArticleRevision, AssistantChunk, AssistantIndexGeneration
from .preflight import scan_evidence
from .question_intent import (
    PERSONAL_SOURCES,
    asks_personal_skills,
    diverse_skill_evidence,
    personal_priority,
)


@dataclass(frozen=True)
class Evidence:
    alias: str
    chunk_id: str
    title: str
    heading_path: str
    public_path: str
    body: str
    source_type: str
    source_id: int
    source_version: str
    generation_id: int
    sources: tuple[str, ...]
    content_role: str = "unknown"

    def descriptor(self) -> dict[str, object]:
        return {
            "alias": self.alias,
            "chunk_id": self.chunk_id,
            "title": self.title,
            "heading_path": self.heading_path,
            "public_path": self.public_path,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_version": self.source_version,
            "generation_id": self.generation_id,
            "sources": list(self.sources),
        }


@dataclass(frozen=True)
class HydratedRetrieval:
    status: str
    degraded: bool
    generation_id: int | None
    evidence: list[Evidence]
    isolated_chunk_ids: tuple[str, ...]
    candidate_count: int = 0


def _article_parts(db: Session, source: SourceDocument) -> tuple[str, str]:
    """Read only the already validated published revision; never infer from rank."""
    if source.source_type != "article" or not source.source_version.isdecimal():
        return "", ""
    revision = db.get(ArticleRevision, int(source.source_version))
    if revision is None or revision.article_id != source.source_id:
        return "", ""
    content = revision.content or ""
    if content and not source.body.endswith(content):
        return "", ""
    metadata = source.body[:-len(content)] if content else source.body
    return " ".join(metadata.split()), " ".join(content.split())


def _content_role(body: str, parts: tuple[str, str]) -> str:
    # Whitespace folding only classifies origin. Evidence and quotes remain exact.
    text = " ".join(body.split())
    if not text:
        return "unknown"
    in_metadata, in_body = (text in part for part in parts)
    if in_metadata == in_body:
        return "unknown"
    return "metadata" if in_metadata else "body"


def hydrate_evidence(
    db: Session,
    runtime: AssistantIndexRuntime,
    query: str,
    *,
    limit: int,
    query_vector: list[float] | None = None,
    skip_dense: bool = False,
    current_path: str | None = None,
    max_chars: int,
    question: str | None = None,
) -> HydratedRetrieval:
    result: RetrievalResult = retrieve(
        db,
        runtime,
        query,
        limit=limit,
        query_vector=query_vector,
        skip_dense=skip_dense,
    )
    pointer_generation = None
    if result.status == "not_ready":
        return HydratedRetrieval("not_ready", False, None, [], ())
    from ..assistant_index.worker import ensure_pointer

    pointer = ensure_pointer(db)
    pointer_generation = pointer.active_generation_id
    generation = (
        db.get(AssistantIndexGeneration, pointer_generation) if pointer_generation else None
    )
    isolated: list[str] = []
    evidence: list[Evidence] = []
    parts: dict[tuple[str, int, str], tuple[str, str]] = {}
    ranked = list(result.candidates)
    personal_question = asks_personal_skills(question or query)
    if personal_question:
        from ..assistant_index.retriever import RetrievalCandidate

        # Directly include bounded personal sources from the active generation.
        # They still pass the same live projection, version and injection checks below.
        personal = db.query(AssistantChunk).filter(
            AssistantChunk.generation_id == pointer_generation,
            AssistantChunk.source_type.in_(PERSONAL_SOURCES),
        ).order_by(AssistantChunk.ordinal, AssistantChunk.chunk_id).limit(64).all()
        personal.sort(key=lambda c: personal_priority(
            c.source_type, c.heading_path, c.page_content,
        ))
        seen = {c.chunk_id for c in personal}
        ranked = [RetrievalCandidate(c.chunk_id, i + 1, ('personal',), 0.0)
                  for i, c in enumerate(personal)] + [
                      candidate for candidate in ranked if candidate.chunk_id not in seen
                  ]
    if current_path:
        ranked.sort(
            key=lambda item: (0 if _path_matches(db, item.chunk_id, current_path) else 1, item.rank)
        )
    for candidate in ranked:
        chunk = (
            db.query(AssistantChunk)
            .filter_by(
                generation_id=pointer_generation,
                chunk_id=candidate.chunk_id,
            )
            .one_or_none()
        )
        if chunk is None:
            continue
        current = project_source(db, chunk.source_type, chunk.source_id)
        if current is None or current.source_version != chunk.source_version:
            continue
        if any(scan_evidence(value) for value in (
            chunk.title, chunk.heading_path, chunk.page_content,
        )):
            isolated.append(chunk.chunk_id)
            continue
        body = chunk.page_content
        if not body:
            continue
        key = (current.source_type, current.source_id, current.source_version)
        if key not in parts:
            parts[key] = _article_parts(db, current)
        evidence.append(
            Evidence(
                alias=f"c{len(evidence) + 1}",
                chunk_id=chunk.chunk_id,
                title=chunk.title,
                heading_path=chunk.heading_path,
                public_path=chunk.public_path,
                body=body,
                source_type=chunk.source_type,
                source_id=chunk.source_id,
                source_version=chunk.source_version,
                generation_id=chunk.generation_id,
                sources=candidate.sources,
                content_role=_content_role(body, parts[key]),
            )
        )
    if personal_question:
        evidence = diverse_skill_evidence(evidence, lambda item: item.source_type)
    selected: list[Evidence] = []
    used = 0
    for item in evidence:
        if len(item.body) > max_chars - used:
            continue
        selected.append(replace(item, alias=f'c{len(selected) + 1}'))
        used += len(item.body)
        if len(selected) >= limit:
            break
    degraded = result.degraded or skip_dense
    return HydratedRetrieval(
        result.status if not degraded else "degraded",
        degraded,
        generation.id if generation is not None else pointer_generation,
        selected,
        tuple(isolated),
        len(ranked),
    )


def _path_matches(db: Session, chunk_id: str, current_path: str) -> bool:
    chunk = db.query(AssistantChunk).filter_by(chunk_id=chunk_id).first()
    return bool(chunk and chunk.public_path == current_path)


def hydrate_descriptors(db: Session, descriptors: list[dict[str, Any]]) -> list[Evidence]:
    """Hydrate only descriptors still bound to the current published projection."""
    from ..assistant_index.worker import ensure_pointer

    pointer = ensure_pointer(db)
    live: list[Evidence] = []
    parts: dict[tuple[str, int, str], tuple[str, str]] = {}
    for item in descriptors:
        generation_id = int(item["generation_id"])
        if pointer.active_generation_id != generation_id:
            continue
        chunk = (
            db.query(AssistantChunk)
            .filter_by(generation_id=generation_id, chunk_id=str(item["chunk_id"]))
            .one_or_none()
        )
        if chunk is None or chunk.source_version != str(item["source_version"]):
            continue
        current = project_source(db, chunk.source_type, chunk.source_id)
        if current is None or current.source_version != chunk.source_version:
            continue
        if any(scan_evidence(value) for value in (
            chunk.title, chunk.heading_path, chunk.page_content,
        )):
            continue
        key = (current.source_type, current.source_id, current.source_version)
        if key not in parts:
            parts[key] = _article_parts(db, current)
        live.append(
            Evidence(
                alias=str(item["alias"]),
                chunk_id=chunk.chunk_id,
                title=chunk.title,
                heading_path=chunk.heading_path,
                public_path=chunk.public_path,
                body=chunk.page_content,
                source_type=chunk.source_type,
                source_id=chunk.source_id,
                source_version=chunk.source_version,
                generation_id=chunk.generation_id,
                sources=tuple(str(value) for value in item.get("sources", [])),
                content_role=_content_role(chunk.page_content, parts[key]),
            )
        )
    return live
