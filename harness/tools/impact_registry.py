"""Cheap ownership inventory validation. Reads Git paths, never imports product code."""

from __future__ import annotations

import fnmatch
import subprocess

from .impact import read_json, safe_path
from .module_verification import case_index, load_module_contract


def owners(path, units):
    return [
        name
        for name, unit in units.items()
        if any(
            path == pattern or fnmatch.fnmatchcase(path, pattern)
            for pattern in unit["paths"]
        )
    ]


def audit(root, *, paths=None):
    registry = read_json(root / "harness/verification/impact/ownership.json")
    units = registry.get("units", {})
    indexed = case_index(load_module_contract(root))
    errors = []
    for name, unit in units.items():
        for pattern in unit.get("paths", []):
            safe_path(pattern)
            if not any(c in pattern for c in "*?") and not (root / pattern).is_file():
                errors.append(f"{name}: stale ownership path {pattern}")
        if not unit.get("cases") or any(c not in indexed for c in unit["cases"]):
            errors.append(f"{name}: missing/unresolved cases")
        if any(dep not in units for dep in unit.get("dependents", [])):
            errors.append(f"{name}: unresolved consumer")
    if paths is None:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            capture_output=True,
            check=True,
        )
        paths = result.stdout.decode("utf-8").split("\0")
    governed = [
        p
        for p in paths
        if p
        and any(
            fnmatch.fnmatchcase(p, pattern) for pattern in registry.get("coverage", [])
        )
    ]
    for path in sorted(set(governed)):
        matches = owners(path, units)
        if len(matches) != 1:
            errors.append(
                f"impact gap: {path}: "
                + (
                    "ambiguous " + ", ".join(matches)
                    if matches
                    else "missing ownership"
                )
            )
    return {"units": len(units), "paths": len(set(governed)), "errors": errors}
