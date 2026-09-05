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


def test_local_query_links_resolve_files_and_keep_missing_and_durable_checks(tmp_path: Path) -> None:
    check = _load_check()
    (tmp_path / "desk.html").write_text("<main>Desk</main>", encoding="utf-8")
    document = tmp_path / "README.md"
    document.write_text("[desk](desk.html?page=articles&theme=light#main)\n[current](?theme=dark#main)", encoding="utf-8")
    assert check.run({"project_root": tmp_path})["passed"] is True

    document.write_text("[missing](missing.html?page=articles)", encoding="utf-8")
    result = check.run({"project_root": tmp_path})
    assert result["passed"] is False
    assert "missing link target missing.html" in result["details"][0]

    active = tmp_path / "harness" / "specs" / "active" / "20260905-example.md"
    active.parent.mkdir(parents=True)
    active.write_text("# Spec", encoding="utf-8")
    document.write_text("[active](harness/specs/active/20260905-example.md?view=source#goal)", encoding="utf-8")
    result = check.run({"project_root": tmp_path})
    assert result["passed"] is False
    assert "durable Markdown must not link short-lived active spec" in result["details"][0]


def test_link_check_never_traverses_installed_dependencies_or_local_artifacts(tmp_path, monkeypatch):
    check=_load_check()
    skipped=['node_modules','.venv','.run','.git','.agents','.codex']
    for name in skipped:
        _write(tmp_path/name/'deep'/'report.md','[broken](missing.md)')
    _write(tmp_path/'README.md','[guide](docs/guide.md)')
    _write(tmp_path/'docs/guide.md','[root](../README.md)')
    original=check.os.scandir
    visited=[]
    def scandir(path):
        value=Path(path)
        if value.is_relative_to(tmp_path):
            assert not set(value.relative_to(tmp_path).parts)&set(skipped)
            visited.append(value)
        return original(path)
    monkeypatch.setattr(check.os,'scandir',scandir)
    result=check.run({'project_root':tmp_path})
    assert result['passed'] and len(visited)==2
