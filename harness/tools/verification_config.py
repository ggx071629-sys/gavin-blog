from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

TOKEN_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def required_check_names(config: Mapping[str, Any]) -> list[str]:
    verification = config.get("verification")
    raw = verification.get("required_task_checks") if isinstance(verification, Mapping) else None
    if (
        not isinstance(raw, list)
        or not raw
        or not all(
            isinstance(value, str) and TOKEN_PATTERN.fullmatch(value)
            for value in raw
        )
    ):
        raise ValueError(
            "verification.required_task_checks must be a non-empty array of check names"
        )
    values = [str(value) for value in raw]
    if len(values) != len(set(values)):
        raise ValueError(
            "verification.required_task_checks must not contain duplicates"
        )
    return values
