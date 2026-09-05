from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SKIP_PARTS = {
    ".git",
    ".agents",
    ".codex",
    ".run",
    ".nuxt",
    ".output",
    ".venv",
    "__pycache__",
    "artifacts",
    "local",
    "node_modules",
}


def markdown_files(root: Path):
    """Prune local/dependency trees before traversal, not after rglob scans them."""
    def failed(error):
        raise error
    for directory, folders, files in os.walk(root, followlinks=False, onerror=failed):
        parent = Path(directory)
        folders[:] = sorted(
            name for name in folders
            if name not in SKIP_PARTS
            and not (getattr((parent/name).lstat(), 'st_file_attributes', 0) & 0x400)
            and not (parent/name).is_symlink()
        )
        for name in sorted(files):
            if name.endswith('.md'):
                yield parent/name


def _target(raw: str) -> str:
    value = raw.strip().strip("<>")
    if " " in value and not value.startswith(("/", "./", "../")):
        value = value.split(" ", 1)[0]
    return value.split("#", 1)[0].split("?", 1)[0]


def run(context: dict[str, Any]) -> dict[str, Any]:
    project_root: Path = context["project_root"]
    broken: list[str] = []
    unstable: list[str] = []
    checked = 0
    active_specs = project_root / "harness" / "specs" / "active"
    specs_root = project_root / "harness" / "specs"
    for path in markdown_files(project_root):
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
                continue
            if (
                resolved.is_relative_to(active_specs)
                and not path.resolve().is_relative_to(specs_root)
            ):
                source = path.relative_to(project_root).as_posix()
                unstable.append(
                    f"{source}: durable Markdown must not link short-lived active spec {target}"
                )
    failures = broken + unstable
    details = failures or [
        f"{checked} local Markdown links resolve without durable active-spec references"
    ]
    return {"name": "links", "passed": not failures, "details": details}
