from __future__ import annotations

from pathlib import Path

from harness.verification.checks import l0 as l0_check


def _agents_text() -> str:
    required = [
        "This file is the only L0 document",
        "Never preload or recursively read all",
        "selected by that index or explicitly named by this L0 map",
        "After changing metadata on indexed Harness documents",
        "Run Harness CLI commands from `harness/`",
        "root npm commands from the repository root",
        "uv/Alembic/API commands from `apps/api/`",
    ]
    return "\n".join([*required, *(f"filler {index}" for index in range(53))]) + "\n"


def _context(project: Path) -> dict[str, object]:
    return {
        "project_root": project,
        "config": {"levels": {"l0": ["../AGENTS.md"]}},
    }


def test_l0_accepts_explicit_routes_and_command_working_directories(
    tmp_path: Path,
) -> None:
    (tmp_path / "AGENTS.md").write_text(_agents_text(), encoding="utf-8")

    result = l0_check.run(_context(tmp_path))

    assert result["passed"] is True


def test_l0_rejects_a_missing_command_working_directory(tmp_path: Path) -> None:
    text = _agents_text().replace("root npm commands from the repository root", "root commands")
    (tmp_path / "AGENTS.md").write_text(text, encoding="utf-8")

    result = l0_check.run(_context(tmp_path))

    assert result["passed"] is False
    assert "AGENTS.md is missing the command working directories contract" in result["details"]
