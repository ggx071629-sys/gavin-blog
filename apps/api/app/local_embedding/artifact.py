from __future__ import annotations

import hashlib
import json
from pathlib import Path

MODEL = "intfloat/multilingual-e5-small"
REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
REPRESENTATION = "e5-fp32-mean-l2-v1"
VERSION = f"{REVISION}:{REPRESENTATION}"
PIPELINE = "assistant-e5-token384-overlap64-v1"
DIMENSION = 384
MAX_TOKENS = 512
LOCK_PATH = Path(__file__).with_name("model.lock.json")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_artifact(directory: Path, *, tokenizer_only: bool = False) -> dict:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    if lock["model"] != MODEL or lock["revision"] != REVISION:
        raise RuntimeError("unsupported E5 artifact identity")
    for name, expected in lock["files"].items():
        if tokenizer_only and name != "tokenizer.json":
            continue
        path = directory / name
        if not path.is_file() or sha256(path) != expected["sha256"]:
            raise RuntimeError(f"E5 artifact missing or hash mismatch: {name}")
    return lock
