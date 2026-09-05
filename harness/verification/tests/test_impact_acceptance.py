from harness.tools.impact_acceptance import validate_comparison, workload_contract


def test_cost_comparison_rejects_missing_failed_or_fixture_only_samples():
    assert validate_comparison({"samples": []})
    rows = [
        {
            "version": v,
            "workload": w,
            "status": "passed",
            "closed": True,
            "evidence_sha256": "a" * 64,
            "kind": "real-module",
            "executed": 1,
            "wall_ms": 1.0,
            "output_bytes": 100,
        }
        for v in ["before", "after"]
        for w in ["harness", "profile-api"]
    ]
    assert validate_comparison({"samples": rows}) == []
    rows[0]["kind"] = "synthetic-fixture"
    rows[1]["closed"] = False
    errors = validate_comparison({"samples": rows})
    assert any("fixture-only" in e for e in errors)
    assert any("incomplete real CLI closure" in e for e in errors)


def test_benchmark_uses_existing_real_module_sources_and_tests():
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    for workload in ["harness", "profile-api"]:
        source, _, gate, path, name = workload_contract(workload)
        assert (root / source).is_file()
        assert ("def " + name + "(") in (root / path).read_text(encoding="utf-8")
        assert gate in ["harness-tests", "api-tests"]
