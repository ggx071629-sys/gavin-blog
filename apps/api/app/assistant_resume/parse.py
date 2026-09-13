from __future__ import annotations

import base64
import io
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .download import MAX_BYTES, worker_environment
from .isolation import limit_memory, restrict_io

MAX_PAGES = 20
MAX_CHARS = 200000
PARSE_SECONDS = 15
PARSER_VERSION = "pypdf-6.18.0-text-v1"
ERROR_CODES = frozenset(
    {
        "not_pdf",
        "too_large",
        "too_many_pages",
        "encrypted_pdf",
        "text_unavailable",
        "parse_failed",
        "parser_unavailable",
        "parse_timeout",
        "text_too_large",
    }
)


class ParseError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ParsedPdf:
    pages: tuple[str, ...]
    body: str
    parser_version: str = PARSER_VERSION


def _body(pages: list[str]) -> str:
    return "\n\n".join(f"## 第 {n} 页\n\n{value}" for n, value in enumerate(pages, 1) if value)


def extract_pages(body: bytes) -> list[str]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(body), strict=True)
    if reader.is_encrypted:
        raise ParseError("encrypted_pdf")
    if len(reader.pages) > MAX_PAGES:
        raise ParseError("too_many_pages")
    pages: list[str] = []
    chars = 0
    for page in reader.pages:
        value = (page.extract_text() or "").strip()
        if not value and page.get_contents() is not None:
            raise ParseError("text_unavailable")
        chars += len(value)
        if chars > MAX_CHARS:
            raise ParseError("text_too_large")
        pages.append(value)
    if not any(pages):
        raise ParseError("text_unavailable")
    if len(_body(pages)) > MAX_CHARS:
        raise ParseError("text_too_large")
    return pages


def parse_pdf(body: bytes) -> ParsedPdf:
    if len(body) > MAX_BYTES:
        raise ParseError("too_large")
    if not body.startswith(b"%PDF-"):
        raise ParseError("not_pdf")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "app.assistant_resume.parse"],
            input=base64.b64encode(body),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=PARSE_SECONDS,
            env=worker_environment(),
            cwd=Path(__file__).resolve().parents[2],
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise ParseError("parse_timeout") from None
    except OSError:
        raise ParseError("parser_unavailable") from None
    try:
        if result.returncode != 0 or len(result.stdout) > MAX_CHARS * 6 + 1024:
            raise ValueError
        payload = json.loads(result.stdout)
        if "error" in payload:
            raise ParseError(
                payload["error"] if payload["error"] in ERROR_CODES else "parse_failed"
            )
        pages = payload["pages"]
        if not isinstance(pages, list) or not 1 <= len(pages) <= MAX_PAGES:
            raise ValueError
        if any(not isinstance(page, str) for page in pages) or not any(pages):
            raise ValueError
        text = _body(pages)
        if len(text) > MAX_CHARS:
            raise ValueError
        return ParsedPdf(tuple(pages), text)
    except (ValueError, TypeError, KeyError):
        raise ParseError("parse_failed") from None


def main() -> None:
    try:
        if not limit_memory():
            raise ParseError("parser_unavailable")
        restrict_io()
        encoded = sys.stdin.buffer.read(MAX_BYTES * 2 + 1)
        body = base64.b64decode(encoded, validate=True)
        if len(body) > MAX_BYTES:
            raise ParseError("too_large")
        result = {"pages": extract_pages(body)}
    except ParseError as exc:
        result = {"error": exc.code}
    except Exception:
        result = {"error": "parse_failed"}
    sys.stdout.write(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
