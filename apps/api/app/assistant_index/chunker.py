from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from .constants import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE
from .projector import SourceDocument

FENCE_RE = re.compile(r"(```[\s\S]*?```|~~~[\s\S]*?~~~)")
SCRIPT_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
EVENT_ATTR_RE = re.compile(
    r"\son[a-z]+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)",
    re.IGNORECASE,
)
HIDDEN_BLOCK_RE = re.compile(
    r"<[^>]*("
    r"\bhidden\b|"
    r"aria-hidden\s*=\s*['\"]true['\"]|"
    r"style\s*=\s*['\"][^'\"]*display\s*:\s*none"
    r")[^>]*>.*?</[^>]+>",
    re.IGNORECASE | re.DOTALL,
)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
MUSTACHE_RE = re.compile(r"\{\{[\s\S]*?\}\}")
HEADER_SPLITTERS = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
    ("####", "h4"),
    ("#####", "h5"),
    ("######", "h6"),
]
MARKDOWN_SEPARATORS = [
    "\n```",
    "\n## ",
    "\n### ",
    "\n#### ",
    "\n\n",
    "\n- ",
    "\n* ",
    "\n1. ",
    "\n",
    " ",
    "",
]


@dataclass(frozen=True)
class ChunkDraft:
    ordinal: int
    heading_path: str
    page_content: str
    content_hash: str
    chunk_id: str


def _sanitize_markup(text: str) -> str:
    text = COMMENT_RE.sub("", text)
    text = SCRIPT_RE.sub("", text)
    text = HIDDEN_BLOCK_RE.sub("", text)
    text = EVENT_ATTR_RE.sub("", text)
    text = MUSTACHE_RE.sub("", text)
    return text


def sanitize_markdown(value: str) -> str:
    normalized = (value or "").replace("\r\n", "\n")
    parts = FENCE_RE.split(normalized)
    cleaned: list[str] = []
    for part in parts:
        if part.startswith("```") or part.startswith("~~~"):
            cleaned.append(part)
        else:
            cleaned.append(_sanitize_markup(part))
    return "".join(cleaned).strip()


def stable_chunk_id(
    *,
    source_type: str,
    source_id: int,
    source_version: str,
    pipeline_version: str,
    ordinal: int,
    content_hash: str,
) -> str:
    material = "|".join(
        [
            source_type,
            str(source_id),
            source_version,
            pipeline_version,
            str(ordinal),
            content_hash,
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _heading_path(metadata: dict[str, str]) -> str:
    header_keys = ("h1", "h2", "h3", "h4", "h5", "h6")
    parts = [metadata[key] for key in header_keys if key in metadata]
    return " > ".join(parts)


def chunk_source(
    document: SourceDocument,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    tokenizer=None,
) -> list[ChunkDraft]:
    sanitized = sanitize_markdown(document.body)
    if not sanitized:
        sanitized = document.title
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADER_SPLITTERS,
        strip_headers=False,
    )
    sections = header_splitter.split_text(sanitized)
    if not sections:
        sections = [Document(page_content=sanitized, metadata={})]
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=MARKDOWN_SEPARATORS,
        keep_separator=True,
    )
    drafts: list[ChunkDraft] = []
    ordinal = 0
    for section in sections:
        heading_path = _heading_path(dict(section.metadata))
        pieces = (
            tokenizer.split(section.page_content, size=chunk_size, overlap=chunk_overlap)
            if tokenizer is not None else text_splitter.split_text(section.page_content)
        )
        if not pieces:
            pieces = [section.page_content]
        for piece in pieces:
            content = piece.strip()
            if not content:
                continue
            content_hash = hashlib.sha256(
                f"{heading_path}\n{content}".encode()
            ).hexdigest()
            drafts.append(
                ChunkDraft(
                    ordinal=ordinal,
                    heading_path=heading_path,
                    page_content=content,
                    content_hash=content_hash,
                    chunk_id=stable_chunk_id(
                        source_type=document.source_type,
                        source_id=document.source_id,
                        source_version=document.source_version,
                        pipeline_version=document.pipeline_version,
                        ordinal=ordinal,
                        content_hash=content_hash,
                    ),
                )
            )
            ordinal += 1
    if drafts:
        return drafts
    content_hash = hashlib.sha256(document.title.encode("utf-8")).hexdigest()
    return [
        ChunkDraft(
            ordinal=0,
            heading_path="",
            page_content=document.title,
            content_hash=content_hash,
            chunk_id=stable_chunk_id(
                source_type=document.source_type,
                source_id=document.source_id,
                source_version=document.source_version,
                pipeline_version=document.pipeline_version,
                ordinal=0,
                content_hash=content_hash,
            ),
        )
    ]
