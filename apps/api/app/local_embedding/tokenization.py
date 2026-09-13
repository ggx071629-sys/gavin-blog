from __future__ import annotations

from pathlib import Path

from tokenizers import Tokenizer  # type: ignore[import-untyped]

from .artifact import MAX_TOKENS, verify_artifact


class E5Tokenizer:
    def __init__(self, directory: Path) -> None:
        verify_artifact(directory, tokenizer_only=True)
        self.inner = Tokenizer.from_file(str(directory / "tokenizer.json"))
        self.inner.no_truncation()
        self.inner.no_padding()

    def count(self, text: str, *, special: bool = True) -> int:
        return len(self.inner.encode(text, add_special_tokens=special).ids)

    def retrieval_query(self, current: str, history: list[str]) -> tuple[str, bool]:
        # Never discard the current question, including its tail.
        if self.count("query: " + current) > MAX_TOKENS:
            return current, True
        query = current
        for question in reversed(history):
            # FTS shares this query and truncates terms from the tail.
            candidate = query + " " + str(question)
            if self.count("query: " + candidate) > MAX_TOKENS:
                break
            query = candidate
        return query, False

    def split(self, text: str, *, size: int = 384, overlap: int = 64) -> list[str]:
        # Token offsets slice original Unicode, preserving code and citation text.
        # Re-encode every emitted substring: word boundaries can change token counts.
        pieces: list[str] = []
        start = 0
        while start < len(text):
            remainder = text[start:]
            encoded = self.inner.encode(remainder, add_special_tokens=False)
            if not encoded.ids:
                break
            end = len(remainder)
            if len(encoded.ids) > size:
                end = encoded.offsets[size - 1][1]
                # Prefer paragraph/line ends in the latter half of a chunk.
                boundary = remainder.rfind("\n", end // 2, end)
                if boundary >= 0:
                    end = boundary + 1
            while end > 0 and (
                self.count(remainder[:end], special=False) > size
                or self.count("passage: " + remainder[:end]) > MAX_TOKENS
            ):
                end -= 1
            if end <= 0:
                raise ValueError("cannot form a valid E5 chunk")
            piece = remainder[:end]
            if piece.strip():
                pieces.append(piece.strip())
            if end == len(remainder):
                break
            offsets = self.inner.encode(piece, add_special_tokens=False).offsets
            advance = offsets[-overlap][0] if len(offsets) > overlap else end
            start += max(1, advance)
        return pieces
