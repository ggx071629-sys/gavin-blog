"""Explicit download only; serving never accesses Hugging Face."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.local_embedding.artifact import LOCK_PATH, MODEL, REVISION, sha256, verify_artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path("data/models/multilingual-e5-small"))
    args = parser.parse_args()
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    for name, expected in lock["files"].items():
        target = args.directory / name
        if target.is_file() and sha256(target) == expected["sha256"]:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".partial")
        url = f"https://huggingface.co/{MODEL}/resolve/{REVISION}/{name}"
        print(f"Downloading {name}", flush=True)
        with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as stream:
            while block := response.read(1024 * 1024):
                stream.write(block)
        if sha256(temporary) != expected["sha256"]:
            raise RuntimeError(f"download hash mismatch: {name}")
        temporary.replace(target)
    verify_artifact(args.directory)
    print(f"Verified {MODEL}@{REVISION}")


if __name__ == "__main__":
    main()
