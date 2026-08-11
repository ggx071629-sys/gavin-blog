from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import harness_root, load_config
from .summarizer import validate_task_id


def emit_event(
    event_type: str,
    task_id: str,
    reason: str,
    source: str,
    *,
    create_proposal: bool = True,
) -> tuple[Path, Path | None]:
    config = load_config()
    validate_task_id(task_id)
    allowed = set(config["evolution"]["allowed_events"])
    if event_type not in allowed:
        raise ValueError(f"event type is not allowed: {event_type}")
    if source == "telemetry":
        raise ValueError("telemetry cannot directly trigger evolution")

    token = event_type.replace(".", "-")
    events_dir = harness_root() / str(config["evolution"]["events"])
    proposals_dir = harness_root() / str(config["evolution"]["proposals"])
    events_dir.mkdir(parents=True, exist_ok=True)
    proposals_dir.mkdir(parents=True, exist_ok=True)
    event_path = events_dir / f"{task_id}--{token}.json"
    proposal_path = proposals_dir / f"{task_id}--{token}.md"
    if event_path.exists() or proposal_path.exists():
        raise FileExistsError("event or proposal already exists")

    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "schema_version": 1,
        "event_type": event_type,
        "task_id": task_id,
        "created_at": now,
        "source": source,
        "reason": reason,
        "may_modify_agents_md": False,
    }
    event_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if create_proposal:
        proposal_path.write_text(
            "---\n"
            f"id: evolution-{task_id}-{token}\n"
            "level: L1\n"
            f"summary: Review evolution event {event_type} for {task_id}\n"
            "load_when:\n"
            "  - process-evolution\n"
            f"  - task:{task_id}\n"
            f"task_id: {task_id}\n"
            "status: proposed\n"
            "---\n\n"
            f"# Evolution proposal: {event_type}\n\n"
            f"Reason: {reason}\n\n"
            "## Allowed outcome\n\n"
            "After human confirmation, update only relevant L1/L2 sources, templates, workflows, indexes, or checks.\n\n"
            "## Forbidden outcome\n\n"
            "This proposal must not modify `AGENTS.md` automatically.\n",
            encoding="utf-8",
            newline="\n",
        )
        return event_path, proposal_path
    return event_path, None
