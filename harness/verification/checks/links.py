from __future__ import annotations

import re
from pathlib import Path
from typing import Any


LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SKIP_PARTS = {
    ".git",
    ".nuxt",
    ".output",
    ".venv",
    "__pycache__",
    "artifacts",
    "local",
    "node_modules",
}


def _target(raw: str) -> str:
    value = raw.strip().strip("<>")
    if " " in value and not value.startswith(("/", "./", "../")):
        value = value.split(" ", 1)[0]
    return value.split("#", 1)[0]


def run(context: dict[str, Any]) -> dict[str, Any]:
    project_root: Path = context["project_root"]
    broken: list[str] = []
    checked = 0
    for path in sorted(project_root.rglob("*.md")):
        if any(part in SKIP_PARTS for part in path.relative_to(project_root).parts):
            continue
        text = path.read_text(encoding="utf-8")
        for match in LINK.finditer(text):
            raw = match.group(1)
            if raw.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = _target(raw)
            if not target:
                continue
            checked += 1
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                source = path.relative_to(project_root).as_posix()
                broken.append(f"{source}: missing link target {target}")
    details = broken or [f"{checked} local Markdown links resolve"]
    return {"name": "links", "passed": not broken, "details": details}
