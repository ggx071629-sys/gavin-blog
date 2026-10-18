from __future__ import annotations

import json
import subprocess
import sys

import pytest

from harness.tools import (
    impact,
    selected_tests,
    verification_inputs,
    verification_resume,
)
from harness.tools import product_verification as pv
from harness.verification.tests.test_module_coverage import _write_project

TASK = "20260905-impact-fixture"


@pytest.fixture
def selection(tmp_path, monkeypatch):
    _write_project(tmp_path)
    path = "harness/tools/fixture.py"
    units = {
        "M08.fixture": {
            "paths": [path],
            "cases": ["M08-TRACE-P0"],
            "dependents": ["M06.profile"],
        },
        "M06.profile": {
            "paths": ["apps/api/app/profile.py"],
            "cases": ["M06-TRACE-P0"],
            "dependents": [],
        },
    }
    decisions = [
        {
            "path": path,
            "owner": "M08.fixture",
            "reason": "selection implementation changes",
            "cases": ["M08-TRACE-P0"],
            "dependencies": [
                {
                    "unit": "M06.profile",
                    "affected": False,
                    "reason": "profile response contract is unchanged",
                    "cases": [],
                }
            ],
        }
    ]
    folder = tmp_path / "harness/verification/impact"
    folder.mkdir()
    (folder / "ownership.json").write_text(json.dumps({"units": units}))
    plan_file = folder / f"{TASK}.json"

    def save():
        plan_file.write_text(
            json.dumps({"schema_version": 1, "task_id": TASK, "changes": decisions})
        )

    save()
    monkeypatch.setattr(
        pv,
        "verification_contract",
        lambda _: (
            ["AC-1"],
            {"harness-tests": ["AC-1"], "harness-integrity": ["AC-1"]},
        ),
    )
    monkeypatch.setattr(
        pv, "verification_case_plan", lambda *_: {"AC-1": ["M08-TRACE-P0"]}
    )
    monkeypatch.setattr(pv, "verification_profile", lambda _: "focused")
    return tmp_path, decisions, save


def test_exact_impact_and_exclusions_do_not_follow_dependency_edges(selection):
    root, decisions, _ = selection
    plan = impact.build_plan(TASK, paths=[decisions[0]["path"]], root=root)
    assert plan["selected_cases"] == ["M08-TRACE-P0"]
    assert len(plan["test_refs"]) == 1
    assert "M06-TRACE-P0" in {c["case"] for c in plan["excluded_cases"]}
    assert plan["required_gates"] == ["harness-integrity", "harness-tests"]


def test_shared_contract_propagates_only_with_reviewed_case_reason(
    selection, monkeypatch
):
    root, decisions, save = selection
    decisions[0]["dependencies"][0].update(
        affected=True,
        cases=["M06-TRACE-P0"],
        reason="consumer parses the changed response field",
    )
    save()
    monkeypatch.setattr(
        pv,
        "verification_case_plan",
        lambda *_: {"AC-1": ["M08-TRACE-P0", "M06-TRACE-P0"]},
    )
    plan = impact.build_plan(TASK, paths=[decisions[0]["path"]], root=root)
    assert plan["selected_cases"] == ["M06-TRACE-P0", "M08-TRACE-P0"]
    assert "consumer parses" in plan["reasons"]["M06-TRACE-P0"][0]["reason"]


def test_unknown_path_and_incomplete_dependency_analysis_block(selection):
    root, decisions, save = selection
    with pytest.raises(ValueError, match="impact gap.*scripts/unknown"):
        impact.build_plan(TASK, paths=["scripts/unknown.py"], root=root)
    decisions[0]["dependencies"] = []
    save()
    with pytest.raises(ValueError, match="review every dependent"):
        impact.build_plan(TASK, paths=[decisions[0]["path"]], root=root)


def test_global_structure_never_calls_collectors(selection, monkeypatch):
    from harness.tools import module_verification as mv

    root, _, _ = selection
    monkeypatch.setattr(
        mv,
        "collect_test_index",
        lambda *_: pytest.fail("cross-project collector called"),
    )
    _, errors = mv.validate_module_contract(
        root,
        root / "harness",
        {"verification": {"gates": {"harness-tests": {}}}},
        structure_only=True,
    )
    assert errors == []


def test_runner_uses_exact_selectors_without_suite_scripts(tmp_path):
    python = (
        tmp_path
        / "apps/api/.venv"
        / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    )
    python.parent.mkdir(parents=True)
    python.touch()
    refs = [
        {
            "kind": "pytest",
            "path": "harness/verification/tests/test_a.py",
            "name": "test_selected",
        }
    ]
    command, cwd = selected_tests.command_for(refs, tmp_path)
    assert command[-1] == "harness/verification/tests/test_a.py::test_selected"
    assert cwd == tmp_path
    assert "harness/verification/tests" not in command
    js = [
        {
            "kind": "vitest",
            "path": "apps/web/tests/a.test.ts",
            "name": "selected [literal]",
        },
        {"kind": "vitest", "path": "apps/web/tests/b.test.ts", "name": "other"},
    ]
    assert len(selected_tests.batches(js)) == 2
    assert (
        selected_tests.playwright_config("apps/web/tests/quality/a.spec.ts")[1]
        == "quality-chromium"
    )


def test_real_pytest_selection_skips_unaffected_and_rejects_skipped_test(tmp_path):
    source = tmp_path / "test_selected.py"
    source.write_text(
        "import pytest\ndef test_selected(): assert True\ndef test_unaffected(): assert False\n@pytest.mark.skip\ndef test_skipped(): pass\n"
    )
    command = [sys.executable, "-c", selected_tests.PYTEST_RUNNER]
    ok = subprocess.run(
        [*command, str(source) + "::test_selected"],
        capture_output=True,
        check=False,
        text=True,
        cwd=tmp_path,
    )
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert '"collected": 1, "executed": 1' in ok.stdout
    skipped = subprocess.run(
        [*command, str(source) + "::test_skipped"],
        capture_output=True,
        check=False,
        text=True,
        cwd=tmp_path,
    )
    assert skipped.returncode != 0


def test_docs_snapshot_has_zero_dependency_scans_or_product_tools(monkeypatch):
    plan = {"test_refs": [], "task_id": TASK}
    monkeypatch.setattr(
        verification_inputs,
        "tree_digest",
        lambda *_: pytest.fail("installed tree scan"),
    )
    monkeypatch.setattr(
        verification_inputs.subprocess,
        "run",
        lambda *_a, **_k: pytest.fail("dependency process"),
    )
    monkeypatch.setattr(pv, "_configured_gates", dict)
    monkeypatch.setattr(pv, "head_commit", lambda: "head")
    monkeypatch.setattr(verification_inputs.platform, "system", lambda: "Windows")
    monkeypatch.setattr(verification_inputs.platform, "machine", lambda: "AMD64")
    snapshot = verification_inputs.scoped_snapshot({}, {}, plan)
    assert snapshot["dependencies"] == {}


def test_default_scope_is_fresh_even_with_matching_success():
    prepared = {
        "mappings": {"harness-tests": ["AC-1"]},
        "profile": "focused",
        "identity": "a",
        "reuse_enabled": False,
    }
    rows = verification_resume.gate_plan(prepared, {"runs": []})
    assert rows[0]["action"] == "execute"
