"""Canonical restricted runners. Never invoke an application-wide npm test script."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from collections import defaultdict
from contextlib import ExitStack

from . import impact
from . import test_collection as tc
from .config import project_root
from .product_verification import _run_supervised_command
from .result_reporting import parse_test_counts

PYTEST_RUNNER = r"""
import json, sys, pytest
class Proof:
    def __init__(self):
        self.collected = 0
        self.executed = 0
        self.bad = False
    def pytest_collection_finish(self, session):
        self.collected = len(session.items)
        if len({item.nodeid for item in session.items}) != self.collected: self.bad = True
    def pytest_runtest_logreport(self, report):
        if report.when == 'call': self.executed += 1
        if report.skipped or report.failed: self.bad = True
p = Proof()
code = pytest.main(['-q', '-o', 'addopts=', *sys.argv[1:]], plugins=[p])
print('HARNESS_SELECTION ' + json.dumps({'collected': p.collected, 'executed': p.executed}))
raise SystemExit(code or (1 if p.bad or not p.collected or p.executed != p.collected or p.collected != len(sys.argv) - 1 else 0))
"""


def batches(refs):
    """One exact pytest invocation; JS names are scoped per file to avoid cross-products."""
    grouped = defaultdict(list)
    for ref in refs:
        impact.safe_path(ref["path"])
        if not ref["name"] or "\0" in ref["name"]:
            raise ValueError("invalid exact test name")
        key = (ref["kind"], "" if ref["kind"] == "pytest" else ref["path"])
        grouped[key].append(ref)
    return list(grouped.values())


def playwright_config(path):
    for directory, config, project in (
        ("tests/e2e/", "playwright.config.ts", "chromium"),
        ("tests/e2e-assistant/", "playwright.assistant.config.ts", "chromium"),
        ("tests/quality/", "playwright.quality.config.ts", "quality-chromium"),
        ("tests/failure/", "playwright.failure.config.ts", ""),
    ):
        if path.startswith("apps/web/" + directory):
            return config, project
    raise ValueError(f"impact gap: no Playwright config/project binding for {path}")


def command_for(refs, root):
    kind = refs[0]["kind"]
    if kind == "pytest":
        api = all(r["path"].startswith("apps/api/") for r in refs)
        cwd = root / "apps/api" if api else root
        return [
            str(tc._api_python(root)),
            "-c",
            PYTEST_RUNNER,
            *[
                (r["path"].removeprefix("apps/api/") if api else r["path"])
                + "::"
                + r["name"]
                for r in refs
            ],
        ], cwd
    npm = shutil.which("npm.cmd" if sys.platform == "win32" else "npm")
    if not npm:
        raise ValueError("selected JavaScript tests require npm")
    relative = refs[0]["path"].removeprefix("apps/web/")
    # Full title may include describe prefixes; the literal leaf title must match at the end.
    pattern = "(?:^| > | )(?:(" + "|".join(re.escape(r["name"]) for r in refs) + "))$"
    if kind == "vitest":
        return [
            npm,
            "exec",
            "--",
            "vitest",
            "run",
            relative,
            "--config",
            "vitest.config.ts",
            "-t",
            pattern,
        ], root / "apps/web"
    if kind == "playwright":
        config, project = playwright_config(refs[0]["path"])
        return [
            npm,
            "exec",
            "--",
            "playwright",
            "test",
            re.escape(relative),
            "--config",
            config,
            *(["--project", project] if project else []),
            "--grep",
            pattern,
            "--retries=0",
        ], root / "apps/web"
    raise ValueError(f"unsupported selected runner: {kind}")


def run_selected(refs, root=None):
    root = root or project_root()
    with ExitStack() as cleanup:
        env = {}
        if any(r['kind'] == 'playwright' for r in refs):
            runtime = root / '.run'
            runtime.mkdir(exist_ok=True)
            env['GAVIN_E2E_RUN_ROOT'] = cleanup.enter_context(
                tempfile.TemporaryDirectory(prefix='selected-e2e-', dir=runtime))
        return _run_selected(refs, root, env)


def _run_selected(refs, root, env):
    root = root or project_root()
    if not refs:
        raise ValueError("empty test selection is forbidden")
    prepared_web = False
    for group in batches(refs):
        command, cwd = command_for(group, root)
        if group[0]["kind"] == "vitest" and not prepared_web:
            prepare = _run_supervised_command(
                [command[0], "exec", "--", "nuxt", "prepare"],
                cwd=cwd,
                timeout_seconds=120,
            )
            if prepare.returncode:
                return prepare.returncode
            prepared_web = True
        if group[0]["kind"] in {"vitest", "playwright"}:
            # Verify only the selected file/name/project before running. Missing refs fail closed.
            if group[0]["kind"] == "vitest":
                rows = tc._collect_vitest(
                    root,
                    selectors=[
                        group[0]["path"].removeprefix("apps/web/"),
                        "-t",
                        command[-1],
                    ],
                    prepare=False,
                )
            else:
                config, project = playwright_config(group[0]["path"])
                rows = tc._collect_playwright(
                    root,
                    config,
                    group[0]["gate"],
                    selectors=[
                        re.escape(group[0]["path"].removeprefix("apps/web/")),
                        *(["--project", project] if project else []),
                        "--grep",
                        command[-2],
                    ],
                )
            for ref in group:
                matches = [
                    row
                    for row in rows
                    if row["path"] == ref["path"] and row["name"] == ref["name"]
                ]
                if len(matches) != 1 or matches[0]["disabled"]:
                    raise ValueError(
                        f"selected collection missing, duplicate or disabled: {ref['path']}::{ref['name']}"
                    )
            if len(rows) != len(group):
                raise ValueError("selected collection expanded beyond exact refs")
        if (
            group[0]["kind"] == "playwright"
            and playwright_config(group[0]["path"])[0] == "playwright.quality.config.ts"
        ):
            # This config previews a production build. Build only for selected quality cases.
            built = _run_supervised_command(
                [command[0], "run", "build"], cwd=cwd, timeout_seconds=600
            )
            if built.returncode:
                return built.returncode
        result = _run_supervised_command(
            command,
            cwd=cwd,
            timeout_seconds=600,
            env={"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
            if group[0]["kind"] == "pytest"
            else env,
        )
        if result.returncode:
            return result.returncode
        if group[0]["kind"] != "pytest":
            counts = parse_test_counts(result.stdout, result.stderr)
            if not counts or counts["passed"] != len(group) or counts["failed"]:
                raise ValueError(
                    "selected execution incomplete, skipped or expanded beyond collected refs"
                )
            print(
                "HARNESS_SELECTION "
                + json.dumps({"collected": len(rows), "executed": counts["passed"]})
            )
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--gate", required=True)
    args = parser.parse_args()
    plan = impact.build_plan(args.task)
    refs = [r for r in plan["test_refs"] if r["gate"] == args.gate]
    return run_selected(refs)


if __name__ == "__main__":
    raise SystemExit(main())
