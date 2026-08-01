from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .config import harness_root, load_config, project_root
from .metadata import parse_front_matter, values_as_list


def validate_task_id(task_id: str) -> None:
    pattern = str(load_config()["specs"]["task_id_pattern"])
    if re.fullmatch(pattern, task_id) is None:
        raise ValueError(f"invalid task_id: {task_id}")


def active_spec(task_id: str) -> Path:
    validate_task_id(task_id)
    config = load_config()
    return harness_root() / str(config["specs"]["active"]) / f"{task_id}.md"


def ensure_spec_in_git_history(path: Path) -> None:
    relative = path.relative_to(project_root()).as_posix()
    result = subprocess.run(
        ["git", "cat-file", "-e", f"HEAD:{relative}"],
        cwd=project_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "refusing to close: the active spec is not preserved in Git HEAD"
        )


def _section(body: str, heading: str) -> str:
    pattern = re.compile(
        rf"^## {re.escape(heading)}\s*$\n(?P<body>.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(body)
    return match.group("body").strip() if match else "Not recorded."


def close_spec(task_id: str) -> tuple[Path, str]:
    config = load_config()
    source = active_spec(task_id)
    if not source.is_file():
        raise FileNotFoundError(f"active spec not found: {source}")
    if bool(config["specs"]["require_git_history_before_close"]):
        ensure_spec_in_git_history(source)

    source_text = source.read_text(encoding="utf-8")
    metadata, body = parse_front_matter(source)
    archive_dir = harness_root() / str(config["specs"]["archive"])
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive = archive_dir / f"{task_id}.md"
    if archive.exists():
        raise FileExistsError(f"archive already exists: {archive}")

    author = metadata.get("author")
    author_line = f"author: {author}\n" if author else ""
    load_when = values_as_list(metadata.get("load_when")) or [f"task:{task_id}"]
    load_lines = "\n".join(f"  - {value}" for value in load_when)
    content = (
        "---\n"
        f"id: archive-{task_id}\n"
        "level: L2\n"
        f"summary: {metadata.get('summary', task_id)}\n"
        "load_when:\n"
        f"{load_lines}\n"
        f"{author_line}"
        f"task_id: {task_id}\n"
        "status: compressed\n"
        "---\n\n"
        f"# {task_id}\n\n"
        "Deterministic compressed record. The original active spec remains in Git history.\n\n"
        "## Goal\n\n"
        f"{_section(body, 'Goal')}\n\n"
        "## Acceptance criteria\n\n"
        f"{_section(body, 'Acceptance criteria')}\n\n"
        "## Result\n\n"
        "Verified and closed by the harness close command.\n\n"
        "## Evidence\n\n"
        f"[{task_id}.json](../../verification/evidence/{task_id}.json)\n\n"
        f"Closed at {datetime.now(timezone.utc).isoformat()}.\n"
    )
    archive.write_text(content, encoding="utf-8", newline="\n")
    source.unlink()
    return archive, source_text


def restore_spec(task_id: str, source_text: str, archive: Path | None) -> None:
    source = active_spec(task_id)
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(source_text, encoding="utf-8", newline="\n")
    if archive is not None and archive.exists():
        archive.unlink()

