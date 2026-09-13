"""Canonical restricted runners. Never invoke an application-wide npm test script."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
import time
from collections import defaultdict
from contextlib import ExitStack
from pathlib import Path

from . import exact_identity as exact
from . import impact
from . import test_collection as tc
from .config import load_config, project_root
from .execution_contracts import ensure_prerequisites
from .product_verification import _run_supervised_command
from .run_artifacts import log_path

PYTEST_RUNNER = r"""
import json, sys, pytest
from pathlib import Path
class Proof:
    def __init__(self):
        self.collected = []
        self.executed = []
        self.bad = False
    def pytest_collection_finish(self, session):
        self.collected = [item.nodeid for item in session.items]
        if len(set(self.collected)) != len(self.collected): self.bad = True
        def requested(value):
            path, name = value.split('::', 1)
            return str(Path(path).resolve()), name
        actual = {(str(item.path.resolve()), item.nodeid.split('::', 1)[1]) for item in session.items}
        if actual != {requested(v) for v in sys.argv[1:]}: self.bad = True
    def pytest_runtest_logreport(self, report):
        if report.when == 'call': self.executed.append(report.nodeid)
        if report.skipped or report.failed: self.bad = True
p = Proof()
code = pytest.main(['-q', '-o', 'addopts=', *sys.argv[1:]], plugins=[p])
print('HARNESS_SELECTION ' + json.dumps({'collected': len(p.collected), 'executed': len(p.executed)}))
raise SystemExit(code or (1 if p.bad or not p.collected or sorted(p.executed) != sorted(p.collected) or len(p.collected) != len(sys.argv) - 1 else 0))
"""


def batches(refs):
    """One exact pytest invocation; JS names are scoped per file to avoid cross-products."""
    grouped = defaultdict(list)
    for ref in refs:
        impact.safe_path(ref["path"])
        if not ref["name"] or "\0" in ref["name"]:
            raise ValueError("invalid exact test name")
        key = (
            ref["kind"],
            "" if ref["kind"] == "pytest" else ref["path"],
            ref.get("config", ""),
            ref.get("project", ""),
        )
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
    pattern = (
        "(?:^| > | )(?:("
        + "|".join(
            re.escape(" ".join(r["title_path"]) if "title_path" in r else r["name"])
            for r in refs
        )
        + "))$"
    )
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
        project = refs[0].get("project", project)
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


def execution_batches(refs, *, merge=False, shared_paths=()):
    grouped = {}
    for position, ref in enumerate(refs):
        if ref["kind"] != "playwright":
            key = (
                ref["kind"],
                ref.get("gate"),
                "" if ref["kind"] == "pytest" else ref["path"],
            )
        else:
            config, project = playwright_config(ref["path"])
            shared = (
                merge
                and ref["path"] in shared_paths
                and exact.test_list_line(ref) is not None
            )
            key = (
                ref["kind"],
                ref["gate"],
                config,
                ref.get("project", project),
                "shared" if shared else position,
            )
        grouped.setdefault(key, []).append(ref)
    return list(grouped.values())


def execution_rows(kind, payload, root, group):
    if kind == "playwright":
        rows = tc._walk_playwright_suites(
            payload["suites"],
            Path(payload["config"]["rootDir"]),
            root,
            group[0]["gate"],
            config=group[0]["config"],
        )
        bad = [
            r
            for r in rows
            if r["disabled"]
            or r["status"] != "expected"
            or len(r["results"]) != 1
            or r["results"][0].get("status") != "passed"
            or r["results"][0].get("retry", 0) != 0
        ]
        if payload.get("errors"):
            raise ValueError("service-startup: runner reported global errors")
    else:
        rows, bad = [], []
        if payload.get("version") != 3:
            raise ValueError("unknown Vitest identity report version")
        for test in payload["rows"]:
            row = {**test, "path": tc._project_path(root, test["path"])}
            # Vitest reports filtered-out tests as skipped without execution diagnostics.
            # Selected skips and any unexpected test that actually ran still fail.
            if (
                test["status"] == "skipped"
                and "retry_count" not in test
                and exact.identity(row) not in {exact.identity(r) for r in group}
            ):
                continue
            rows.append(row)
            if (
                test["status"] != "passed"
                or test.get("retry_count") != 0
                or test.get("repeat_count") != 0
                or test.get("errors")
            ):
                bad.append(row)
        if payload.get("errors"):
            raise ValueError("assertion: Vitest reported failure")
    exact.prove(group, rows, phase="execution")
    if bad:
        raise ValueError("assertion: failed, skipped or retried identities")
    return rows


def run_selected(refs, root=None):
    root = root or project_root()
    if not refs:
        raise ValueError("empty test selection is forbidden")
    gate = refs[0]["gate"]
    artifact = root / "test-results" / "harness" / gate
    artifact.mkdir(parents=True, exist_ok=True)
    phase_started = time.perf_counter()
    completed_refs = set()

    def record(phase, status, consumers, **extra):
        nonlocal phase_started
        now = time.perf_counter()
        row = {
            "version": exact.VERSION,
            "source": "selected-runner",
            "phase": phase,
            "status": status,
            "consumers": [
                {
                    k: r[k]
                    for k in (
                        "kind",
                        "gate",
                        "path",
                        "name",
                        "config",
                        "project",
                        "title_path",
                    )
                    if k in r
                }
                for r in consumers
            ],
            "duration_ms": round((now - phase_started) * 1000, 3),
            **extra,
        }
        phase_started = now
        print("HARNESS_STAGE " + json.dumps(row, ensure_ascii=True), flush=True)
        with (artifact / "stages.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    phase, current = "initialization", refs
    token = log_path.set(artifact / "initialization.log")
    try:
        code = ensure_prerequisites(refs, root, _run_supervised_command, record)
        if code:
            record("execution", "not-run", refs)
            return code
        log_path.reset(token)
        token = log_path.set(artifact / "collection.log")
        phase = "collection"
        resolved = []
        for group in batches(refs):
            current = group
            command, cwd = command_for(group, root)
            kind = group[0]["kind"]
            if kind == "pytest":
                resolved.extend(group)
                continue
            if kind == "vitest":
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
                        *(
                            ["--project", group[0].get("project", project)]
                            if group[0].get("project", project)
                            else []
                        ),
                        "--grep",
                        command[-2],
                    ],
                )
            resolved.extend(exact.resolve(group, rows))
            record("collection", "passed", group)
        javascript = [r for r in resolved if r["kind"] != "pytest"]
        if javascript:
            exact.prove(javascript, javascript, phase="collection")
        settings = load_config()["verification"].get("execution", {})
        groups = execution_batches(
            resolved,
            merge=settings.get("merge_playwright", False),
            shared_paths=settings.get("shared_test_paths", []),
        )
        for number, group in enumerate(groups):
            current = group
            batch_id = f"batch-{number + 1:04d}"
            batch_root = artifact / batch_id
            batch_root.mkdir(parents=True, exist_ok=True)
            log_path.reset(token)
            token = log_path.set(batch_root / "output.log")
            command, cwd = command_for(group, root)
            kind = group[0]["kind"]
            phase = "collection"
            if kind == "playwright":
                lines = [exact.test_list_line(r) for r in group]
                if all(line is not None for line in lines):
                    selection = batch_root / "test-list.txt"
                    selection.write_text("\n".join(lines) + "\n", encoding="utf-8")
                    selectors = ["--test-list", str(selection)]
                    config, project = playwright_config(group[0]["path"])
                    command = [
                        command[0],
                        "exec",
                        "--",
                        "playwright",
                        "test",
                        "--config",
                        config,
                        *selectors,
                        "--retries=0",
                        "--workers=1",
                    ]
                else:
                    if len(group) != 1:
                        raise ValueError("cannot express exact batch selection")
                    selectors = [
                        re.escape(group[0]["path"].removeprefix("apps/web/")),
                        *(
                            ["--project", group[0]["project"]]
                            if group[0]["project"]
                            else []
                        ),
                        "--grep",
                        command[-2],
                    ]
                collected = tc._collect_playwright(
                    root, group[0]["config"], gate, selectors=selectors
                )
                exact.prove(group, collected, phase="collection")
                if any(r["disabled"] for r in collected):
                    raise ValueError("collection contains disabled tests")
                record("collection", "passed", group, batch_id=batch_id)
            phase = "execution"
            with ExitStack() as cleanup:
                env = (
                    {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"} if kind == "pytest" else {}
                )
                report = batch_root / "report.json"
                if kind == "playwright":
                    runtime = root / ".run"
                    runtime.mkdir(exist_ok=True)
                    env["GAVIN_E2E_RUN_ROOT"] = cleanup.enter_context(
                        tempfile.TemporaryDirectory(prefix=batch_id + "-", dir=runtime)
                    )
                    env["PLAYWRIGHT_JSON_OUTPUT_NAME"] = str(report)
                    command.extend(
                        ["--reporter=json", "--output", str(batch_root / "artifacts")]
                    )
                elif kind == "vitest":
                    env["HARNESS_VITEST_REPORT"] = str(report)
                    command.extend(
                        [
                            "--retry=0",
                            "--reporter="
                            + str(
                                Path(__file__).with_name("vitest-identity-reporter.mjs")
                            ),
                        ]
                    )
                result = _run_supervised_command(
                    command, cwd=cwd, timeout_seconds=600, env=env
                )
                if kind != "pytest":
                    phase = "result-identity"
                    if not report.is_file():
                        raise ValueError("runner did not produce an identity report")
                    rows = execution_rows(
                        kind,
                        json.loads(report.read_text(encoding="utf-8")),
                        root,
                        group,
                    )
                if result.returncode:
                    record("assertion", "failed", group, batch_id=batch_id)
                    record(
                        "execution",
                        "not-run",
                        [r for later in groups[number + 1 :] for r in later],
                    )
                    return result.returncode
                phase = "cleanup"
            completed_refs.update((r["kind"], r["path"], r["name"]) for r in group)
            record("execution", "passed", group, batch_id=batch_id)
            if kind == "pytest":
                # Preserve in-process pytest's collected/executed proof for the outer gate.
                for line in result.stdout.splitlines():
                    if line.startswith("HARNESS_SELECTION "):
                        print(line)
            else:
                print(
                    "HARNESS_SELECTION "
                    + json.dumps({"collected": len(group), "executed": len(rows)})
                )
        return 0
    except BaseException as error:
        kind = (
            "service-startup"
            if str(error).startswith("service-startup:")
            else "assertion"
            if str(error).startswith("assertion:")
            else phase
        )
        record(kind, "failed", current, summary=str(error)[:300])
        record(
            "execution",
            "not-run",
            [
                r
                for r in refs
                if (r["kind"], r["path"], r["name"]) not in completed_refs
                and not any(
                    r["path"] == c["path"] and r["name"] == c["name"] for c in current
                )
            ],
        )
        raise
    finally:
        log_path.reset(token)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--gate", required=True)
    parser.add_argument("--selection", type=Path)
    args = parser.parse_args()
    plan = impact.build_plan(args.task)
    refs = [r for r in plan["test_refs"] if r["gate"] == args.gate]
    if args.selection:
        selected = json.loads(args.selection.read_text(encoding="utf-8"))
        from .diagnostics import match_current

        refs = match_current([r for r in selected if r["gate"] == args.gate], refs)
    return run_selected(refs)


if __name__ == "__main__":
    raise SystemExit(main())
