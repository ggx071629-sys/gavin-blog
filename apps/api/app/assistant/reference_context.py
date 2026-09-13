"""Bounded source reference resolution; never infer an ordinal from answer prose."""

from __future__ import annotations

import re

from ..assistant_index.projector import project_source
from ..assistant_index.worker import ensure_pointer
from ..models import AssistantChunk
from .preflight import scan_evidence
from .store import public_completed_turn_at, session_is_live

REFERENCE = re.compile(
    r"它|(?<!其)他(?!们)|她(?!们)|该(?:项目|文章|书|笔记)|上述|前面(?:的)?(?:项目|文章)|"
    r"\b(?:it|its|that (?:project|article|book|note)|the (?:former|latter))\b",
    re.I,
)
ORDINAL = re.compile(
    r"第[一二三四五六七八九十0-9]+个|"
    r"\b(?:first|second|third)\s+(?:one|project|article)\b|\bthe (?:former|latter)\b",
    re.I,
)
SWITCH = re.compile(
    r"换(?:个)?话题|另一个问题|\b(?:new topic|change (?:the )?topic|unrelated question)\b", re.I
)


def needs_reference(question: str) -> bool:
    return bool(REFERENCE.search(question) or ORDINAL.search(question))


def resolve_reference(online, state) -> dict | None:
    """Read only the latest successful retained pair's source locations.

    An updated source is re-projected now; its previous answer is never read as
    evidence. No source body or previous question is copied to graph state.
    """
    question = state["question"]
    if ORDINAL.search(question) or SWITCH.search(question):
        return None

    def latest(conn):
        if not session_is_live(conn, state["session_id"], online.now()):
            return None
        row = conn.execute(
            """SELECT t.* FROM assistant_history h JOIN assistant_turns t ON t.id = h.turn_id
               WHERE h.session_id = ? ORDER BY h.id DESC LIMIT 1""",
            (state["session_id"],),
        ).fetchone()
        return public_completed_turn_at(dict(row), online.now()) if row else None

    previous = online.control.read(latest)
    if not previous or not previous["body_available"]:
        return None
    sources = previous.get("sources") or []
    targets = {(s.get("path"), s.get("title")) for s in sources}
    if len(targets) != 1:
        return None
    path, title = targets.pop()
    with online.content_session() as db:
        generation = ensure_pointer(db).active_generation_id
        chunks = (
            db.query(AssistantChunk)
            .filter_by(
                generation_id=generation,
                public_path=path,
                title=title,
            )
            .all()
        )
        targets = {(c.source_type, c.source_id) for c in chunks}
        if len(targets) != 1:
            return None
        source_type, source_id = targets.pop()
        document = project_source(db, source_type, source_id)
        if (
            document is None
            or document.public_path != path
            or scan_evidence(document.title)
            or not any(c.source_version == document.source_version for c in chunks)
        ):
            return None
        return dict(
            source_type=source_type,
            source_id=source_id,
            source_version=document.source_version,
            public_path=path,
            title=document.title,
        )


def reference_is_current(db, reference: dict) -> bool:
    document = project_source(db, reference["source_type"], reference["source_id"])
    return bool(
        document
        and document.source_version == reference["source_version"]
        and document.public_path == reference["public_path"]
    )
