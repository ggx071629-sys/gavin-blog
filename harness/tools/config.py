from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


def harness_root() -> Path:
    return Path(__file__).resolve().parent.parent


def project_root() -> Path:
    return harness_root().parent


def load_config() -> dict[str, Any]:
    config_path = harness_root() / "config.toml"
    with config_path.open("rb") as handle:
        return tomllib.load(handle)


def resolve_harness_path(value: str) -> Path:
    return (harness_root() / value).resolve()

