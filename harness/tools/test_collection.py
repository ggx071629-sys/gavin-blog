from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class TestCollectionError(ValueError):
    pass


GATE_BINDINGS: dict[str, tuple[str, tuple[str, ...]]] = {
    "api-tests": ("apps/api", ("{api_python}", "-m", "pytest")),
    "harness-tests": (
        ".",
        ("{api_python}", "-m", "pytest", "harness/verification/tests"),
    ),
    "web-quality": (".", ("npm", "run", "quality:web")),
    "e2e": (".", ("npm", "run", "test:e2e")),
}

PACKAGE_SCRIPT_BINDINGS: dict[str, dict[str, str]] = {
    "package.json": {
        "quality:web": (
            "npm --workspace @gavin/web run typecheck && "
            "npm --workspace @gavin/web run lint && "
            "npm --workspace @gavin/web run test && "
            "npm --workspace @gavin/web run build && "
            "npm --workspace @gavin/web run test:quality && "
            "npm --workspace @gavin/web run test:failure-states"
        ),
        "test:e2e": "npm --workspace @gavin/web run test:e2e",
    },
    "apps/web/package.json": {
        "test": "vitest run",
        "test:e2e": "node scripts/run-playwright-e2e.mjs",
        "test:quality": "playwright test --config playwright.quality.config.ts",
        "test:failure-states": (
            "playwright test --config playwright.failure.config.ts"
        ),
    },
}
FILE_SHA256_BINDINGS = {
    "apps/web/scripts/run-playwright-e2e.mjs": (
        "a1ade1a47a512853596f76e0f3685c11ef7af80c0b15e941097dd1e5c059bf2d"
    ),
}

PYTEST_PAYLOAD_PREFIX = "HARNESS_PYTEST_COLLECTION "
_COLLECTION_CACHE: dict[
    tuple[str, tuple[tuple[str, int, int], ...]],
    dict[tuple[str, str, str, str], list[dict[str, Any]]],
] = {}
_PYTEST_COLLECTOR = r'''
import json
from pathlib import Path
import pytest
import sys

PREFIX = "HARNESS_PYTEST_COLLECTION "

class Collector:
    def pytest_collection_finish(self, session):
        rows = []
        for item in session.items:
            source = Path(str(item.path)).resolve()
            markers = sorted({
                marker.name for marker in item.iter_markers()
                if marker.name in {"skip", "skipif", "xfail"}
            })
            rows.append({
                "path": source.as_posix(),
                "name": item.nodeid.split("::", 1)[1],
                "nodeid": item.nodeid,
                "disabled": markers,
            })
        print(PREFIX + json.dumps(rows, sort_keys=True))

raise SystemExit(pytest.main(["--collect-only", "-q", "-o", "addopts=", *sys.argv[1:]], plugins=[Collector()]))
'''


def _json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TestCollectionError(f"cannot read collector binding {path}: {error}") from error
    if not isinstance(payload, dict):
        raise TestCollectionError(f"collector binding must be an object: {path}")
    return payload


def validate_gate_bindings(project_root: Path, config: Mapping[str, Any]) -> None:
    verification = config.get("verification")
    gates = verification.get("gates") if isinstance(verification, Mapping) else None
    if not isinstance(gates, Mapping):
        raise TestCollectionError("verification.gates must be an object")
    defects: list[str] = []
    for gate, (expected_cwd, expected_command) in sorted(GATE_BINDINGS.items()):
        definition = gates.get(gate)
        if not isinstance(definition, Mapping):
            defects.append(f"collector owner gate is missing: {gate}")
            continue
        raw_command = definition.get("command")
        actual_command = (
            tuple(raw_command)
            if isinstance(raw_command, list)
            and all(isinstance(value, str) for value in raw_command)
            else ()
        )
        if definition.get("cwd") != expected_cwd or actual_command != expected_command:
            defects.append(f"collector owner gate command drifted: {gate}")

    for relative, expected_scripts in sorted(PACKAGE_SCRIPT_BINDINGS.items()):
        payload = _json_file(project_root / relative)
        scripts = payload.get("scripts")
        if not isinstance(scripts, Mapping):
            defects.append(f"collector binding has no scripts object: {relative}")
            continue
        for name, expected in sorted(expected_scripts.items()):
            if scripts.get(name) != expected:
                defects.append(f"collector owner script drifted: {relative}#{name}")
    for relative, expected_digest in sorted(FILE_SHA256_BINDINGS.items()):
        path = project_root / relative
        try:
            actual_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            actual_digest = ""
        if actual_digest != expected_digest:
            defects.append(f"collector owner runner drifted: {relative}")
    if defects:
        raise TestCollectionError("; ".join(defects))


def _api_python(project_root: Path) -> Path:
    relative = (
        Path("apps/api/.venv/Scripts/python.exe")
        if os.name == "nt"
        else Path("apps/api/.venv/bin/python")
    )
    executable = (project_root / relative).resolve()
    if not executable.is_file():
        raise TestCollectionError("API virtual environment Python is missing")
    return executable


def _run(command: list[str], cwd: Path) -> str:
    from .verification_inputs import controlled_environment
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=120,
            env=controlled_environment(),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise TestCollectionError(f"test collector failed to start: {error}") from error
    from .run_artifacts import LOG_LIMIT, log_path
    diagnostic = log_path.get()
    if diagnostic is not None:
        diagnostic.parent.mkdir(parents=True, exist_ok=True)
        existing = diagnostic.stat().st_size if diagnostic.exists() else 0
        with diagnostic.open("ab") as handle:
            handle.write((result.stdout + result.stderr).encode("utf-8")[:max(0, LOG_LIMIT - existing)])
    if result.returncode != 0:
        from .result_reporting import failure_summary
        summary = failure_summary(result.stdout, result.stderr)
        raise TestCollectionError(f"test collector failed: {summary}")
    return result.stdout


def _npm() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def _project_path(project_root: Path, value: str) -> str:
    path = Path(value).resolve()
    try:
        return path.relative_to(project_root.resolve()).as_posix()
    except ValueError as error:
        raise TestCollectionError(f"collector returned path outside project: {value}") from error


def _collect_pytest(project_root: Path, target: str | list[str], gate: str) -> list[dict[str, Any]]:
    stdout = _run(
        [str(_api_python(project_root)), "-c", _PYTEST_COLLECTOR, *([target] if isinstance(target, str) else target)],
        project_root,
    )
    lines = [
        line[len(PYTEST_PAYLOAD_PREFIX) :]
        for line in stdout.splitlines()
        if line.startswith(PYTEST_PAYLOAD_PREFIX)
    ]
    if len(lines) != 1:
        raise TestCollectionError(f"pytest collector emitted invalid payload for {gate}")
    try:
        payload = json.loads(lines[0])
    except json.JSONDecodeError as error:
        raise TestCollectionError(f"pytest collector emitted malformed JSON for {gate}") from error
    if not isinstance(payload, list):
        raise TestCollectionError(f"pytest collector payload must be an array for {gate}")
    rows: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise TestCollectionError(f"pytest collector item is invalid for {gate}")
        rows.append(
            {
                "kind": "pytest",
                "gate": gate,
                "path": _project_path(project_root, str(item.get("path", ""))),
                "name": str(item.get("name", "")),
                "node": str(item.get("nodeid", "")),
                "disabled": list(item.get("disabled", [])),
            }
        )
    return rows


def _walk_playwright_suites(suites, root_dir, project_root, gate, *, config="", titles=(), depth=0):
    rows = []
    for suite in suites:
        # JSON's outer file suite is not part of the user describe hierarchy.
        parents = (*titles, suite["title"]) if depth else titles
        for spec in suite.get("specs", []):
            source = Path(spec["file"])
            if not source.is_absolute():
                source = root_dir / source
            for test in spec.get("tests", []):
                disabled = [a["type"] for a in test.get("annotations", [])
                            if a.get("type") in {"skip", "fixme", "todo", "fail"}]
                if test.get("expectedStatus") != "passed":
                    disabled.append(test.get("expectedStatus", "unknown"))
                rows.append({"kind": "playwright", "gate": gate,
                             "path": _project_path(project_root, str(source)),
                             "name": spec["title"], "title_path": [*parents, spec["title"]],
                             "config": config, "project": test.get("projectName", ""),
                             "selection_path": source.relative_to(root_dir).as_posix(),
                             "node": spec.get("id", ""), "disabled": disabled,
                             "results": test.get("results", []), "status": test.get("status")})
        rows.extend(_walk_playwright_suites(suite.get("suites", []), root_dir, project_root, gate,
                                          config=config, titles=parents, depth=depth + 1))
    return rows


def _collect_playwright(
    project_root: Path,
    config_name: str,
    gate: str,
    *, selectors: list[str] | None = None,
) -> list[dict[str, Any]]:
    web_root = project_root / "apps/web"
    stdout = _run(
        [
            _npm(),
            "exec",
            "playwright",
            "test",
            "--",
            "--config",
            config_name,
            "--list",
            "--reporter=json",
            *(selectors or []),
        ],
        web_root,
    )
    try:
        payload = json.loads(stdout)
        root_dir = Path(str(payload["config"]["rootDir"]))
        suites = payload["suites"]
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise TestCollectionError(
            f"Playwright collector emitted invalid JSON for {config_name}"
        ) from error
    if not isinstance(suites, list):
        raise TestCollectionError(f"Playwright suites must be an array for {config_name}")
    return _walk_playwright_suites(suites, root_dir, project_root, gate, config=config_name)


def _collect_vitest(project_root: Path, *, selectors: list[str] | None = None, prepare: bool = True) -> list[dict[str, Any]]:
    web_root = project_root / "apps/web"
    if prepare:
        _run([_npm(), "exec", "nuxt", "--", "prepare"], web_root)
    stdout = _run(
        # --json accepts an optional output path. Keep it last so a positional
        # test selector can never be interpreted as a file to overwrite.
        [_npm(), "exec", "--", "vitest", "list", "--config", "vitest.config.ts", *(selectors or []), "--json"],
        web_root,
    )
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise TestCollectionError("Vitest collector emitted malformed JSON") from error
    if not isinstance(payload, list):
        raise TestCollectionError("Vitest collector payload must be an array")
    rows: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise TestCollectionError("Vitest collector item must be an object")
        relative_path = _project_path(project_root, str(item.get("file", "")))
        name = str(item.get("name", "")).split(" > ")[-1]
        try:
            source = (project_root / relative_path).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise TestCollectionError(f"cannot inspect Vitest definition: {relative_path}") from error
        disabled = []
        title = re.escape(name)
        if re.search(
            rf"(?:test|it)(?:\.[A-Za-z]+)*\.(?:skip|todo|fixme)(?:\.[A-Za-z]+)*\s*\(\s*(['\"`]){title}\1",
            source,
        ):
            disabled.append("skip/todo/fixme")
        rows.append(
            {
                "kind": "vitest",
                "gate": "web-quality",
                "path": relative_path,
                "name": name,
                "node": str(item.get("name", "")),
                "config": "vitest.config.ts", "project": item.get("projectName", ""),
                "title_path": str(item.get("name", "")).split(" > "),
                "disabled": disabled,
            }
        )
    return rows


def collect_test_index(
    project_root: Path,
    config: Mapping[str, Any],
) -> dict[tuple[str, str, str, str], list[dict[str, Any]]]:
    root = project_root.resolve()
    validate_gate_bindings(root, config)
    watched = [
        root / "package.json",
        root / "package-lock.json",
        root / "apps/web/package.json",
        root / "apps/web/nuxt.config.ts",
        root / "apps/web/tsconfig.json",
        root / "apps/web/vitest.config.ts",
        root / "apps/web/playwright.config.ts",
        root / "apps/web/playwright.assistant.config.ts",
        root / "apps/web/playwright.quality.config.ts",
        root / "apps/web/playwright.failure.config.ts",
        *sorted((root / "apps/api/tests").glob("test_*.py")),
        *sorted((root / "harness/verification/tests").glob("test_*.py")),
        *sorted((root / "apps/web/tests").rglob("*.test.ts")),
        *sorted((root / "apps/web/tests").rglob("*.spec.ts")),
    ]
    signature = tuple(
        (
            path.relative_to(root).as_posix(),
            path.stat().st_mtime_ns,
            path.stat().st_size,
        )
        for path in watched
        if path.is_file()
    )
    cache_key = (str(root), signature)
    cached = _COLLECTION_CACHE.get(cache_key)
    if cached is not None:
        return cached
    rows = [
        *_collect_pytest(root, "apps/api/tests", "api-tests"),
        *_collect_pytest(root, "harness/verification/tests", "harness-tests"),
        *_collect_vitest(root),
        *_collect_playwright(root, "playwright.config.ts", "e2e"),
        *_collect_playwright(root, "playwright.assistant.config.ts", "e2e"),
        *_collect_playwright(root, "playwright.quality.config.ts", "web-quality"),
        *_collect_playwright(root, "playwright.failure.config.ts", "web-quality"),
    ]
    index: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["kind"], row["path"], row["name"], row["gate"])
        index.setdefault(key, []).append(row)
    _COLLECTION_CACHE.clear()
    _COLLECTION_CACHE[cache_key] = index
    return index
