from __future__ import annotations

import json

import pytest

from harness.tools import impact
from harness.tools import product_verification as pv
from harness.verification.tests.test_impact import TASK
from harness.verification.tests.test_impact import selection as selection_fixture


@pytest.fixture
def selection(tmp_path, monkeypatch):
    return selection_fixture.__wrapped__(tmp_path, monkeypatch)


def test_affected_consumer_requires_transitive_review(selection, monkeypatch):
    root, changes, save = selection
    registry = root / "harness/verification/impact/ownership.json"
    units = json.loads(registry.read_text())["units"]
    units["M06.profile"]["dependents"] = ["M08.consumer"]
    units["M08.consumer"] = {
        "paths": ["consumer.py"],
        "cases": ["M08-TRACE-P0"],
        "dependents": [],
    }
    registry.write_text(json.dumps({"units": units}))
    changes[0]["dependencies"][0].update(affected=True, cases=["M06-TRACE-P0"])
    save()
    with pytest.raises(ValueError, match="M08.consumer"):
        impact.build_plan(TASK, paths=[changes[0]["path"]], root=root)
    changes[0]["dependencies"].append(
        {
            "unit": "M08.consumer",
            "affected": False,
            "cases": [],
            "reason": "Consumer does not use the changed field",
        }
    )
    save()
    monkeypatch.setattr(
        pv,
        "verification_case_plan",
        lambda *_: {"AC-1": ["M08-TRACE-P0", "M06-TRACE-P0"]},
    )
    assert impact.build_plan(TASK, paths=[changes[0]["path"]], root=root)[
        "selected_cases"
    ] == ["M06-TRACE-P0", "M08-TRACE-P0"]


def test_cycles_terminate_but_unreachable_decisions_are_rejected(selection):
    root, changes, save = selection
    registry = root / "harness/verification/impact/ownership.json"
    units = json.loads(registry.read_text())["units"]
    units["M06.profile"]["dependents"] = ["M08.fixture"]
    registry.write_text(json.dumps({"units": units}))
    impact.build_plan(TASK, paths=[changes[0]["path"]], root=root)
    changes[0]["dependencies"].append(
        {
            "unit": "M08.fixture",
            "affected": False,
            "cases": [],
            "reason": "Unreachable duplicate of origin",
        }
    )
    save()
    with pytest.raises(ValueError, match="dependent"):
        impact.build_plan(TASK, paths=[changes[0]["path"]], root=root)


def test_contract_documents_and_registry_never_silently_become_structural(selection):
    root, _, _ = selection
    for path in [
        "harness/workflows/verify.md",
        "harness/verification/impact/ownership.json",
        "README.md",
        "harness/verification/evidence/unregistered.py",
    ]:
        with pytest.raises(ValueError, match="missing analysis"):
            impact.build_plan(TASK, paths=[path], root=root)


def test_ambiguous_ownership_blocks_even_when_one_owner_is_declared(selection):
    root, changes, _ = selection
    registry = root / "harness/verification/impact/ownership.json"
    units = json.loads(registry.read_text())["units"]
    units["M06.profile"]["paths"].append(changes[0]["path"])
    registry.write_text(json.dumps({"units": units}))
    with pytest.raises(ValueError, match="ambiguous"):
        impact.build_plan(TASK, paths=[changes[0]["path"]], root=root)


def test_spec_lint_allows_planned_cases_without_implementation_plan(monkeypatch):
    from harness.tools import summarizer

    monkeypatch.setattr(summarizer, "ensure_spec_in_git_history", lambda *_: None)
    monkeypatch.setattr(
        pv, "verification_contract", lambda _: (["AC-1"], {"harness-tests": ["AC-1"]})
    )
    monkeypatch.setattr(
        pv, "verification_case_plan", lambda *_: {"AC-1": ["M08-NEW-01"]}
    )
    monkeypatch.setattr(pv, "verification_profile", lambda _: "focused")
    monkeypatch.setattr(
        impact,
        "build_plan",
        lambda *_: pytest.fail("spec-lint requires future implementation"),
    )
    assert pv.lint_task_contract(TASK)[2] == "focused"
