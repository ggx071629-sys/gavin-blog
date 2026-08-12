from __future__ import annotations

from typing import Any

from . import product_verification, summarizer, validator
from .metadata import parse_front_matter


def task_record(task_id: str) -> dict[str, Any]:
    summarizer.validate_task_id(task_id)
    active = summarizer.active_spec(task_id)
    if active.is_file():
        metadata, _ = parse_front_matter(active)
        persisted = str(metadata.get("status", ""))
        profile = str(metadata.get("verification_profile", "")) or None
        if persisted == "frozen":
            return {
                "task_id": task_id,
                "state": "frozen",
                "verification_profile": profile,
                "evidence": "not-evaluated",
                "blockers": [],
            }
        errors = product_verification.validate_evidence(
            task_id,
            validator.evidence_path(task_id),
        )
        return {
            "task_id": task_id,
            "state": "verified" if not errors else "active",
            "verification_profile": profile,
            "evidence": "valid" if not errors else "invalid",
            "blockers": errors,
        }
    if summarizer.archive_spec(task_id).is_file():
        return {
            "task_id": task_id,
            "state": "compressed",
            "verification_profile": None,
            "evidence": "archived",
            "blockers": [],
        }
    return {
        "task_id": task_id,
        "state": "missing",
        "verification_profile": None,
        "evidence": "missing",
        "blockers": ["task was not found in active specs or compressed archives"],
    }


def current_task_records() -> list[dict[str, Any]]:
    return [task_record(path.stem) for path in summarizer.active_specs()]
