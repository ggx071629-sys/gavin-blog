from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from harness.tools import product_verification as pv
from harness.tools import selected_tests as runner
from harness.tools import verification_inputs as inputs


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
        runner.tc, "_collect_playwright", lambda *_, **__: [{**ref, "disabled": []}]
    )
    calls = []

    def invoke(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=7, stdout="build failed", stderr="")

    monkeypatch.setattr(runner, "_run_supervised_command", invoke)
    assert runner.run_selected([ref], tmp_path) == 7
    assert len(calls) == 1 and calls[0][-2:] == ["run", "build"]


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
        runner.tc, "_collect_playwright", lambda *_, **__: [{**ref, "disabled": []}]
    )
    calls = []

    def invoke(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout="1 passed (1s)", stderr="")

    monkeypatch.setattr(runner, "_run_supervised_command", invoke)
    assert not (tmp_path / "apps/web/.output").exists()
    assert runner.run_selected([ref], tmp_path) == 0
    assert len(calls) == 2 and calls[0][-2:] == ["run", "build"]


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
        runner.tc, "_collect_playwright", lambda *_, **__: [{**ref, "disabled": []}]
    )
    roots = []

    def invoke(command, **kwargs):
        run_root = Path(kwargs["env"]["GAVIN_E2E_RUN_ROOT"])
        assert run_root.is_dir() and run_root.is_relative_to(tmp_path)
        roots.append(run_root)
        assert "build" not in command
        return SimpleNamespace(returncode=0, stdout="1 passed (1s)", stderr="")

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
