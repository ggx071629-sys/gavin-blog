from __future__ import annotations

import importlib.util
from pathlib import Path

CHECK_PATH = Path(__file__).parents[1] / "checks" / "links.py"


def _load_check():
    spec = importlib.util.spec_from_file_location("harness_links_check", CHECK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_durable_markdown_cannot_link_active_spec(tmp_path: Path) -> None:
    active = tmp_path / "harness" / "specs" / "active" / "20260802-example.md"
    _write(active, "# Example\n")
    _write(
        tmp_path / "README.md",
        "[unstable](harness/specs/active/20260802-example.md)\n",
    )

    result = _load_check().run({"project_root": tmp_path})

    assert result["passed"] is False
    assert "short-lived active spec" in result["details"][0]


def test_index_archive_and_spec_coordination_links_are_allowed(tmp_path: Path) -> None:
    active = tmp_path / "harness" / "specs" / "active" / "20260802-example.md"
    archive = tmp_path / "harness" / "specs" / "archive" / "20260801-done.md"
    index = tmp_path / "harness" / "specs" / "INDEX.md"
    _write(active, "[temporary](20260802-example.md)\n")
    _write(archive, "# Done\n")
    _write(index, "# Specifications\n")
    _write(
        tmp_path / "README.md",
        "[specs](harness/specs/INDEX.md) [archive](harness/specs/archive/20260801-done.md)\n",
    )

    result = _load_check().run({"project_root": tmp_path})

    assert result["passed"] is True
    assert result["details"] == [
        "3 local Markdown links resolve without durable active-spec references"
    ]
