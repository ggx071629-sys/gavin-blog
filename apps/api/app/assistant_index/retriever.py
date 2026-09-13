from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..models import AssistantChunk, AssistantIndexGeneration
from ..search import safe_match_query
from .constants import RRF_K
from .fts import lexical_fallback_query, lexical_match_query
from .projector import project_source
from .runtime import AssistantIndexRuntime
from .worker import ensure_pointer

logger = logging.getLogger("gavin.assistant_index")


@dataclass(frozen=True)
class RetrievalCandidate:
    chunk_id: str
    rank: int
    sources: tuple[str, ...]
    rrf_score: float


@dataclass(frozen=True)
class RetrievalResult:
    status: str
    degraded: bool
    candidates: list[RetrievalCandidate]


def _not_ready() -> RetrievalResult:
    return RetrievalResult(status="not_ready", degraded=False, candidates=[])


def _fts_search(db: Session, generation_id: int, query: str, limit: int) -> list[str]:
    for match in _match_expressions(query):
        rows = _fts_hits(db, generation_id, match, limit)
        if rows:
            return rows
    return []


def _match_expressions(query: str) -> list[str]:
    """Precise CJK/term matching first, then relaxed, then the legacy expression.

    The legacy form keeps pre-existing generations that were indexed before the
    lexical projection useful until the index is rebuilt.
    """
    candidates = [
        lexical_match_query(query),
        lexical_fallback_query(query),
        safe_match_query(query),
    ]
    ordered: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in ordered:
            ordered.append(candidate)
    return ordered


def _fts_hits(db: Session, generation_id: int, match: str, limit: int) -> list[str]:
    rows = db.execute(
        text(
            """
            SELECT chunk_id
            FROM assistant_chunk_fts
            WHERE assistant_chunk_fts MATCH :query
              AND generation_id = :generation_id
            ORDER BY bm25(assistant_chunk_fts), chunk_id
            LIMIT :limit
            """
        ),
        {"query": match, "generation_id": generation_id, "limit": limit},
    ).scalars()
    return [str(chunk_id) for chunk_id in rows]


def _rrf(
    fts_ids: list[str],
    dense_ids: list[str],
    k: int = RRF_K,
) -> list[tuple[str, float, tuple[str, ...]]]:
    scores: dict[str, float] = {}
    sources: dict[str, list[str]] = {}
    for rank, chunk_id in enumerate(fts_ids, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
        sources.setdefault(chunk_id, []).append("fts")
    for rank, chunk_id in enumerate(dense_ids, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
        sources.setdefault(chunk_id, []).append("dense")
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [(chunk_id, score, tuple(sources[chunk_id])) for chunk_id, score in ranked]


def retrieve(
    db: Session,
    runtime: AssistantIndexRuntime,
    query: str,
    *,
    limit: int = 32,
    query_vector: list[float] | None = None,
    skip_dense: bool = False,
) -> RetrievalResult:
    pointer = ensure_pointer(db)
    if pointer.active_generation_id is None:
        return _not_ready()
    generation = db.get(AssistantIndexGeneration, pointer.active_generation_id)
    if generation is None or generation.status != "active":
        return _not_ready()
    fetch_limit = max(limit * 4, 16)
    try:
        fts_ids = _fts_search(db, generation.id, query, fetch_limit)
    except Exception as exc:
        logger.warning("assistant fts unavailable: %s", type(exc).__name__)
        return _not_ready()
    dense_ids: list[str] = []
    dense_failed = bool(skip_dense)
    if not skip_dense:
        try:
            if not runtime.store.collection_exists(generation.collection_name):
                raise RuntimeError("active collection missing")
            vector = (
                query_vector if query_vector is not None else runtime.embeddings.embed_query(query)
            )
            dense_ids = [
                hit.chunk_id
                for hit in runtime.store.search(
                    generation.collection_name,
                    vector,
                    limit=fetch_limit,
                )
            ]
        except Exception as exc:
            logger.warning("assistant dense branch unavailable: %s", type(exc).__name__)
            dense_failed = True
    fused = _rrf(fts_ids, dense_ids)
    groups: dict[tuple[str, int, str], list[tuple[str, float, tuple[str, ...]]]] = {}
    for chunk_id, score, sources in fused:
        chunk = db.scalar(
            select(AssistantChunk).where(
                AssistantChunk.generation_id == generation.id,
                AssistantChunk.chunk_id == chunk_id,
            )
        )
        if chunk is None:
            continue
        current = project_source(db, chunk.source_type, chunk.source_id)
        if current is None or current.source_version != chunk.source_version:
            continue
        key = (chunk.source_type, chunk.source_id, chunk.source_version)
        groups.setdefault(key, []).append((chunk_id, score, sources))
    # Apply the limit after source diversity, not after individual chunk rank.
    # Preserve the best-hit source order and each source's internal relevance.
    ordered = [
        items[index]
        for index in range(max((len(items) for items in groups.values()), default=0))
        for items in groups.values()
        if index < len(items)
    ]
    candidates: list[RetrievalCandidate] = []
    for chunk_id, score, sources in ordered[:limit]:
        candidates.append(
            RetrievalCandidate(
                chunk_id=chunk_id,
                rank=len(candidates) + 1,
                sources=sources,
                rrf_score=score,
            )
        )
    if dense_failed:
        return RetrievalResult(status="degraded", degraded=True, candidates=candidates)
    return RetrievalResult(status="ok", degraded=False, candidates=candidates)
