from harness.tools.impact_acceptance import validate_comparison, workload_contract


def test_paired_cost_summary_retains_failures_and_uses_median_and_range():
    from harness.tools.impact_acceptance import paired_summary
    rows = [{"workload": "web", "version": v, "status": "passed", "closed": True,
             "executed": 2, "wall_ms": ms}
            for v, values in (("before", [9, 10, 11]), ("after", [7, 8, 9])) for ms in values]
    summary = paired_summary(rows)["web"]
    assert summary["improved"] and summary["after"] == {"median_ms": 8, "range_ms": [7, 9]}
    rows[0]["status"] = "failed"
    assert not paired_summary(rows)["web"]["eligible"]
    assert paired_summary(rows)["web"]["samples"] == 6


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
            "wall_ms": 0.8 if v == "after" else 1.0,
            "output_bytes": 100,
        }
        for v in ["before", "after"]
        for w in ["harness", "profile-api"]
    ]
    rows.append(
        {
            "workload": "profile-web",
            "status": "passed",
            "closed": True,
            "executed": 3,
            "kinds": ["pytest", "vitest", "playwright"],
        }
    )
    assert validate_comparison({"samples": rows}) == []
    rows[0]["kind"] = "synthetic-fixture"
    rows[1]["closed"] = False
    errors = validate_comparison({"samples": rows})
    assert any("fixture-only" in e for e in errors)
    assert any("incomplete real CLI closure" in e for e in errors)
    rows[0]["kind"] = "real-module"
    rows[1]["closed"] = True
    next(
        r
        for r in rows
        if r.get("version") == "after" and r["workload"] == "profile-api"
    )["wall_ms"] = 10
    assert any("did not improve" in e for e in validate_comparison({"samples": rows}))


def test_benchmark_uses_existing_real_module_sources_and_tests():
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    for workload in ["harness", "profile-api"]:
        source, _, gate, path, name = workload_contract(workload)
        assert (root / source).is_file()
        assert ("def " + name + "(") in (root / path).read_text(encoding="utf-8")
        assert gate in ["harness-tests", "api-tests"]


def test_acceptance_cleanup_rejects_paths_outside_owned_fixture_roots(tmp_path):
    import pytest

    from harness.tools.impact_acceptance import retain_and_cleanup_sample

    with pytest.raises(ValueError, match="not an owned temporary repository"):
        retain_and_cleanup_sample({"repository": str(tmp_path / "repository")})
    assert tmp_path.exists()
