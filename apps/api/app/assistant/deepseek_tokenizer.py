"""Pinned, offline-only text tokenization for DeepSeek-V4.1-Flash.

This counts text, not the provider's complete message template or billing usage.
The prompt builder adds protocol headroom and falls back to a UTF-8 bound if unavailable.
"""
from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path

from tokenizers import Tokenizer  # type: ignore[import-untyped]

REVISION = "8cadfede7063c896b944e7bae05daa3549ae97ea"
SHA256 = "81f64d1248a68ce3663e07ab3ee48b851e5df0e32d27cb98e4c9a268151e8d99"
DEFAULT_PATH = "/opt/tokenizers/deepseek-v41/tokenizer.json"
PATH_ENV = "DEEPSEEK_V41_TOKENIZER_PATH"


@lru_cache(maxsize=1)
def _load(path: str) -> Tokenizer:
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise RuntimeError("DeepSeek V4.1 tokenizer is missing or unreadable") from exc
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise RuntimeError("DeepSeek V4.1 tokenizer checksum mismatch")
    tokenizer = Tokenizer.from_str(data.decode("utf-8"))
    tokenizer.no_truncation()
    tokenizer.no_padding()
    return tokenizer


def token_ids(text: str) -> list[int]:
    """No network, model weights, or automatic fallback downloads."""
    tokenizer = _load(os.environ.get(PATH_ENV, DEFAULT_PATH))
    return tokenizer.encode(text, add_special_tokens=False).ids
