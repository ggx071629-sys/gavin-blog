from __future__ import annotations

from typing import Any


def run(_: dict[str, Any]) -> dict[str, Any]:
    from tools.qualification import validate_repository_manifests

    errors = validate_repository_manifests()
    return {
        "name": "qualification-manifests",
        "passed": not errors,
        "details": errors or ["configured qualification manifests have valid historical bindings"],
    }
