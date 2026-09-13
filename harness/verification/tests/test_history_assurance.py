from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.tools import assurance, indexer


def _document(path: Path, document_id: str, *, status: str | None = None) -> None:
    status_line = f"status: {status}\n" if status else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"id: {document_id}\n"
        "level: L1\n"
        "summary: fixture\n"
        "load_when:\n"
        "  - fixture\n"
        f"{status_line}"
        "---\n\n# Fixture\n",
        encoding="utf-8",
    )


def test_scope_filter_hides_only_explicit_terminal_statuses(tmp_path: Path) -> None:
    _document(tmp_path / "policy.md", "policy")
    _document(tmp_path / "proposed.md", "proposed", status="proposed")
    _document(tmp_path / "accepted.md", "accepted", status="accepted")
    _document(tmp_path / "applied.md", "applied", status="applied")
    _document(tmp_path / "no-action.md", "no-action", status="reviewed-no-action")

    rendered = indexer.render_scope(
        "Evolution",
        tmp_path,
        exclude_statuses={"applied", "reviewed-no-action", "rejected"},
    )

    assert "policy.md" in rendered
    assert "proposed.md" in rendered
    assert "accepted.md" in rendered
    assert "applied.md" not in rendered
    assert "no-action.md" not in rendered


def test_scope_filter_is_deterministic(tmp_path: Path) -> None:
    _document(tmp_path / "b.md", "b", status="proposed")
    _document(tmp_path / "a.md", "a", status="accepted")

    first = indexer.render_scope("Evolution", tmp_path, exclude_statuses={"applied"})
    second = indexer.render_scope("Evolution", tmp_path, exclude_statuses={"applied"})

    assert first == second
    assert first.index("a.md") < first.index("b.md")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_inventory_conservatively_classifies_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence = tmp_path / "evidence"
    config = {"verification": {"evidence": "evidence"}}
    monkeypatch.setattr(assurance, "harness_root", lambda: tmp_path)
    monkeypatch.setattr(assurance, "load_config", lambda: config)
    _write_json(
        evidence / "20260812-v2.json",
        {
            "schema_version": 2,
            "status": "passed",
            "execution": {"mode": "git-worktree", "cleanup_status": "passed"},
            "checks": [{"kind": "product", "status": "passed"}],
        },
    )
    _write_json(
        evidence / "20260812-legacy-app.json",
        {
            "schema_version": 1,
            "status": "passed",
            "checks": [{"name": "indexes", "status": "passed"}],
        },
    )
    _write_json(
        evidence / "20260812-legacy-app.application.json",
        {"schema_version": 1, "status": "passed"},
    )
    _write_json(
        evidence / "20260812-legacy-structure.json",
        {
            "schema_version": 1,
            "status": "passed",
            "checks": [{"name": "links", "status": "passed"}],
        },
    )
    _write_json(evidence / "20260812-invalid.json", {"schema_version": 2, "status": "passed"})
    _write_json(
        evidence / "20260812-transitional.json",
        {
            "schema_version": 2,
            "status": "passed",
            "checks": [{"kind": "product", "status": "passed"}],
        },
    )

    result = assurance.inventory()
    levels = {record["task_id"]: record["assurance"] for record in result["records"]}

    assert levels == {
        "20260812-invalid": "invalid",
        "20260812-legacy-app": "legacy-product-reported",
        "20260812-legacy-structure": "legacy-structure-only",
        "20260812-transitional": "v2-transitional-product-reported",
        "20260812-v2": "v2-product-verified",
    }
    assert result["auxiliary_files"] == 1
    assert sum(result["assurance"].values()) == result["tasks"] == 5


def test_transitional_v2_rejects_malformed_execution_and_failed_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(assurance, "harness_root", lambda: tmp_path)
    monkeypatch.setattr(
        assurance,
        "load_config",
        lambda: {"verification": {"evidence": "evidence"}},
    )
    _write_json(
        tmp_path / "evidence" / "20260812-bad-execution.json",
        {
            "schema_version": 2,
            "status": "passed",
            "execution": {"mode": "shared"},
            "checks": [{"kind": "product", "status": "passed"}],
        },
    )
    _write_json(
        tmp_path / "evidence" / "20260812-failed-check.json",
        {
            "schema_version": 2,
            "status": "passed",
            "checks": [{"kind": "product", "status": "failed"}],
        },
    )

    result = assurance.inventory()

    assert result["assurance"]["invalid"] == 2
    assert result["assurance"]["v2-transitional-product-reported"] == 0


def test_schema_v1_product_checks_remain_legacy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(assurance, "harness_root", lambda: tmp_path)
    monkeypatch.setattr(
        assurance,
        "load_config",
        lambda: {"verification": {"evidence": "evidence"}},
    )
    _write_json(
        tmp_path / "evidence" / "20260812-reported.json",
        {
            "schema_version": 1,
            "status": "passed",
            "checks": [{"name": "api-tests", "status": "passed"}],
        },
    )

    result = assurance.inventory()

    assert result["records"][0]["assurance"] == "legacy-product-reported"
    assert result["assurance"]["v2-product-verified"] == 0
