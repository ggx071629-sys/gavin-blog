"""Pure committed-snapshot preflight; no collectors, dependency links or builds."""

from __future__ import annotations

import json
import sys

from . import impact, validator
from .run_store import digest


def inspect(task_id=None):
    checks = validator.run_checks()
    plan_digest = None
    if task_id and validator.passed(checks):
        try:
            plan_digest = digest(impact.build_plan(task_id))
        except ValueError as error:
            checks.append(
                {
                    "name": "snapshot-input",
                    "status": "failed",
                    "passed": False,
                    "details": [str(error)],
                    "duration_ms": 0,
                }
            )
    return {"version": 1, "checks": checks, "plan_digest": plan_digest}


if __name__ == "__main__":
    report = inspect(sys.argv[1] if len(sys.argv) > 1 else None)
    print(json.dumps(report, ensure_ascii=True))
    raise SystemExit(0 if validator.passed(report["checks"]) else 1)
