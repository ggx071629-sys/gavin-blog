from pathlib import Path

from harness.tools.impact_registry import audit


def test_current_governed_sources_have_unique_existing_ownership_and_cases():
    result = audit(Path(__file__).resolve().parents[3])
    assert result["paths"] > 300
    assert result["errors"] == []


def test_new_unknown_source_fails_without_expanding_test_scope():
    result = audit(
        Path(__file__).resolve().parents[3],
        paths=["apps/web/utils/new-unregistered.ts"],
    )
    assert any("new-unregistered.ts: missing ownership" in e for e in result["errors"])
