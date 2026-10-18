from __future__ import annotations

import json
from decimal import Decimal

import pytest

from app.assistant.crypto import hmac_hex
from app.assistant_qualification import provider_probe as probe

from .test_assistant_provider_qualification import _local_probe_inputs


def test_compatibility_is_independent_of_cost(tmp_path, monkeypatch):
    args, calls = _local_probe_inputs(tmp_path, monkeypatch)
    result = probe.run_local_chat_probe(**args)
    original = args["output_path"].read_bytes()
    changed = args["settings"].model_copy(
        update={
            "assistant_chat_input_price_cny_per_million": Decimal("8"),
            "assistant_chat_daily_budget_cny": Decimal("1"),
        }
    )
    assert (
        probe.validate_local_chat_probe_artifact(args["output_path"], changed)["completed_at"]
        == result["completed_at"]
    )
    for field, value in [
        ("assistant_chat_api_key", "changed"),
        ("assistant_chat_endpoint", "https://api.deepseek.com/v1"),
        ("assistant_chat_max_output_tokens", 500),
        ("assistant_provider_timeout_seconds", 44),
        ("assistant_chat_daily_budget_cny", Decimal("3")),
    ]:
        with pytest.raises(probe.ProviderQualificationError):
            probe.validate_local_chat_probe_artifact(
                args["output_path"], changed.model_copy(update={field: value})
            )
    monkeypatch.setattr("app.assistant.readiness._schema_hash", lambda: "changed-schema")
    with pytest.raises(probe.ProviderQualificationError):
        probe.validate_local_chat_probe_artifact(args["output_path"], changed)
    assert len(calls) == 1 and args["output_path"].read_bytes() == original


def test_legacy_conversion_preserves_evidence(tmp_path, monkeypatch):
    args, calls = _local_probe_inputs(tmp_path, monkeypatch)
    payload = probe.run_local_chat_probe(**args)
    for key in ["probe_hmac", "compatibility_digest", "approved_daily_budget_cny"]:
        payload.pop(key)
    payload["schema_version"] = 1
    payload["probe_hmac"] = hmac_hex(
        str(args["settings"].assistant_readiness_hmac_secret),
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
        context="local-chat-probe-artifact-v1",
    )
    args["output_path"].write_text(json.dumps(payload))
    original = args["output_path"].read_bytes()
    output = tmp_path / "converted.json"
    changed = args["settings"].model_copy(
        update={"assistant_chat_input_price_cny_per_million": Decimal("8")}
    )
    with pytest.raises(probe.ProviderQualificationError):
        probe.migrate_local_chat_evidence(args["output_path"], output, changed)
    converted = probe.migrate_local_chat_evidence(args["output_path"], output, args["settings"])
    assert converted["legacy_evidence"] == payload
    assert converted["completed_at"] == payload["completed_at"]
    probe.validate_local_chat_probe_artifact(output, changed)
    with pytest.raises(probe.ProviderQualificationError):
        probe.migrate_local_chat_evidence(
            args["output_path"], args["output_path"], args["settings"]
        )
    assert len(calls) == 1 and args["output_path"].read_bytes() == original


def _authorize(args, name="review-1", calls=2, cost=1_000_000, daily="2"):
    from app.assistant_qualification import local_ledger

    return local_ledger.authorize(
        settings=args["settings"],
        ledger_path=args["ledger_path"],
        authorization_id=name,
        max_calls=calls,
        max_micro_cny=cost,
        daily_budget=Decimal(daily),
        reason="synthetic reviewed authorization",
    )


def test_cumulative_authorization_preserves_history_and_replay(tmp_path, monkeypatch):
    from app.assistant_qualification import local_ledger

    args, calls = _local_probe_inputs(tmp_path, monkeypatch)
    probe.run_local_chat_probe(**args)
    original = args["ledger_path"].read_bytes()
    assert _authorize(args)["calls_used"] == 1
    signed = args["ledger_path"].read_bytes()
    assert _authorize(args)["calls_used"] == 1
    assert args["ledger_path"].read_bytes() == signed
    data = json.loads(signed)
    assert data["legacy"]["original_text"].encode() == original
    assert data["legacy"]["payload"] == json.loads(original)
    run = {
        **args,
        "authorization_id": "review-1",
        "max_calls": 2,
        "output_path": tmp_path / "data/new-probe.json",
    }
    result = probe.run_local_chat_probe(**run)
    assert result["ledger"]["calls_used"] == 2
    assert result["ledger"]["micro_cny_used"] == 1080
    with pytest.raises(probe.ProviderQualificationError, match="call envelope"):
        probe.run_local_chat_probe(**{**run, "output_path": tmp_path / "data/third.json"})
    with pytest.raises(probe.ProviderQualificationError, match="replayed or changed"):
        _authorize(args, calls=3)
    _authorize(args, name="review-2", calls=2)
    with pytest.raises(probe.ProviderQualificationError, match="active ID"):
        probe.run_local_chat_probe(**{**run, "output_path": tmp_path / "data/old-id.json"})
    assert (
        local_ledger.status(settings=args["settings"], ledger_path=args["ledger_path"])[
            "calls_remaining"
        ]
        == 0
    )
    assert len(calls) == 2


@pytest.mark.parametrize("state", ["sending", "unknown", "measured_fail"])
def test_recovery_preserves_failed_facts_and_remaining_budget(tmp_path, monkeypatch, state):
    from app.assistant_qualification import local_ledger

    args, calls = _local_probe_inputs(tmp_path, monkeypatch, usage=False)
    probe.run_local_chat_probe(**args)
    legacy = json.loads(args["ledger_path"].read_text())
    legacy["attempts"][0]["status"] = state
    legacy["attempts"][0]["settled_micro_cny"] = 0 if state in {"sending", "unknown"} else 28000
    args["ledger_path"].write_text(json.dumps(legacy))
    status = _authorize(args)
    attempt = legacy["attempts"][0]
    charged = (
        max(attempt["reserved_micro_cny"], attempt["settled_micro_cny"])
        if state != "measured_fail"
        else 28000
    )
    assert status["micro_cny_used"] == charged
    run = {
        **args,
        "authorization_id": "review-1",
        "max_calls": 2,
        "output_path": tmp_path / "data/retry.json",
    }
    with pytest.raises(probe.ProviderQualificationError, match="unresolved"):
        probe.run_local_chat_probe(**run)
    with pytest.raises(probe.ProviderQualificationError, match="quiescence"):
        local_ledger.recover(
            settings=args["settings"],
            ledger_path=args["ledger_path"],
            attempt_id=attempt["attempt_id"],
            confirm_quiescent=False,
            reason="investigated",
        )
    kwargs = dict(
        settings=args["settings"],
        ledger_path=args["ledger_path"],
        attempt_id=attempt["attempt_id"],
        confirm_quiescent=True,
        reason="transport stopped; reserve retained",
    )
    recovered = local_ledger.recover(**kwargs)
    assert not recovered["unresolved"] and recovered["micro_cny_used"] == charged
    original = args["ledger_path"].read_bytes()
    local_ledger.recover(**kwargs)
    assert original == args["ledger_path"].read_bytes()
    assert json.loads(original)["legacy"]["payload"] == legacy
    assert len(calls) == 1
    probe.run_local_chat_probe(**run)
    assert len(calls) == 2
    assert (
        local_ledger.status(settings=args["settings"], ledger_path=args["ledger_path"])[
            "calls_used"
        ]
        == 2
    )


def test_cost_exhaustion_lock_and_tamper_fail_closed(tmp_path, monkeypatch):
    from app.assistant.errors import AssistantOwnerLockError
    from app.assistant_qualification import local_ledger

    args, calls = _local_probe_inputs(tmp_path, monkeypatch)
    _authorize(args, cost=1)
    run = {**args, "authorization_id": "review-1", "max_calls": 2, "approved_max_micro_cny": 1}
    with pytest.raises(probe.ProviderQualificationError, match="cost envelope"):
        probe.run_local_chat_probe(**run)
    with local_ledger.run_lock(args["ledger_path"]):
        with pytest.raises(AssistantOwnerLockError):
            _authorize(args, name="other")
        with pytest.raises(AssistantOwnerLockError):
            probe.run_local_chat_probe(**run)
        with pytest.raises(AssistantOwnerLockError):
            local_ledger.recover(
                settings=args["settings"],
                ledger_path=args["ledger_path"],
                attempt_id="x",
                confirm_quiescent=True,
                reason="investigated",
            )
    _authorize(args, name="review-2", cost=1_000_000)
    probe.run_local_chat_probe(
        **{**run, "authorization_id": "review-2", "approved_max_micro_cny": 1_000_000}
    )
    data = json.loads(args["ledger_path"].read_text())
    data["authorizations"][-1]["attempts"] = []
    args["ledger_path"].write_text(json.dumps(data))
    with pytest.raises(probe.ProviderQualificationError, match="signature"):
        local_ledger.status(settings=args["settings"], ledger_path=args["ledger_path"])
    assert len(calls) == 1


def test_cli_offline_operations_never_probe(tmp_path, monkeypatch, capsys):
    from scripts import run_assistant_provider_qualification as cli

    args, calls = _local_probe_inputs(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "get_settings", lambda: args["settings"])

    def forbidden(**kwargs):
        raise AssertionError("offline action must not probe")

    monkeypatch.setattr(cli, "run_local_chat_probe", forbidden)
    base = ["--local-chat", "--ledger", str(args["ledger_path"])]
    assert cli.main(base + ["--local-action", "status"]) == 0
    assert (
        cli.main(
            base
            + [
                "--local-action",
                "authorize",
                "--authorization-id",
                "cli-1",
                "--approve-max-micro-cny",
                "1000000",
                "--max-calls",
                "2",
                "--approve-daily-budget-cny",
                "2",
                "--reason",
                "synthetic approval",
            ]
        )
        == 0
    )
    assert cli.main(base + ["--local-action", "status"]) == 0
    with pytest.raises(SystemExit):
        cli.main(base + ["--local-action", "recover"])
    with pytest.raises(SystemExit):
        cli.main(["--ledger", str(args["ledger_path"]), "--local-action", "status"])
    assert not calls
    assert "synthetic-private" not in capsys.readouterr().out


def test_daily_budget_reauthorization_is_offline(tmp_path, monkeypatch):
    from app.assistant_qualification import local_ledger

    args, calls = _local_probe_inputs(tmp_path, monkeypatch)
    result = probe.run_local_chat_probe(**args)
    original = args["output_path"].read_bytes()
    args["settings"] = args["settings"].model_copy(
        update={"assistant_chat_daily_budget_cny": Decimal("3")}
    )
    with pytest.raises(probe.ProviderQualificationError):
        probe.validate_local_chat_probe_artifact(args["output_path"], args["settings"])
    _authorize(args, daily="3")
    output = tmp_path / "data/new-cost-policy.json"
    bound = probe.rebind_local_chat_costs(
        args["output_path"], output, args["settings"], args["ledger_path"], "review-1"
    )
    probe.validate_local_chat_probe_artifact(output, args["settings"])
    assert bound["completed_at"] == result["completed_at"]
    assert bound["previous_evidence"] == json.loads(original)
    assert args["output_path"].read_bytes() == original
    assert (
        local_ledger.status(settings=args["settings"], ledger_path=args["ledger_path"])[
            "calls_used"
        ]
        == 1
    )
    assert len(calls) == 1
    drift = args["settings"].model_copy(update={"assistant_chat_api_key": "new-key"})
    _authorize({**args, "settings": drift}, name="review-2", daily="3")
    with pytest.raises(probe.ProviderQualificationError):
        probe.rebind_local_chat_costs(
            args["output_path"],
            tmp_path / "data/invalid.json",
            drift,
            args["ledger_path"],
            "review-2",
        )
    assert len(calls) == 1


def test_changed_costs_resign_runtime_receipt_without_probe(tmp_path, monkeypatch):
    import sqlite3

    from app.assistant.development import build_real_development_settings
    from app.assistant.errors import AssistantNotReadyError
    from app.assistant.provisioning import provision_runtime
    from app.assistant.readiness import verify_receipt, write_receipt
    from app.db import Base, Database

    from .test_assistant_real_development import _inputs

    args, calls = _inputs(tmp_path, monkeypatch)
    settings = build_real_development_settings(**args)
    database = Database(settings.database_url)
    Base.metadata.create_all(database.engine)
    database.engine.dispose()
    provision_runtime(settings)
    write_receipt(
        settings, probe_live=True, provider_probe=args["probe_path"], local_development=True
    )
    args["chat"] = args["chat"].model_copy(
        update={
            "assistant_chat_input_price_cny_per_million": Decimal("8"),
            "assistant_chat_daily_budget_cny": Decimal("1"),
        }
    )
    changed = build_real_development_settings(**args)
    with sqlite3.connect(settings.assistant_runtime_path) as conn:
        conn.row_factory = sqlite3.Row
        with pytest.raises(AssistantNotReadyError):
            verify_receipt(changed, conn)
    write_receipt(
        changed, probe_live=True, provider_probe=args["probe_path"], local_development=True
    )
    with sqlite3.connect(settings.assistant_runtime_path) as conn:
        conn.row_factory = sqlite3.Row
        verify_receipt(changed, conn)
    assert len(calls) == 1
