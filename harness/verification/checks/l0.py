from __future__ import annotations

from pathlib import Path
from typing import Any

REQUIRED_STATEMENTS = {
    "explicit L1 routing": (
        "selected by that index or explicitly named by this L0 map",
        "After changing metadata on indexed Harness documents",
    ),
    "command working directories": (
        "Run Harness CLI commands from `harness/`",
        "root npm commands from the repository root",
        "uv/Alembic/API commands from `apps/api/`",
    ),
}


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
        content = "\n".join(lines)
        if not 60 <= len(lines) <= 80:
            details.append(f"AGENTS.md has {len(lines)} lines; expected 60-80")
        if "This file is the only L0 document" not in content:
            details.append("AGENTS.md does not declare the unique L0 boundary")
        if "Never preload or recursively read all" not in content:
            details.append("AGENTS.md does not prohibit bulk docs loading")
        for label, fragments in REQUIRED_STATEMENTS.items():
            if any(fragment not in content for fragment in fragments):
                details.append(f"AGENTS.md is missing the {label} contract")

    passed = not details
    if passed:
        details = ["AGENTS.md is the unique L0 and stays within 60-80 lines"]
    return {
        "name": "l0",
        "passed": passed,
        "details": details,
    }
