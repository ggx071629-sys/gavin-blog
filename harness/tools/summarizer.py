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


def active_specs() -> list[Path]:
    config = load_config()
    root = harness_root() / str(config["specs"]["active"])
    return sorted(root.glob("*.md"))


def archive_spec(task_id: str) -> Path:
    validate_task_id(task_id)
    config = load_config()
    return harness_root() / str(config["specs"]["archive"]) / f"{task_id}.md"


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


def _required_section(body: str, heading: str) -> str:
    heading_pattern = re.compile(
        rf"^(?P<marks>#{{1,2}})[ \t]+{re.escape(heading)}[ \t]*$",
        re.MULTILINE,
    )
    match = heading_pattern.search(body)
    if match is None:
        raise ValueError(f"required non-empty section missing: {heading}")

    level = len(match.group("marks"))
    boundary_pattern = re.compile(rf"^#{{1,{level}}}[ \t]+", re.MULTILINE)
    boundary = boundary_pattern.search(body, match.end())
    end = boundary.start() if boundary else len(body)
    section = body[match.end() : end].strip()
    if not section:
        raise ValueError(f"required non-empty section missing: {heading}")
    return section


def close_spec(task_id: str, *, evidence_sha256: str | None = None) -> tuple[Path, str]:
    config = load_config()
    source = active_spec(task_id)
    if not source.is_file():
        raise FileNotFoundError(f"active spec not found: {source}")
    if bool(config["specs"]["require_git_history_before_close"]):
        ensure_spec_in_git_history(source)

    source_text = source.read_text(encoding="utf-8")
    metadata, body = parse_front_matter(source)
    status = str(metadata.get("status", ""))
    if status != "active":
        raise RuntimeError(f"refusing to close: spec status must be active, found {status or 'missing'}")
    goal = _required_section(body, "Goal")
    acceptance_criteria = _required_section(body, "Acceptance criteria")
    archive = archive_spec(task_id)
    archive_dir = archive.parent
    archive_dir.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        raise FileExistsError(f"archive already exists: {archive}")

    author = metadata.get("author")
    author_line = f"author: {author}\n" if author else ""
    load_when = values_as_list(metadata.get("load_when")) or [f"task:{task_id}"]
    load_lines = "\n".join(f"  - {value}" for value in load_when)
    state_history = values_as_list(metadata.get("state_history"))
    history_lines = "state_history:\n" + "\n".join(
        f"  - {value}" for value in state_history
    )
    if state_history:
        history_lines += "\n"
    documentation_impact = str(metadata.get("documentation_impact", "")).strip()
    documentation_reason = str(metadata.get("documentation_reason", "")).strip()
    documentation_targets = values_as_list(metadata.get("documentation_targets"))
    documentation_lines = ""
    if documentation_impact:
        documentation_lines = f"documentation_impact: {documentation_impact}\n"
        if documentation_targets:
            documentation_lines += "documentation_targets:\n" + "\n".join(
                f"  - {value}" for value in documentation_targets
            ) + "\n"
        documentation_lines += f"documentation_reason: {documentation_reason}\n"
    evidence_digest_line = (
        f"evidence_sha256: {evidence_sha256}\n" if evidence_sha256 is not None else ""
    )
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
        f"{documentation_lines}"
        f"{evidence_digest_line}"
        f"{history_lines}"
        "---\n\n"
        f"# {task_id}\n\n"
        "Deterministic compressed record. The original active spec remains in Git history.\n\n"
        "## Goal\n\n"
        f"{goal}\n\n"
        "## Acceptance criteria\n\n"
        f"{acceptance_criteria}\n\n"
        "## Result\n\n"
        "Verified and closed by the harness close command.\n\n"
        "## Evidence\n\n"
        f"[{task_id}.json](../../verification/evidence/{task_id}.json)\n\n"
        + (
            f"SHA-256: `{evidence_sha256}`\n\n"
            if evidence_sha256 is not None
            else ""
        )
        + f"Closed at {datetime.now(timezone.utc).isoformat()}.\n"
    )
    from .run_store import atomic_write
    atomic_write(archive, content.encode("utf-8"))
    source.unlink()
    return archive, source_text


def restore_spec(task_id: str, source_text: str, archive: Path | None) -> None:
    source = active_spec(task_id)
    source.parent.mkdir(parents=True, exist_ok=True)
    from .run_store import atomic_write
    atomic_write(source, source_text.encode("utf-8"))
    if archive is not None and archive.exists():
        archive.unlink()
