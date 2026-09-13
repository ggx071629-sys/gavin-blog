from __future__ import annotations

from typing import Any

from tools.indexer import expected_indexes


def run(context: dict[str, Any]) -> dict[str, Any]:
    root = context["harness_root"]
    stale: list[str] = []
    expected = expected_indexes()
    for path, content in expected.items():
        relative = path.relative_to(root).as_posix()
        if not path.is_file():
            stale.append(f"missing generated index: {relative}")
        elif path.read_text(encoding="utf-8") != content:
            stale.append(f"stale generated index: {relative}")
    details = stale or [f"{len(expected)} generated indexes are current"]
    return {"name": "indexes", "passed": not stale, "details": details}

