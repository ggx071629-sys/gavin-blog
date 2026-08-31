from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from tools.lifecycle import validate_active_spec
    from tools.metadata import (
        FrontMatterError,
        markdown_files,
        parse_front_matter,
        values_as_list,
    )
except ModuleNotFoundError:  # pragma: no cover - repository-root test imports
    from harness.tools.lifecycle import validate_active_spec
    from harness.tools.metadata import (
        FrontMatterError,
        markdown_files,
        parse_front_matter,
        values_as_list,
    )


def _project_documents(
    project_root: Path,
    config: dict[str, Any],
    details: list[str],
) -> list[Path]:
    raw_documents = config["metadata"].get("project_documents", [])
    if not isinstance(raw_documents, list):
        details.append("metadata.project_documents must be a list")
        return []

    documents: list[Path] = []
    seen_paths: set[str] = set()
    for raw in raw_documents:
        if not isinstance(raw, str):
            details.append("metadata.project_documents entries must be strings")
            continue
        target = raw.strip()
        parts = target.split("/")
        if (
            not target
            or "\\" in target
            or target.startswith("/")
            or any(part in {"", ".", ".."} for part in parts)
            or ":" in parts[0]
        ):
            details.append(
                "metadata.project_documents must use safe project-relative POSIX paths"
            )
            continue
        if not target.lower().endswith(".md"):
            details.append(f"{target}: project document must be a Markdown file")
            continue
        if target in seen_paths:
            details.append(f"{target}: duplicate project document path")
            continue
        seen_paths.add(target)
        path = (project_root / target).resolve()
        if not path.is_relative_to(project_root.resolve()):
            details.append(f"{target}: project document must stay inside the project")
            continue
        if not path.is_file():
            details.append(f"{target}: configured project document is missing")
            continue
        documents.append(path)
    return documents


def run(context: dict[str, Any]) -> dict[str, Any]:
    root: Path = context["harness_root"]
    project_root: Path = context["project_root"]
    config = context["config"]
    required = [str(value) for value in config["metadata"]["required"]]
    levels = set(str(value) for value in config["levels"]["routable"])
    details: list[str] = []
    seen: dict[str, str] = {}
    checked = 0
    active_root = root / str(config["specs"]["active"])

    documents: list[Path] = []
    for item in config["indexes"].values():
        scope = root / str(item["path"])
        documents.extend(markdown_files(scope))
    documents.extend(_project_documents(project_root, config, details))

    for path in documents:
        checked += 1
        relative = path.relative_to(project_root).as_posix()
        try:
            metadata, _ = parse_front_matter(path)
        except FrontMatterError as error:
            details.append(f"{relative}: {error}")
            continue

        for key in required:
            if key not in metadata or metadata[key] in ("", []):
                details.append(f"{relative}: missing {key}")
        level = str(metadata.get("level", ""))
        if level and level not in levels:
            details.append(f"{relative}: level must be L1 or L2")
        if not values_as_list(metadata.get("load_when")):
            details.append(f"{relative}: load_when must not be empty")

        document_id = str(metadata.get("id", ""))
        if document_id:
            if document_id in seen:
                details.append(f"{relative}: duplicate id also used by {seen[document_id]}")
            else:
                seen[document_id] = relative

        if path.parent == active_root:
            for error in validate_active_spec(path):
                details.append(f"{relative}: {error}")

    passed = not details
    if passed:
        details = [f"{checked} routed Markdown documents have valid metadata"]
    return {"name": "metadata", "passed": passed, "details": details}
