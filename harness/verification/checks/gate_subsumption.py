from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from tools.product_verification import (
        ProductVerificationError,
        configured_subsumption_contracts,
    )
except ModuleNotFoundError:  # pragma: no cover - repository-root test imports
    from harness.tools.product_verification import (
        ProductVerificationError,
        configured_subsumption_contracts,
    )


def run(context: dict[str, Any]) -> dict[str, Any]:
    project_root: Path = context["project_root"]
    try:
        contracts = configured_subsumption_contracts(project_root)
    except (OSError, ProductVerificationError, ValueError) as error:
        return {
            "name": "gate-subsumption",
            "passed": False,
            "details": [str(error)],
        }
    child_count = sum(len(contract["stages"]) for contract in contracts.values())
    return {
        "name": "gate-subsumption",
        "passed": True,
        "details": [
            f"{len(contracts)} subsumption contracts bind {child_count} registered child gates"
        ],
    }
