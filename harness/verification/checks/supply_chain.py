from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import tomllib

ACTION_REF = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_./-]+)?@[0-9a-f]{40}$")
USES_LINE = re.compile(r"^\s*(?:-\s+)?uses:\s*([^\s#]+)")
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
MAX_FAILURES = 20


def _workflow_failures(path: Path, relative: str) -> list[str]:
    text = path.read_text(encoding="utf-8")
    failures: list[str] = []

    if re.search(r"(?m)^\s*pull_request_target:\s*$", text):
        failures.append(f"{relative}: pull_request_target is forbidden")

    permission_lines = [
        line.rstrip()
        for line in text.splitlines()
        if re.match(r"^\s*permissions:\s*", line)
    ]
    if permission_lines != ["permissions:"] or not re.search(
        r"(?m)^permissions:\s*\n  contents: read\s*$",
        text,
    ):
        failures.append(f"{relative}: permissions must be exactly top-level contents: read")

    for line_number, line in enumerate(text.splitlines(), start=1):
        match = USES_LINE.match(line)
        if not match:
            continue
        reference = match.group(1)
        if reference.startswith("./"):
            continue
        if reference.startswith("docker://"):
            if not re.search(r"@sha256:[0-9a-f]{64}$", reference):
                failures.append(
                    f"{relative}:{line_number}: container action must pin sha256"
                )
            continue
        if not ACTION_REF.fullmatch(reference):
            failures.append(
                f"{relative}:{line_number}: action must use a full 40-character commit SHA"
            )

    if re.search(r"(?i)\bnpm\s+install\b", text):
        failures.append(f"{relative}: npm install is forbidden; use npm ci")
    if "npm ci" not in text:
        failures.append(f"{relative}: missing npm ci")
    if re.search(r"(?i)(?:python\s+-m\s+)?pip\s+install\b", text):
        failures.append(f"{relative}: pip install is forbidden in CI; use the project lock")

    uv_sync_lines = [line.strip() for line in text.splitlines() if "uv sync" in line]
    if not uv_sync_lines:
        failures.append(f"{relative}: missing uv sync --locked")
    for line in uv_sync_lines:
        if "--locked" not in line:
            failures.append(f"{relative}: uv sync must use --locked")

    return failures


def _package_lock_failures(path: Path, relative: str) -> list[str]:
    if not path.is_file():
        return [f"{relative}: required lockfile is missing"]
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"{relative}: invalid JSON lockfile: {error}"]

    failures: list[str] = []
    if document.get("lockfileVersion") != 3:
        failures.append(f"{relative}: lockfileVersion must be 3")
    packages = document.get("packages")
    if not isinstance(packages, dict) or not packages:
        failures.append(f"{relative}: packages map must not be empty")
        return failures
    for name, record in packages.items():
        if (
            not isinstance(record, dict)
            or "resolved" not in record
            or record.get("link") is True
        ):
            continue
        integrity = record.get("integrity")
        if not isinstance(integrity, str) or not integrity.startswith("sha512-"):
            failures.append(f"{relative}: {name or '<root>'} lacks sha512 integrity")
    return failures


def _uv_lock_failures(path: Path, relative: str) -> list[str]:
    if not path.is_file():
        return [f"{relative}: required lockfile is missing"]
    try:
        with path.open("rb") as handle:
            document = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        return [f"{relative}: invalid TOML lockfile: {error}"]

    failures: list[str] = []
    if document.get("version") != 1 or document.get("revision") != 3:
        failures.append(f"{relative}: expected uv lock version 1 revision 3")
    packages = document.get("package")
    if not isinstance(packages, list) or not packages:
        failures.append(f"{relative}: package list must not be empty")
        return failures
    for package in packages:
        if not isinstance(package, dict):
            failures.append(f"{relative}: package entries must be tables")
            continue
        source = package.get("source")
        if not isinstance(source, dict) or "registry" not in source:
            continue
        name = str(package.get("name", "<unknown>"))
        if source.get("registry") != "https://pypi.org/simple":
            failures.append(f"{relative}: {name} uses a non-PyPI registry")
        artifacts = [package.get("sdist"), *(package.get("wheels") or [])]
        artifacts = [item for item in artifacts if isinstance(item, dict)]
        if not artifacts:
            failures.append(f"{relative}: {name} has no hashed distribution artifact")
            continue
        if any(not SHA256.fullmatch(str(item.get("hash", ""))) for item in artifacts):
            failures.append(f"{relative}: {name} has an invalid distribution hash")
    return failures


def run(context: dict[str, Any]) -> dict[str, Any]:
    root: Path = context["project_root"]
    workflows_root = root / ".github" / "workflows"
    workflows = sorted(
        [*workflows_root.glob("*.yml"), *workflows_root.glob("*.yaml")],
        key=lambda item: item.as_posix(),
    )
    failures: list[str] = []
    if not workflows:
        failures.append(".github/workflows: at least one workflow is required")
    for path in workflows:
        failures.extend(_workflow_failures(path, path.relative_to(root).as_posix()))

    failures.extend(_package_lock_failures(root / "package-lock.json", "package-lock.json"))
    failures.extend(_uv_lock_failures(root / "apps" / "api" / "uv.lock", "apps/api/uv.lock"))
    if failures:
        omitted = len(failures) - MAX_FAILURES
        details = failures[:MAX_FAILURES]
        if omitted > 0:
            details.append(f"{omitted} additional supply-chain failures omitted")
        return {"name": "supply-chain", "passed": False, "details": details}

    return {
        "name": "supply-chain",
        "passed": True,
        "details": [
            f"{len(workflows)} workflows use immutable actions, least privilege, and locked installs; 2 lockfiles are structurally valid"
        ],
    }
