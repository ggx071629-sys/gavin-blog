from __future__ import annotations

from pathlib import Path
from typing import Any


def run(context: dict[str, Any]) -> dict[str, Any]:
    project_root: Path = context["project_root"]
    config = context["config"]
    details: list[str] = []
    declared = [str(value) for value in config["levels"]["l0"]]
    expected = ["../AGENTS.md"]
    if declared != expected:
        details.append("AGENTS.md must be the only declared L0 document")

    path = project_root / "AGENTS.md"
    if not path.is_file():
        details.append("AGENTS.md is missing")
    else:
        lines = path.read_text(encoding="utf-8").splitlines()
        if not 60 <= len(lines) <= 80:
            details.append(f"AGENTS.md has {len(lines)} lines; expected 60-80")
        if "This file is the only L0 document" not in "\n".join(lines):
            details.append("AGENTS.md does not declare the unique L0 boundary")
        if "Never preload or recursively read all" not in "\n".join(lines):
            details.append("AGENTS.md does not prohibit bulk docs loading")

    if not details:
        details = ["AGENTS.md is the unique L0 and stays within 60-80 lines"]
    return {"name": "l0", "passed": len(details) == 1 and details[0].startswith("AGENTS.md is"), "details": details}

