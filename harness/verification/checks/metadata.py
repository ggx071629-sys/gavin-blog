from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.lifecycle import validate_active_spec
from tools.metadata import FrontMatterError, markdown_files, parse_front_matter, values_as_list


def run(context: dict[str, Any]) -> dict[str, Any]:
    root: Path = context["harness_root"]
    config = context["config"]
    required = [str(value) for value in config["metadata"]["required"]]
    levels = set(str(value) for value in config["levels"]["routable"])
    details: list[str] = []
    seen: dict[str, Path] = {}
    checked = 0
    active_root = root / str(config["specs"]["active"])

    for item in config["indexes"].values():
        scope = root / str(item["path"])
        for path in markdown_files(scope):
            checked += 1
            relative = path.relative_to(root).as_posix()
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
                    first = seen[document_id].relative_to(root).as_posix()
                    details.append(f"{relative}: duplicate id also used by {first}")
                else:
                    seen[document_id] = path

            if path.parent == active_root:
                for error in validate_active_spec(path):
                    details.append(f"{relative}: {error}")

    passed = not details
    if passed:
        details = [f"{checked} routed Markdown documents have valid metadata"]
    return {"name": "metadata", "passed": passed, "details": details}
