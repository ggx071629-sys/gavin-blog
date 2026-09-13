from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable


class FrontMatterError(ValueError):
    pass


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


def parse_front_matter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontMatterError("missing opening front matter delimiter")

    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration as error:
        raise FrontMatterError("missing closing front matter delimiter") from error

    data: dict[str, Any] = {}
    active_list: str | None = None
    for raw_line in lines[1:end]:
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        stripped = raw_line.strip()
        if stripped.startswith("- "):
            if active_list is None:
                raise FrontMatterError("list item without a key")
            data[active_list].append(_scalar(stripped[2:]))
            continue
        if ":" not in raw_line:
            raise FrontMatterError(f"invalid metadata line: {raw_line}")
        key, value = raw_line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise FrontMatterError("empty metadata key")
        if value:
            data[key] = _scalar(value)
            active_list = None
        else:
            data[key] = []
            active_list = key

    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return data, body


def _scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def markdown_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.md")):
        if path.name == "INDEX.md":
            continue
        if any(part in SKIP_PARTS for part in path.relative_to(root).parts):
            continue
        yield path


def values_as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value in (None, ""):
        return []
    return [str(value)]
