from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from harness.tools import product_verification as pv
from harness.tools import selected_tests as runner
from harness.tools import verification_inputs as inputs


@pytest.fixture(autouse=True)
def prerequisite_inputs(tmp_path):
    for relative in ("package-lock.json", "apps/web/nuxt.config.ts", "apps/web/tsconfig.json"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")


def collected(ref):
    config, project = runner.playwright_config(ref["path"])
    return {**ref, "disabled": [], "config": config, "project": project, "title_path": [ref["name"]]}


def successful(command, kwargs, root, ref):
    if "prepare" in command:
        (root / "apps/web/.nuxt").mkdir(exist_ok=True)
    elif "build" in command:
        (root / "apps/web/.output").mkdir(exist_ok=True)
    else:
        report = Path(kwargs["env"]["PLAYWRIGHT_JSON_OUTPUT_NAME"])
        report.write_text(json.dumps({"config": {"rootDir": str(root / "apps/web")}, "suites": [
            {"title": "file", "specs": [{"title": ref["name"], "file": ref["path"].removeprefix("apps/web/"),
              "tests": [{"projectName": collected(ref)["project"], "expectedStatus": "passed", "status": "expected",
                         "results": [{"status": "passed", "retry": 0}]}]}]}]}), encoding="utf-8")
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def test_failed_preview_build_prevents_selected_browser_execution(
    tmp_path, monkeypatch
):
    ref = {
        "kind": "playwright",
        "gate": "web-quality",
        "path": "apps/web/tests/quality/site-quality.spec.ts",
        "name": "chosen",
    }
    monkeypatch.setattr(
        runner.tc, "_collect_playwright", lambda *_, **__: [collected(ref)]
    )
    calls = []

    def invoke(command, **kwargs):
        calls.append(command)
        if "prepare" in command:
            return successful(command, kwargs, tmp_path, ref)
        return SimpleNamespace(returncode=7, stdout="build failed", stderr="")

    monkeypatch.setattr(runner, "_run_supervised_command", invoke)
    assert runner.run_selected([ref], tmp_path) == 7
    assert len(calls) == 2 and calls[1][-2:] == ["run", "build"]


def test_missing_preview_artifact_rebuilds_only_for_selected_quality_config(
    tmp_path, monkeypatch
):
    ref = {
        "kind": "playwright",
        "gate": "web-quality",
        "path": "apps/web/tests/quality/site-quality.spec.ts",
        "name": "chosen",
    }
    monkeypatch.setattr(
        runner.tc, "_collect_playwright", lambda *_, **__: [collected(ref)]
    )
    calls = []

    def invoke(command, **kwargs):
        calls.append(command)
        return successful(command, kwargs, tmp_path, ref)

    monkeypatch.setattr(runner, "_run_supervised_command", invoke)
    assert not (tmp_path / "apps/web/.output").exists()
    assert runner.run_selected([ref], tmp_path) == 0
    assert len(calls) == 3 and calls[1][-2:] == ["run", "build"]


def test_selected_browser_runtime_is_cleaned_without_building_other_configs(
    tmp_path, monkeypatch
):
    ref = {
        "kind": "playwright",
        "gate": "e2e",
        "path": "apps/web/tests/e2e/profile.spec.ts",
        "name": "chosen",
    }
    monkeypatch.setattr(
        runner.tc, "_collect_playwright", lambda *_, **__: [collected(ref)]
    )
    roots = []

    def invoke(command, **kwargs):
        if "prepare" in command:
            return successful(command, kwargs, tmp_path, ref)
        run_root = Path(kwargs["env"]["GAVIN_E2E_RUN_ROOT"])
        assert run_root.is_dir() and run_root.is_relative_to(tmp_path)
        roots.append(run_root)
        assert "build" not in command
        return successful(command, kwargs, tmp_path, ref)

    monkeypatch.setattr(runner, "_run_supervised_command", invoke)
    assert runner.run_selected([ref], tmp_path) == 0
    assert len(roots) == 1 and not roots[0].exists()


def test_default_same_process_input_identity_never_reads_installed_distributions(
    monkeypatch,
):
    monkeypatch.setattr(inputs, "load_reuse_policy", lambda: False)
    monkeypatch.setattr(
        inputs.subprocess,
        "run",
        lambda *_, **__: pytest.fail("installed dependency probe"),
    )
    monkeypatch.setattr(pv, "_configured_gates", dict)
    monkeypatch.setattr(pv, "head_commit", lambda: "head")
    monkeypatch.setattr(inputs.platform, "system", lambda: "Windows")
    monkeypatch.setattr(inputs.platform, "machine", lambda: "AMD64")
    result = inputs.scoped_snapshot(
        {},
        {},
        {"test_refs": [{"kind": "pytest", "path": "harness/verification/tests/a.py"}]},
    )
    assert result["dependencies"] == {} and result["reusable"] is False
    assert result["persistent_close"] is False


def test_reuse_dependency_probe_failure_has_bounded_diagnostic(monkeypatch):
    import subprocess

    monkeypatch.setattr(inputs, "load_reuse_policy", lambda: True)
    monkeypatch.setattr(pv, "_configured_gates", dict)
    monkeypatch.setattr(pv, "head_commit", lambda: "head")

    def failed(*args, **kwargs):
        raise subprocess.CalledProcessError(
            1,
            ["python", "-c", "internal script"],
            stderr="PackageNotFoundError: pytest",
        )

    monkeypatch.setattr(inputs.subprocess, "run", failed)
    with pytest.raises(
        pv.ProductVerificationError,
        match="dependency input check failed: PackageNotFoundError: pytest",
    ) as failure:
        inputs.scoped_snapshot(
            {},
            {},
            {
                "test_refs": [
                    {"kind": "pytest", "path": "harness/verification/tests/a.py"}
                ]
            },
        )
    assert "internal script" not in str(failure.value)


def test_same_process_resolution_rechecks_head_source_and_runtime_without_replanning(
    monkeypatch,
):
    from harness.tools import verification_resume as resume

    prepared = {
        "impact": {},
        "snapshot": {"head": "current"},
        "documentation": {"targets": []},
        "mappings": {},
        "fingerprints": {},
    }
    checks = []
    monkeypatch.setattr(pv, "head_commit", lambda: "current")
    monkeypatch.setattr(pv, "ensure_source_clean", lambda paths: checks.append(paths))
    monkeypatch.setattr(inputs, "input_snapshot", lambda *_: {"head": "current"})
    monkeypatch.setattr(
        resume, "prepare", lambda *_a, **_k: pytest.fail("redundant plan resolution")
    )
    assert resume.prepared_in_process(prepared) is prepared
    assert len(checks) == 1
    monkeypatch.setattr(inputs, "input_snapshot", lambda *_: {"head": "changed"})
    with pytest.raises(ValueError, match="runtime inputs changed"):
        resume.prepared_in_process(prepared)
    monkeypatch.setattr(pv, "head_commit", lambda: "new-head")
    with pytest.raises(ValueError, match="HEAD changed"):
        resume.prepared_in_process(prepared)
