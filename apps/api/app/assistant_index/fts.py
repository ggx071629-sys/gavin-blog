from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import AssistantChunk

ASSISTANT_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS assistant_chunk_fts USING fts5(
    chunk_id UNINDEXED,
    generation_id UNINDEXED,
    title,
    heading_path,
    body,
    tokenize = 'unicode61 remove_diacritics 2'
)
"""

# CJK extension A, unified ideographs, compatibility ideographs and the
# supplementary planes. unicode61 keeps a run of these characters as one token,
# so substring queries cannot match it without a lexical projection below.
_CJK_RANGES = "\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002ffff"
_CJK_RUN = re.compile(rf"[{_CJK_RANGES}]+")
_MATCH_TOKEN = re.compile(
    rf"[{_CJK_RANGES}]+|[^\W_{_CJK_RANGES}]+(?:[-_][^\W_{_CJK_RANGES}]+)*",
    re.UNICODE,
)

MAX_MATCH_TOKENS = 12
MAX_CJK_PHRASES = 8
MIN_CJK_PHRASE_CHARS = 2


def lexical_index_text(value: str) -> str:
    """Space-separate CJK characters so unicode61 stores them as single terms.

    The text is otherwise unchanged, so an audited row still carries the original
    words and can be verified against the canonical chunk after the same
    transformation.
    """
    if not value:
        return ""
    spaced = re.sub(rf"([{_CJK_RANGES}])", r" \1 ", str(value))
    return re.sub(r"\s+", " ", spaced).strip()


def _cjk_phrases(run: str) -> list[str]:
    if len(run) < MIN_CJK_PHRASE_CHARS:
        return [f'"{run}"']
    phrases = [f'"{run[index]} {run[index + 1]}"' for index in range(len(run) - 1)]
    if len(phrases) > MAX_CJK_PHRASES:
        step = len(phrases) / MAX_CJK_PHRASES
        phrases = [phrases[int(index * step)] for index in range(MAX_CJK_PHRASES)]
    return phrases


def _match_terms(query: str, *, max_tokens: int = MAX_MATCH_TOKENS) -> list[str]:
    terms: list[str] = []
    for token in _MATCH_TOKEN.findall(str(query or ""))[:max_tokens]:
        if _CJK_RUN.fullmatch(token):
            options = _cjk_phrases(token)
            terms.append(
                options[0] if len(options) == 1 else "(" + " OR ".join(options) + ")"
            )
        else:
            terms.append(f'"{token}"*')
    return terms


def lexical_match_query(query: str, *, max_tokens: int = MAX_MATCH_TOKENS) -> str:
    """Precise form: every term must match, Chinese runs may match any character pair."""
    return " AND ".join(_match_terms(query, max_tokens=max_tokens))


def lexical_fallback_query(query: str, *, max_tokens: int = MAX_MATCH_TOKENS) -> str:
    """Relaxed form: any term may match, so a natural-language question still recalls."""
    return " OR ".join(_match_terms(query, max_tokens=max_tokens))


def ensure_assistant_fts(db: Session) -> None:
    db.execute(text(ASSISTANT_FTS_SQL))


def delete_fts_ids(db: Session, chunk_ids: list[str], *, generation_id: int) -> None:
    ensure_assistant_fts(db)
    if not chunk_ids:
        return
    placeholders = ", ".join(f":id_{index}" for index in range(len(chunk_ids)))
    params = {f"id_{index}": chunk_id for index, chunk_id in enumerate(chunk_ids)}
    params["generation_id"] = generation_id
    db.execute(
        text(
            "DELETE FROM assistant_chunk_fts WHERE generation_id = :generation_id "
            f"AND chunk_id IN ({placeholders})"
        ),
        params,
    )


def upsert_chunk_fts(db: Session, chunk: AssistantChunk) -> None:
    ensure_assistant_fts(db)
    delete_fts_ids(db, [chunk.chunk_id], generation_id=chunk.generation_id)
    db.execute(
        text(
            """
            INSERT INTO assistant_chunk_fts(
                chunk_id, generation_id, title, heading_path, body
            ) VALUES (:chunk_id, :generation_id, :title, :heading_path, :body)
            """
        ),
        {
            "chunk_id": chunk.chunk_id,
            "generation_id": chunk.generation_id,
            "title": lexical_index_text(chunk.title),
            "heading_path": lexical_index_text(chunk.heading_path),
            "body": lexical_index_text(chunk.page_content),
        },
    )


def delete_generation_fts(db: Session, generation_id: int) -> None:
    ensure_assistant_fts(db)
    db.execute(
        text("DELETE FROM assistant_chunk_fts WHERE generation_id = :generation_id"),
        {"generation_id": generation_id},
    )
