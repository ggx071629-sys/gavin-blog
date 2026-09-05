from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from harness.tools import diagnostics, run_artifacts, snapshot_check
from harness.tools import exact_identity as exact
from harness.tools import execution_contracts as contracts
from harness.tools import isolated_verification as isolation
from harness.tools import selected_tests as runner


def ref(name="中文 [x]", path="a.spec.ts", **extra):
    return {
        "kind": "playwright",
        "gate": "e2e",
        "path": "apps/web/tests/e2e/" + path,
        "name": name,
        "config": "playwright.config.ts",
        "project": "chromium",
        "title_path": ["outer", name],
        **extra,
    }


def test_snapshot_failure_stops_before_dependency_links_and_product_calls(
    tmp_path, monkeypatch
):
    temporary = tmp_path / "isolation"
    temporary.mkdir()
    monkeypatch.setattr(isolation.tempfile, "mkdtemp", lambda **_: str(temporary))
    monkeypatch.setattr(
        isolation, "isolation_config", lambda: {"reuse_paths": ["node_modules"]}
    )

    def git(*args):
        if args[:2] == ("worktree", "add"):
            Path(args[-2]).mkdir()
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(isolation, "_run_git", git)
    monkeypatch.setattr(
        isolation,
        "snapshot_preflight",
        lambda *_: {
            "name": "harness-integrity",
            "passed": False,
            "status": "failed",
            "duration_ms": 0,
            "result": {"failure": {"kind": "snapshot-input"}},
        },
    )
    monkeypatch.setattr(
        isolation,
        "_create_directory_link",
        lambda *_: pytest.fail("linked dependency before preflight"),
    )
    monkeypatch.setattr(
        isolation,
        "run_gates",
        lambda *_, **__: pytest.fail("product ran after snapshot failure"),
    )
    results, context = isolation.run_in_worktree(
        {"harness-integrity": [], "e2e": []}, "head"
    )
    assert results[0]["status"] == "failed" and context["not_run"] == ["e2e"]
    assert context["cleanup_status"] == "passed" and not temporary.exists()


def test_snapshot_checks_missing_link_without_collecting(monkeypatch):
    monkeypatch.setattr(
        snapshot_check.validator,
        "run_checks",
        lambda: [
            {
                "name": "links",
                "status": "failed",
                "passed": False,
                "details": ["missing committed image"],
            }
        ],
    )
    monkeypatch.setattr(
        snapshot_check.impact,
        "build_plan",
        lambda *_: pytest.fail("plan after failed checks"),
    )
    result = snapshot_check.inspect("20260906-example")
    assert result["checks"][0]["status"] == "failed" and result["plan_digest"] is None


def test_prerequisites_are_once_per_worktree_and_failure_blocks_consumers(tmp_path):
    calls, records = [], []
    for path in contracts.prerequisites([ref()])[0]["inputs"]:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("source", encoding="utf-8")

    def invoke(command, **_):
        calls.append(command)
        (tmp_path / "apps/web/.nuxt").mkdir(exist_ok=True)
        return SimpleNamespace(returncode=0)

    record = lambda *a, **kw: records.append((a, kw))
    assert contracts.ensure_prerequisites([ref()], tmp_path, invoke, record) == 0
    assert contracts.ensure_prerequisites([ref("other")], tmp_path, invoke, record) == 0
    assert len(calls) == 1 and records[-1][0][1] == "reused-in-worktree"
    shutil.rmtree(tmp_path / "apps/web/.nuxt")
    assert (
        contracts.ensure_prerequisites(
            [ref()], tmp_path, lambda *a, **k: SimpleNamespace(returncode=9), record
        )
        == 9
    )
    assert records[-1][0][0:2] == ("initialization", "failed")
    assert contracts.prerequisites([{"kind": "pytest"}]) == []


def test_exact_identity_rejects_same_count_different_titles_projects_and_duplicates():
    a, b = ref(), ref("other", "b.spec.ts")
    exact.prove([a, b], [b, a], phase="execution")
    for actual in (
        [a, a],
        [a, ref("wrong", "b.spec.ts")],
        [a],
        [a, b, ref("extra")],
        [a, {**b, "project": "firefox"}],
        [a, {**b, "title_path": ["different", "other"]}],
    ):
        with pytest.raises(ValueError, match="identity mismatch"):
            exact.prove([a, b], actual, phase="execution")
    legacy = {
        k: v for k, v in a.items() if k not in {"config", "project", "title_path"}
    }
    with pytest.raises(ValueError, match="duplicate"):
        exact.resolve([legacy], [a, {**a, "title_path": ["nested", a["name"]]}])
    assert (
        exact.test_list_line(a) == "[chromium] › tests/e2e/a.spec.ts › outer › 中文 [x]"
    )
    assert exact.test_list_line(ref("unsafe > title")) is None
    assert exact.test_list_line(ref("unsafe\n title")) is None


def test_batches_isolate_undeclared_and_only_merge_compatible_shared_identities():
    a, b = ref(), ref("other", "b.spec.ts")
    assert len(runner.execution_batches([a, b])) == 2
    assert len(runner.execution_batches([a, b], merge=True)) == 2
    shared = [a["path"], b["path"]]
    assert len(runner.execution_batches([a, b], merge=True, shared_paths=shared)) == 1
    assert (
        len(
            runner.execution_batches(
                [a, {**b, "project": "firefox"}], merge=True, shared_paths=shared
            )
        )
        == 2
    )


def test_diagnose_failed_requires_trusted_consumers_and_matches_current_plan():
    a, b = ref(), ref("other", "b.spec.ts")
    plan = {"test_refs": [a, b]}
    stage = {
        "source": "selected-runner",
        "version": 3,
        "status": "failed",
        "phase": "initialization",
        "consumers": [a],
    }
    ledger = {
        "runs": [
            {
                "state": "failed",
                "attempts": [{"check": {"result": {"stages": [stage]}}}],
            }
        ]
    }
    assert diagnostics.select(plan, ledger=ledger) == [a]
    with pytest.raises(ValueError, match="removed or ambiguous"):
        diagnostics.select({"test_refs": [b]}, ledger=ledger)
    stage["source"] = "log-heuristic"
    with pytest.raises(ValueError, match="no recoverable"):
        diagnostics.select(plan, ledger=ledger)


def test_batch_artifacts_survive_later_calls_and_bounded_export(tmp_path):
    for batch in ("batch-0001", "batch-0002"):
        directory = tmp_path / "test-results/harness/e2e" / batch
        directory.mkdir(parents=True)
        (directory / "screen.png").write_bytes(batch.encode())
    destination = tmp_path / "export"
    run_artifacts.retain(tmp_path, destination)
    files = list(destination.rglob("screen.png"))
    assert len(files) == 2 and {p.read_bytes() for p in files} == {
        b"batch-0001",
        b"batch-0002",
    }


def test_diagnosis_does_not_write_formal_evidence_or_aggregate(tmp_path, monkeypatch):
    from contextlib import nullcontext

    from harness.tools import run_store
    from harness.tools.run_store import RunStore

    task = "20260906-fixture"
    monkeypatch.setattr(run_store, "store_root", lambda: tmp_path)
    store = RunStore(task)
    ledger = store.read()
    ledger["aggregate"] = {"sentinel": "formal"}
    store.write(ledger)
    original = store.path.read_bytes()
    a = ref()
    plan = {"test_refs": [a]}
    monkeypatch.setattr(diagnostics, "repository_lock", nullcontext)
    monkeypatch.setattr(
        diagnostics.verification_resume,
        "prepare",
        lambda *_: {
            "impact": plan,
            "mappings": {"e2e": []},
            "snapshot": {"head": "fixed"},
        },
    )
    monkeypatch.setattr(diagnostics, "select", lambda *_, **__: [a])
    monkeypatch.setattr(
        diagnostics.verification_inputs, "preflight", lambda *_, **__: None
    )
    monkeypatch.setattr(
        diagnostics.verification_resume, "prepared_in_process", lambda *_: None
    )
    monkeypatch.setattr(
        diagnostics.isolated_verification,
        "run_in_worktree",
        lambda *_, **__: ([{"status": "passed"}], {"cleanup_status": "passed"}),
    )
    assert (
        diagnostics.command(SimpleNamespace(task_id=task, case="case", failed=False))
        == 0
    )
    assert store.path.read_bytes() == original
    diagnostic = json.loads((tmp_path / "diagnostics" / f"{task}.json").read_bytes())[
        "payload"
    ]
    assert (
        diagnostic["aggregate"] is None and diagnostic["runs"][0]["certifying"] is False
    )


def test_reporter_proofs_reject_skipped_retried_and_same_count_substitutions(tmp_path):
    chosen = ref()
    payload = {
        "config": {"rootDir": str(tmp_path)},
        "suites": [
            {
                "title": "file",
                "suites": [
                    {
                        "title": "outer",
                        "specs": [
                            {
                                "title": chosen["name"],
                                "file": chosen["path"],
                                "tests": [
                                    {
                                        "projectName": "chromium",
                                        "expectedStatus": "passed",
                                        "status": "expected",
                                        "results": [{"status": "passed", "retry": 0}],
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }
    assert len(runner.execution_rows("playwright", payload, tmp_path, [chosen])) == 1
    test = payload["suites"][0]["suites"][0]["specs"][0]["tests"][0]
    test["results"][0]["retry"] = 1
    with pytest.raises(ValueError, match="retried"):
        runner.execution_rows("playwright", payload, tmp_path, [chosen])
    test["results"][0].update(retry=0, status="skipped")
    with pytest.raises(ValueError, match="skipped"):
        runner.execution_rows("playwright", payload, tmp_path, [chosen])
    test["results"][0]["status"] = "passed"
    test["projectName"] = "firefox"
    with pytest.raises(ValueError, match="identity mismatch"):
        runner.execution_rows("playwright", payload, tmp_path, [chosen])


def test_vitest_filtered_skips_never_hide_selected_skip_retry_or_extra_execution(
    tmp_path,
):
    chosen = {**ref(), "kind": "vitest", "config": "vitest.config.ts", "project": ""}
    actual = {
        **chosen,
        "path": str(tmp_path / chosen["path"]),
        "status": "passed",
        "retry_count": 0,
        "repeat_count": 0,
        "errors": 0,
    }
    skipped = {**actual, "title_path": ["outer", "unselected"], "status": "skipped"}
    skipped.pop("retry_count")
    report = {"version": 3, "rows": [actual, skipped], "errors": 0}
    assert len(runner.execution_rows("vitest", report, tmp_path, [chosen])) == 1
    actual["status"] = "skipped"
    with pytest.raises(ValueError):
        runner.execution_rows("vitest", report, tmp_path, [chosen])
    actual.update(status="passed", retry_count=1)
    with pytest.raises(ValueError):
        runner.execution_rows("vitest", report, tmp_path, [chosen])
    actual["retry_count"] = 0
    skipped.update(status="passed", retry_count=0)
    with pytest.raises(ValueError, match="identity mismatch"):
        runner.execution_rows("vitest", report, tmp_path, [chosen])


def test_real_git_snapshot_cannot_borrow_workspace_only_link_target(
    tmp_path, monkeypatch
):
    from harness.verification.tests.test_impact_cli import (
        REPO,
        TASK,
        fixture_repository,
        git,
    )

    root = fixture_repository(tmp_path)
    shutil.copyfile(
        REPO / "harness/verification/checks/links.py",
        root / "harness/verification/checks/links.py",
    )
    spec = root / f"harness/specs/active/{TASK}.md"
    spec.write_text(
        spec.read_text(encoding="utf-8") + "\n[local material](local-image.png)\n",
        encoding="utf-8",
    )
    (spec.parent / "local-image.png").write_bytes(b"workspace-only")
    # Track the link/check but deliberately leave its target untracked.
    git(
        root, "add", "harness/verification/checks/links.py", str(spec.relative_to(root))
    )
    git(root, "commit", "-qm", "snapshot link fixture")
    source = git(root, "rev-parse", "HEAD").strip()
    monkeypatch.setattr(isolation, "project_root", lambda: root)
    monkeypatch.setattr(
        isolation,
        "_run_git",
        lambda *args: subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, check=False
        ),
    )
    monkeypatch.setattr(
        isolation, "run_gates", lambda *a, **k: pytest.fail("product gate ran")
    )
    results, context = isolation.run_in_worktree(
        {"harness-integrity": [], "e2e": []}, source
    )
    assert results[0]["result"]["failure"]["kind"] == "snapshot-input"
    assert any("local-image.png" in d for d in results[0]["details"])
    assert (
        context["cleanup_status"] == "passed"
        and (spec.parent / "local-image.png").exists()
    )
