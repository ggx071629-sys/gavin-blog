"""Build-time fetch only. Runtime tokenization has no download path."""
from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from app.assistant.deepseek_tokenizer import REVISION, SHA256

ROOT = f"https://raw.githubusercontent.com/deepseek-ai/deepseek-recipe/{REVISION}"
FILES = {
    "tokenizer.json": ("static/tokenizers/v41/tokenizer.json", SHA256),
    "LICENSE": (
        "static/tokenizers/LICENSE",
        "f2c6c602815669d292889e5be8c802f2ed950653b77999b1584e8e6aed25d040",
    ),
}


def main() -> None:
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    for name, (source, expected) in FILES.items():
        target = destination / name
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
            continue
        with urllib.request.urlopen(f"{ROOT}/{source}", timeout=45) as response:
            data = response.read(10 * 1024 * 1024 + 1)
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError(f"Official tokenizer artifact checksum mismatch: {name}")
        target.write_bytes(data)
        target.chmod(0o644)
    print(f"Prepared verified DeepSeek V4.1 tokenizer at revision {REVISION}")


if __name__ == "__main__":
    main()
