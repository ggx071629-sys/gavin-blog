from __future__ import annotations

from pathlib import Path
from typing import Any


def run(context: dict[str, Any]) -> dict[str, Any]:
    root: Path = context["harness_root"]
    required = context["config"]["structure"]["required"]
    missing = [
        value
        for value in required
        if not (root / str(value)).resolve().exists()
    ]
    details = [f"missing required path: {value}" for value in missing]
    if not details:
        details = [f"{len(required)} required paths exist"]
    return {"name": "structure", "passed": not missing, "details": details}

