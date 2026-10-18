from __future__ import annotations

import json
import socket

import pytest

from harness.tools import close_transaction, run_store, validator
from harness.tools import harness as cli
from harness.tools import verification_inputs as inputs
from harness.tools import verification_resume as resume

TASK = "20260905-resume-fixture"


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(run_store, "store_root", lambda: tmp_path / "local")
    monkeypatch.setattr(resume.inputs, "preflight", lambda _: None)
    monkeypatch.setattr(resume.pv, "ensure_source_clean", lambda *_: None)
    prepared = {
        "task_id": TASK,
        "criteria": ["AC-1"],
        "mappings": {g: ["AC-1"] for g in "ABCD"},
        "profile": "focused",
        "documentation": {"targets": []},
        "cases": {},
        "fingerprints": {},
        "snapshot": {"head": "a" * 40},
        "identity": "input-1",
    }
    monkeypatch.setattr(
        resume.inputs, "input_snapshot", lambda *_: prepared["snapshot"]
    )
    monkeypatch.setattr(resume, "prepare", lambda *_a, **_k: prepared)
    calls = []
    control = {"fail": "C", "cleanup": "passed", "interrupt": None}

    def isolated(mappings, head, *, gate_callback, artifact_root):
        results = []
        for gate, covered in mappings.items():
            calls.append(gate)
            gate_callback(gate, None)
            if gate == control["interrupt"]:
                raise KeyboardInterrupt()
            passed = gate != control["fail"]
            check = {
                "name": gate,
                "kind": "product",
                "status": "passed" if passed else "failed",
                "passed": passed,
                "covers": covered,
                "duration_ms": 1,
                "command": gate,
                "result": {
                    "exit_code": 0 if passed else 1,
                    "test_counts": {"passed": 1, "failed": 0, "skipped": 0},
                },
            }
            gate_callback(gate, check)
            results.append(check)
            if not passed:
                break
        return results, {
            "mode": "git-worktree",
            "source_commit": head,
            "cleanup_status": control["cleanup"],
        }

    monkeypatch.setattr(resume.isolated_verification, "run_in_worktree", isolated)
    return prepared, calls, control


def test_preflight_failure_starts_zero_product_gates(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        cli.validator,
        "run_checks",
        lambda: [{"name": "fixture", "status": "failed", "duration_ms": 0}],
    )
    monkeypatch.setattr(cli.lifecycle, "task_status", lambda _: "active")
    monkeypatch.setattr(
        cli.verification_resume, "execute", lambda *_a, **_k: calls.append("gate")
    )
    monkeypatch.setattr(
        cli.validator, "write_task_evidence", lambda *_: tmp_path / "failed.json"
    )
    monkeypatch.setattr(
        cli.product_verification, "derived_task_state", lambda *_: "active"
    )
    monkeypatch.setattr(cli, "_repeated_failure_hint", lambda _: "")
    results, _ = cli._execute_verification(TASK, observe_telemetry=False)
    assert calls == []
    assert not validator.passed(results)
    assert "global preflight failed" in results[-1]["details"][0]


def test_resume_only_failed_and_unrun_gates_and_preserves_failure(runtime):
    prepared, calls, control = runtime
    first, _ = resume.execute(prepared)
    assert calls == list("ABC") and not validator.passed(first)
    control["fail"] = None
    calls.clear()
    second, _ = resume.execute(prepared)
    assert calls == list("CD") and validator.passed(second)
    assert [c["provenance"]["mode"] for c in second] == [
        "reused",
        "reused",
        "executed",
        "executed",
    ]
    ledger = run_store.RunStore(TASK).read()
    failed = ledger["runs"][0]["attempts"][-1]
    assert failed["check"]["status"] == "failed"
    assert ledger["runs"][1]["attempts"][0]["retry_of"] == failed["id"]
    assert validator.summarize_checks(second)["test_counts"]["passed"] == 2


def test_latest_failure_blocks_older_success_and_fresh_executes_all(runtime, tmp_path):
    prepared, calls, control = runtime
    control["fail"] = None
    resume.execute(prepared)
    control["fail"] = "C"
    calls.clear()
    resume.execute(prepared, fresh=True)
    assert calls == list("ABC")
    with pytest.raises(run_store.StoreError, match="no complete authenticated"):
        resume.authenticate(TASK, tmp_path / "missing.json")
    plan = resume.gate_plan(prepared, run_store.RunStore(TASK).read())
    assert plan[2]["state"] == "failed"
    control["fail"] = None
    calls.clear()
    resume.execute(prepared)
    assert calls == ["C"]  # D's previous clean success has no newer attempt.


def test_release_always_requires_execution(runtime):
    prepared, calls, control = runtime
    control["fail"] = None
    prepared["profile"] = "release"
    resume.execute(prepared)
    calls.clear()
    resume.execute(prepared)
    assert calls == list("ABCD")


def test_authenticated_evidence_rejects_tampering_missing_key_and_input_drift(
    runtime, tmp_path
):
    prepared, _calls, control = runtime
    control["fail"] = None
    _, context = resume.execute(prepared)
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({"status": "passed", "execution": context}))
    resume.attest(TASK, evidence, prepared)
    assert resume.authenticate(TASK, evidence) == prepared
    original = evidence.read_bytes()
    evidence.write_bytes(original + b" ")
    with pytest.raises(run_store.StoreError, match="evidence bytes"):
        resume.authenticate(TASK, evidence)
    evidence.write_bytes(original)
    prepared["identity"] = "changed-toolchain"
    with pytest.raises(run_store.StoreError, match="inputs are stale"):
        resume.authenticate(TASK, evidence)
    assert all(
        row["action"] == "execute"
        for row in resume.gate_plan(prepared, run_store.RunStore(TASK).read())
    )
    store = run_store.RunStore(TASK)
    envelope = json.loads(store.path.read_bytes())
    envelope["payload"]["runs"][0]["attempts"][0]["check"]["result"]["exit_code"] = 99
    store.path.write_text(json.dumps(envelope))
    with pytest.raises(run_store.StoreError, match="authentication failed"):
        store.read()
    store.path.unlink()
    assert store.read()["runs"] == []
    (store.root / "authentication.key").unlink()
    with pytest.raises(run_store.StoreError, match="key is missing"):
        store.key()


def test_cleanup_failure_and_interrupt_invalidate_attempts_and_lock_is_exclusive(
    runtime,
):
    prepared, _calls, control = runtime
    control["cleanup"] = "failed"
    resume.execute(prepared)
    assert all(
        row["action"] == "execute"
        for row in resume.gate_plan(prepared, run_store.RunStore(TASK).read())
    )
    control.update(cleanup="passed", interrupt="B")
    with pytest.raises(KeyboardInterrupt):
        resume.execute(prepared)
    ledger = run_store.RunStore(TASK).read()
    assert ledger["runs"][-1]["state"] == "interrupted"
    assert not any(
        a["reusable"]
        for a in run_store.latest_attempts(ledger, prepared["identity"]).values()
    )
    with (  # noqa: SIM117 - the inner acquisition must occur after entering pytest.raises
        run_store.repository_lock(),
        pytest.raises(run_store.StoreError, match="repository lock"),
    ):
        with run_store.repository_lock():
            pytest.fail("concurrent operation entered")


def test_close_consumes_attestation_without_gates_or_collectors(
    runtime, tmp_path, monkeypatch
):
    prepared, calls, control = runtime
    control["fail"] = None
    _, context = resume.execute(prepared)
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({"status": "passed", "execution": context}))
    resume.attest(TASK, evidence, prepared)
    monkeypatch.setattr(cli.validator, "evidence_path", lambda _: evidence)
    monkeypatch.setattr(
        cli.product_verification, "validate_evidence", lambda *_a, **_k: []
    )
    monkeypatch.setattr(
        cli, "_execute_verification", lambda _: pytest.fail("close reran verification")
    )
    monkeypatch.setattr(
        cli.product_verification,
        "resolved_verification_cases",
        lambda *_: pytest.fail("collector invoked"),
    )
    calls.clear()
    assert cli._preflight_close([TASK])
    assert calls == []
    evidence.write_text('{"status":"passed"}')
    assert not cli._preflight_close([TASK])


def test_crashed_running_attempt_is_recovered_without_fallback(runtime):
    prepared, _, _ = runtime
    resume.execute(prepared)
    store = run_store.RunStore(TASK)
    ledger = store.read()
    ledger["runs"][0]["state"] = "running"
    store.write(ledger)
    recovered = store.recover()
    assert recovered["runs"][0]["state"] == "interrupted"
    assert all(
        row["action"] == "execute" for row in resume.gate_plan(prepared, recovered)
    )


def test_dependency_content_and_controlled_environment_identity(tmp_path, monkeypatch):
    installed = tmp_path / "installed"
    installed.mkdir()
    source = installed / "library.py"
    source.write_text("v1")
    old = inputs.tree_digest(installed)
    source.write_text("v2")
    assert inputs.tree_digest(installed) != old
    monkeypatch.setenv("PRIVATE_API_KEY", "should-never-be-forwarded")
    monkeypatch.setenv("GAVIN_E2E_WEB_PORT", "9000")
    assert "PRIVATE_API_KEY" not in inputs.controlled_environment()
    assert "GAVIN_E2E_WEB_PORT" not in inputs.controlled_environment()


def test_close_recovery_restores_complete_asset_set(runtime, tmp_path, monkeypatch):
    source = tmp_path / "active.md"
    archive = tmp_path / "archive.md"
    event = tmp_path / "event.json"
    original = "original spec"
    sha = "a" * 64
    monkeypatch.setattr(close_transaction.summarizer, "active_spec", lambda _: source)
    monkeypatch.setattr(close_transaction.summarizer, "archive_spec", lambda _: archive)
    monkeypatch.setattr(close_transaction.events, "event_path", lambda *_: event)
    monkeypatch.setattr(close_transaction.indexer, "write_indexes", list)

    def restore(task, text, path):
        source.write_text(text)
        path.unlink(missing_ok=True)

    monkeypatch.setattr(close_transaction.summarizer, "restore_spec", restore)
    close_transaction.begin([(TASK, archive, original, event, sha)], "head")
    archive.write_text(sha)
    event.write_text(sha)
    close_transaction.recover()
    assert source.read_text() == original
    assert (
        not archive.exists()
        and not event.exists()
        and not close_transaction.journal_path().exists()
    )


def test_port_conflict_is_reported_before_execution_without_killing(
    monkeypatch, tmp_path
):
    from harness.tools import isolated_verification

    monkeypatch.setattr(
        isolated_verification, "isolation_config", lambda: {"reuse_paths": []}
    )
    monkeypatch.setattr(inputs, "project_root", lambda: tmp_path)
    monkeypatch.setattr(inputs.pv, "_configured_gates", lambda: {"e2e": {}})
    monkeypatch.setattr(inputs.pv, "_command", lambda *_: ([], tmp_path, 1))
    monkeypatch.setattr(inputs, "port_owner", lambda _: "owner PID 12345")

    class Occupied:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def bind(self, _):
            raise OSError("address in use")

    monkeypatch.setattr(socket, "socket", lambda *_: Occupied())
    monkeypatch.setattr(
        inputs.pv,
        "kill_process_tree",
        lambda *_: pytest.fail("killed external process"),
    )
    with pytest.raises(ValueError, match="port-conflict.*owner PID 12345"):
        inputs.preflight({"e2e": ["AC-1"]})


def test_bundle_skips_explicit_child_only_after_authentic_stage_proof(
    monkeypatch, tmp_path
):
    import subprocess

    from harness.tools import product_verification as pv

    gates = {
        "child": {"command": ["child"]},
        "bundle": {"command": ["bundle"], "subsumption_contract": "contract.json"},
    }
    contract = {"sha256": "a" * 64, "stages": [{"gate": "child", "stage": "test"}]}
    monkeypatch.setattr(pv, "_configured_gates", lambda: gates)
    monkeypatch.setattr(
        pv,
        "_load_subsumption_contract",
        lambda g, *_: contract if g == "bundle" else None,
    )
    monkeypatch.setattr(pv, "_command", lambda g, *_: ([g], tmp_path, 1))
    calls = []
    proof = {
        "schema_version": 1,
        "owner_gate": "bundle",
        "contract_sha256": "a" * 64,
        "completed": [{"gate": "child", "stage": "test"}],
    }

    def run(command, **_):
        calls.append(command[0])
        return subprocess.CompletedProcess(
            command, 0, pv.SUBSUMPTION_PROOF_PREFIX + json.dumps(proof), ""
        )

    monkeypatch.setattr(pv, "_run_supervised_command", run)
    results = pv.run_gates({"child": ["AC-1"], "bundle": ["AC-1"]})
    assert calls == ["bundle"] and validator.passed(results)
    assert results[-1]["provenance"] == {"mode": "subsumed", "parent_gate": "bundle"}
    proof["completed"] = []
    calls.clear()
    results = pv.run_gates({"child": ["AC-1"], "bundle": ["AC-1"]})
    assert calls == ["bundle"] and not validator.passed(results)
    assert len(results) == 1


def test_failure_logs_and_bounded_artifacts_are_retained(tmp_path, monkeypatch):
    from harness.tools import product_verification as pv
    from harness.tools import run_artifacts

    monkeypatch.setattr(
        pv,
        "_configured_gates",
        lambda: {
            "fixture": {
                "command": [
                    "{python}",
                    "-c",
                    "print('AssertionError: fixture'); raise SystemExit(1)",
                ]
            }
        },
    )
    log_root = tmp_path / "local"
    results = pv.run_gates(
        {"fixture": ["AC-1"]}, execution_root=tmp_path, artifact_root=log_root
    )
    assert results[0]["result"]["failure"]["kind"] == "nonzero-exit"
    assert results[0]["result"]["failure"]["hint"] == "assertion"
    assert "AssertionError: fixture" in (log_root / "fixture/output.log").read_text()
    artifact = tmp_path / "apps/web/test-results/trace.zip"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"trace")
    run_artifacts.retain(tmp_path, log_root)
    assert (
        log_root / "artifacts/apps/web/test-results/trace.zip"
    ).read_bytes() == b"trace"
    monkeypatch.setattr(run_artifacts, "RUN_LIMIT", 1)
    run_artifacts.retain(tmp_path, log_root)
    assert "omitted" in (log_root / "omitted.txt").read_text()


@pytest.mark.parametrize("changed", ["head", "evidence"])
def test_close_rolls_back_if_inputs_change_during_post_checks(
    runtime, tmp_path, monkeypatch, changed
):
    source = tmp_path / "active.md"
    archive = tmp_path / "archive.md"
    event = tmp_path / "event.json"
    source.write_text("original")
    current = {"head": "a" * 40, "evidence": "b" * 64}
    monkeypatch.setattr(
        cli.product_verification, "head_commit", lambda: current["head"]
    )
    monkeypatch.setattr(cli, "_evidence_sha256", lambda _: current["evidence"])
    monkeypatch.setattr(
        cli,
        "_close_preflight",
        lambda _: [(TASK, archive, "original", event, "b" * 64)],
    )
    monkeypatch.setattr(cli.summarizer, "active_spec", lambda _: source)

    def close(*_a, **_k):
        archive.write_text("b" * 64)
        source.unlink()
        return archive, "original"

    def restore(_, text, path):
        source.write_text(text)
        path.unlink(missing_ok=True)

    monkeypatch.setattr(cli.summarizer, "close_spec", close)
    monkeypatch.setattr(cli.summarizer, "restore_spec", restore)

    def emit(*_a, **_k):
        event.write_text("b" * 64)
        return event, None

    monkeypatch.setattr(cli.events, "emit_event", emit)
    monkeypatch.setattr(cli.indexer, "write_indexes", list)

    def post_check():
        current[changed] = "changed"
        return [{"name": "assets", "status": "passed"}]

    monkeypatch.setattr(cli.validator, "run_close_checks", post_check)
    assert cli._close_tasks([TASK]) == 1
    assert source.read_text() == "original"
    assert (
        not archive.exists()
        and not event.exists()
        and not close_transaction.journal_path().exists()
    )


def test_close_asset_checks_never_load_collector(monkeypatch, tmp_path):
    checks = tmp_path / "checks"
    checks.mkdir()
    (checks / "module_coverage.py").write_text(
        "raise AssertionError('collector loaded')"
    )
    (checks / "history_integrity.py").write_text(
        "def run(context): return {'name': 'history-integrity', 'passed': True}"
    )
    monkeypatch.setattr(validator, "harness_root", lambda: tmp_path)
    monkeypatch.setattr(validator, "project_root", lambda: tmp_path)
    monkeypatch.setattr(
        validator,
        "load_config",
        lambda: {
            "verification": {
                "checks": "checks",
                "required_task_checks": ["module-coverage"],
            }
        },
    )
    assert validator.passed(validator.run_close_checks())
    assert not validator.passed(validator.run_checks())


def test_workspace_link_outputs_do_not_change_installed_dependency_identity(
    tmp_path, monkeypatch
):
    from harness.tools import isolated_verification

    root = tmp_path / "project"
    dependencies = root / "node_modules"
    workspace = root / "apps/web"
    workspace.mkdir(parents=True)
    dependencies.mkdir()
    (root / "package.json").write_text('{"workspaces":["apps/web"]}')
    monkeypatch.setattr(inputs, "project_root", lambda: root)
    link = dependencies / "workspace"
    isolated_verification._create_directory_link(workspace, link)
    try:
        baseline = inputs.tree_digest(dependencies)
        (workspace / "generated-output.js").write_text("random build output")
        assert inputs.tree_digest(dependencies) == baseline
        (dependencies / "installed.js").write_text("actual installed code")
        assert inputs.tree_digest(dependencies) != baseline
    finally:
        isolated_verification._remove_directory_link(link)


def test_invalidation_reasons_compare_canonical_mapping_values(runtime):
    prepared, _, _ = runtime
    prepared["snapshot"] = {"head": "new", "mappings": [("A", ["AC-1"])]}
    ledger = {
        "runs": [
            {
                "identity": "old",
                "inputs": {"head": "old", "mappings": [["A", ["AC-1"]]]},
                "attempts": [{"gate": "A"}],
            }
        ]
    }
    plan = resume.gate_plan(prepared, ledger)
    assert plan[0]["reason"] == "input identity changed: head"


def test_diagnostic_long_paths_preserve_bytes_limits_errors_and_pruning(tmp_path, monkeypatch):
    import os
    import shutil
    from pathlib import Path
    from harness.tools import run_artifacts as artifacts

    def native(path):
        # Independent setup/read oracle, including when system long paths are disabled.
        return Path("\\\\?\\" + str(path.absolute())) if os.name == "nt" else path

    root = tmp_path / "source"
    relative = Path("test-results") / ("nested-" + "a" * 95) / ("b" * 95) / "report.json"
    source = native(root / relative)
    source.parent.mkdir(parents=True)
    source.write_bytes(b'{"expected":1}')
    store = tmp_path / "store"
    destination = store / "artifacts" / ("run-" + "c" * 80)
    try:
        artifacts.retain(root, destination)
        assert native(destination / "artifacts" / relative).read_bytes() == source.read_bytes()
        capped = store / "artifacts" / "capped"
        monkeypatch.setattr(artifacts, "RUN_LIMIT", 1)
        artifacts.retain(root, capped)
        assert not native(capped / "artifacts" / relative).exists()
        assert "1 files omitted" in (capped / "omitted.txt").read_text()
        monkeypatch.setattr(artifacts, "RUN_LIMIT", 64 * 1024 * 1024)
        with monkeypatch.context() as context:
            def denied(*args, **kwargs):
                raise PermissionError("copy denied")
            context.setattr(artifacts.shutil, "copyfile", denied)
            with pytest.raises(PermissionError, match="copy denied"):
                artifacts.retain(root, store / "artifacts" / "denied")
        monkeypatch.setattr(run_store, "store_root", lambda: store)
        monkeypatch.setattr(artifacts, "RETENTION_SECONDS", -1)
        artifacts.prune()
        assert not destination.exists()
        assert source.read_bytes() == b'{"expected":1}'
    finally:
        shutil.rmtree(native(root))
        if store.exists():
            shutil.rmtree(native(store))
