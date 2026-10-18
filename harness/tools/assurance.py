from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import harness_root, load_config

STRUCTURAL_CHECKS = {
    "gate-subsumption",
    "history-integrity",
    "indexes",
    "l0",
    "links",
    "metadata",
    "structure",
    "supply-chain",
}
LEVELS = (
    "v2-product-verified",
    "v2-transitional-product-reported",
    "legacy-product-reported",
    "legacy-structure-only",
    "invalid",
)


def _read(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _v2_valid(payload: dict[str, Any]) -> bool:
    if payload.get("status") != "passed":
        return False
    execution = payload.get("execution")
    if not isinstance(execution, dict):
        return False
    if execution.get("mode") != "git-worktree" or execution.get("cleanup_status") != "passed":
        return False
    checks = payload.get("checks")
    return (
        isinstance(checks, list)
        and bool(checks)
        and all(isinstance(check, dict) and check.get("status") == "passed" for check in checks)
        and any(isinstance(check, dict) and check.get("kind") == "product" for check in checks)
    )


def _legacy_product_reported(
    payload: dict[str, Any], auxiliary_payloads: dict[str, dict[str, Any] | None]
) -> bool:
    application = auxiliary_payloads.get("application")
    if isinstance(application, dict) and application.get("status") == "passed":
        return True
    checks = payload.get("checks")
    if not isinstance(checks, list):
        return False
    names = {
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict) and check.get("name")
    }
    return bool(names - STRUCTURAL_CHECKS)


def _v2_transitional_product_reported(payload: dict[str, Any]) -> bool:
    if payload.get("status") != "passed" or payload.get("execution") is not None:
        return False
    checks = payload.get("checks")
    return (
        isinstance(checks, list)
        and bool(checks)
        and all(isinstance(check, dict) and check.get("status") == "passed" for check in checks)
        and any(isinstance(check, dict) and check.get("kind") == "product" for check in checks)
    )


def inventory() -> dict[str, Any]:
    config = load_config()
    root = harness_root() / str(config["verification"]["evidence"])
    main_files = sorted(path for path in root.glob("*.json") if "." not in path.stem)
    records: list[dict[str, Any]] = []
    counts = {level: 0 for level in LEVELS}
    auxiliary_total = 0
    for path in main_files:
        task_id = path.stem
        payload = _read(path)
        auxiliary: dict[str, str] = {}
        auxiliary_payloads: dict[str, dict[str, Any] | None] = {}
        for kind in ("application", "benchmark"):
            candidate = root / f"{task_id}.{kind}.json"
            if candidate.is_file():
                auxiliary[kind] = candidate.name
                auxiliary_payloads[kind] = _read(candidate)
                auxiliary_total += 1

        schema = payload.get("schema_version") if payload else None
        status = payload.get("status") if payload else None
        if payload is None or status != "passed":
            level = "invalid"
        elif schema == 2:
            if _v2_valid(payload):
                level = "v2-product-verified"
            elif _v2_transitional_product_reported(payload):
                level = "v2-transitional-product-reported"
            else:
                level = "invalid"
        elif schema == 1:
            level = (
                "legacy-product-reported"
                if _legacy_product_reported(payload, auxiliary_payloads)
                else "legacy-structure-only"
            )
        else:
            level = "invalid"
        counts[level] += 1
        records.append(
            {
                "task_id": task_id,
                "schema_version": schema,
                "status": status,
                "assurance": level,
                "evidence": path.name,
                "auxiliary": auxiliary,
            }
        )
    return {
        "schema_version": 1,
        "tasks": len(records),
        "auxiliary_files": auxiliary_total,
        "assurance": counts,
        "records": records,
    }
