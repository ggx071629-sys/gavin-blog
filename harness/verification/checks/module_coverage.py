from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    from tools.module_verification import (
        case_index,
        contract_digest,
        validate_module_contract,
    )
except ModuleNotFoundError:  # pragma: no cover - repository-root test imports
    from harness.tools.module_verification import (
        case_index,
        contract_digest,
        validate_module_contract,
    )


MAX_FAILURE_DETAILS = 12


def _compact(errors: list[str]) -> list[str]:
    sanitized = [
        re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f]", " ", str(error))).strip()[:280]
        for error in errors
    ]
    if len(sanitized) <= MAX_FAILURE_DETAILS:
        return sanitized
    omitted = len(sanitized) - MAX_FAILURE_DETAILS
    return [
        *sanitized[:MAX_FAILURE_DETAILS],
        f"... {omitted} additional defects omitted",
    ]


def run(context: dict[str, Any]) -> dict[str, Any]:
    project_root: Path = context["project_root"]
    harness_root: Path = context["harness_root"]
    payload, errors = validate_module_contract(
        project_root,
        harness_root,
        context["config"],
        structure_only=bool(context["config"].get("verification", {}).get("impact")),
    )
    ownership = harness_root / 'verification/impact/ownership.json'
    if ownership.is_file():
        import json
        if json.loads(ownership.read_bytes()).get('coverage'):
            try:
                from tools.impact_registry import audit
            except ModuleNotFoundError:
                from harness.tools.impact_registry import audit
            errors.extend(audit(project_root)['errors'])
    if errors:
        return {
            "name": "module-coverage",
            "passed": False,
            "details": _compact(errors),
        }

    indexed_cases = case_index(payload)
    expectation_count = sum(
        len(case["expectations"]) for case in indexed_cases.values()
    )
    reference_count = sum(len(case["test_refs"]) for case in indexed_cases.values())
    digest = contract_digest(payload)
    return {
        "name": "module-coverage",
        "passed": True,
        "details": [
            (
                f"{len(payload['modules'])} modules, {len(indexed_cases)} cases, "
                f"{expectation_count} expectations, "
                f"{reference_count} exact test references; "
                f"contract sha256 {digest[:12]}"
            )
        ],
    }
