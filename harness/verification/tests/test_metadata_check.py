from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from harness.verification.checks import metadata as metadata_check

PROJECT_DOCUMENTS = [
    "README.md",
    "apps/web/README.md",
    "apps/api/README.md",
    "packages/contracts/README.md",
]


def _write_document(path: Path, document_id: str, *, summary: str = "Fixture") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"id: {document_id}\n"
        "level: L1\n"
        f"summary: {summary}\n"
        "load_when:\n"
        "  - fixture\n"
        "---\n\n"
        "# Fixture\n",
        encoding="utf-8",
    )


def _context(tmp_path: Path, project_documents: object) -> dict[str, object]:
    project = tmp_path / "project"
    harness = project / "harness"
    (harness / "docs").mkdir(parents=True)
    return {
        "project_root": project,
        "harness_root": harness,
        "config": {
            "metadata": {
                "required": ["id", "level", "summary", "load_when"],
                "project_documents": project_documents,
            },
            "levels": {"routable": ["L1", "L2"]},
            "specs": {"active": "specs/active"},
            "indexes": {"docs": {"path": "docs"}},
        },
    }


def test_live_project_document_scope_and_l0_source_are_explicit() -> None:
    root = Path(__file__).resolve().parents[3]
    with (root / "harness" / "config.toml").open("rb") as handle:
        config = tomllib.load(handle)

    assert config["metadata"]["project_documents"] == PROJECT_DOCUMENTS
    assert "AGENTS.md" in config["verification"]["source_paths"]


@pytest.mark.parametrize("broken", PROJECT_DOCUMENTS)
def test_each_project_document_requires_shared_front_matter(
    tmp_path: Path,
    broken: str,
) -> None:
    context = _context(tmp_path, PROJECT_DOCUMENTS)
    project = context["project_root"]
    assert isinstance(project, Path)
    for index, target in enumerate(PROJECT_DOCUMENTS):
        _write_document(project / target, f"project-{index}")
    (project / broken).write_text("# Missing front matter\n", encoding="utf-8")

    result = metadata_check.run(context)

    assert result["passed"] is False
    assert any(
        detail.startswith(f"{broken}: missing opening front matter delimiter")
        for detail in result["details"]
    )


def test_project_and_indexed_documents_share_global_id_uniqueness(tmp_path: Path) -> None:
    context = _context(tmp_path, ["README.md"])
    project = context["project_root"]
    harness = context["harness_root"]
    assert isinstance(project, Path)
    assert isinstance(harness, Path)
    _write_document(project / "README.md", "duplicate-id")
    _write_document(harness / "docs" / "baseline.md", "duplicate-id")

    result = metadata_check.run(context)

    assert result["passed"] is False
    assert any("duplicate id also used by" in detail for detail in result["details"])


@pytest.mark.parametrize(
    ("configured", "message"),
    [
        ("README.md", "must be a list"),
        (["../README.md"], "safe project-relative POSIX paths"),
        (["README.txt"], "must be a Markdown file"),
        (["missing.md"], "configured project document is missing"),
        (["README.md", "README.md"], "duplicate project document path"),
    ],
)
def test_project_document_configuration_fails_closed(
    tmp_path: Path,
    configured: object,
    message: str,
) -> None:
    context = _context(tmp_path, configured)
    project = context["project_root"]
    assert isinstance(project, Path)
    _write_document(project / "README.md", "project-readme")

    result = metadata_check.run(context)

    assert result["passed"] is False
    assert any(message in detail for detail in result["details"])


def test_valid_indexed_and_project_documents_are_counted_together(tmp_path: Path) -> None:
    context = _context(tmp_path, ["README.md"])
    project = context["project_root"]
    harness = context["harness_root"]
    assert isinstance(project, Path)
    assert isinstance(harness, Path)
    _write_document(project / "README.md", "project-readme")
    _write_document(harness / "docs" / "baseline.md", "harness-baseline")

    result = metadata_check.run(context)

    assert result == {
        "name": "metadata",
        "passed": True,
        "details": ["2 routed Markdown documents have valid metadata"],
    }
