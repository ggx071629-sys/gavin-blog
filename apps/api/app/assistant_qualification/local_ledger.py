"""Explicit local probe authorization; cumulative history never becomes a daily allowance."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from ..assistant.crypto import hmac_hex
from ..assistant.owner_lock import ExclusiveFileLock
from ..config import Settings
from . import provider_probe as probe


def run_lock(path: Path) -> ExclusiveFileLock:
    path = path.resolve()
    return ExclusiveFileLock(path.with_suffix(path.suffix + ".run.lock"))


def _guard(settings: Settings, path: Path) -> None:
    root = Path(probe.__file__).resolve().parents[2] / "data"
    if settings.environment != "development" or settings.assistant_online_enabled:
        raise probe.ProviderQualificationError(
            "local ledger operations require offline development"
        )
    if not path.resolve().is_relative_to(root):
        raise probe.ProviderQualificationError("local ledger must remain under API data")
    if len(settings.assistant_readiness_hmac_secret or "") < 32:
        raise probe.ProviderQualificationError("local ledger signing secret required")


def _signature(data: dict, settings: Settings) -> str:
    return hmac_hex(
        str(settings.assistant_readiness_hmac_secret),
        json.dumps(
            {k: v for k, v in data.items() if k != "ledger_hmac"},
            sort_keys=True,
            separators=(",", ":"),
        ),
        context="local-probe-ledger-v3",
    )


def _save(path: Path, data: dict, settings: Settings) -> None:
    data["ledger_hmac"] = _signature(data, settings)
    probe._atomic_json(path, data)


def _attempts(data: dict) -> list[dict]:
    return data["legacy"]["payload"]["attempts"] + [
        a for authorization in data["authorizations"] for a in authorization["attempts"]
    ]


def totals(data: dict) -> tuple[int, int]:
    attempts = _attempts(data)
    return sum(a["network_calls"] for a in attempts), sum(
        max(a["reserved_micro_cny"], a["settled_micro_cny"])
        if a["status"] in {"sending", "unknown"}
        else a["settled_micro_cny"]
        for a in attempts
    )


def _load(path: Path, settings: Settings) -> dict:
    data = probe._read_json(path)
    if data.get("schema_version") != 3:
        raise probe.ProviderQualificationError("authorize the legacy ledger before using an ID")
    if not hmac.compare_digest(str(data.get("ledger_hmac", "")), _signature(data, settings)):
        raise probe.ProviderQualificationError("local ledger signature mismatch")
    return data


def policy(path: Path, settings: Settings, authorization_id: str) -> dict:
    data = _load(path, settings)
    current = data["authorizations"][-1]
    if current["id"] != authorization_id:
        raise probe.ProviderQualificationError("authorization is not the active ID")
    return current


def _unresolved(data: dict) -> list[dict]:
    recovered = {r["attempt_id"] for r in data["recoveries"]}
    return [
        a
        for a in _attempts(data)
        if a["status"] != "succeeded" and a["attempt_id"] not in recovered
    ]


def _legacy(path: Path) -> dict:
    payload = probe._read_json(path)
    # Validate historical structure without pretending to reconstruct its old configuration.
    if payload.get("schema_version") != probe.LEDGER_SCHEMA_VERSION:
        raise probe.ProviderQualificationError("unsupported legacy ledger")
    required = {"schema_version", "profile_digest", "max_calls", "max_micro_cny", "attempts"}
    if set(payload) != required or not isinstance(payload["attempts"], list):
        raise probe.ProviderQualificationError("invalid legacy ledger")
    if payload["profile_digest"] and not payload["profile_digest"].startswith("local-sha256:"):
        raise probe.ProviderQualificationError("production ledger cannot become local")
    for key in ("max_calls", "max_micro_cny"):
        if type(payload[key]) is not int or payload[key] < 0:
            raise probe.ProviderQualificationError("invalid legacy limits")
    ids = set()
    for a in payload["attempts"]:
        if (
            not isinstance(a, dict)
            or set(a)
            != {
                "attempt_id",
                "kind",
                "network_calls",
                "beijing_date",
                "status",
                "reserved_micro_cny",
                "settled_micro_cny",
                "created_at",
                "settled_at",
            }
            or a.get("kind") != "chat"
            or a.get("status") not in {"sending", "unknown", "measured_fail", "succeeded"}
            or not isinstance(a.get("attempt_id"), str)
            or not a["attempt_id"]
            or a["attempt_id"] in ids
        ):
            raise probe.ProviderQualificationError("invalid legacy attempt")
        ids.add(a["attempt_id"])
        for key in ("network_calls", "reserved_micro_cny", "settled_micro_cny"):
            if type(a.get(key)) is not int or a[key] < (1 if key == "network_calls" else 0):
                raise probe.ProviderQualificationError("invalid legacy accounting")
    raw = path.read_bytes().decode("utf-8") if path.exists() else None
    return {
        "payload": payload,
        "original_text": raw,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if raw is not None else None,
    }


def authorize(
    *,
    settings: Settings,
    ledger_path: Path,
    authorization_id: str,
    max_calls: int,
    max_micro_cny: int,
    daily_budget: Decimal,
    reason: str,
) -> dict:
    _guard(settings, ledger_path)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", authorization_id) or not reason.strip():
        raise probe.ProviderQualificationError("authorization requires a unique ID and reason")
    contract = probe._local_chat_contract(
        settings=settings,
        approved_max_micro_cny=max_micro_cny,
        max_calls=max_calls,
        approved_daily_budget=daily_budget,
        authorization_id=authorization_id,
    )
    with run_lock(ledger_path):
        if probe._read_json(ledger_path).get("schema_version") == 3:
            data = _load(ledger_path, settings)
        else:
            data = {
                "schema_version": 3,
                "legacy": _legacy(ledger_path),
                "authorizations": [],
                "recoveries": [],
            }
        binding = probe._probe_digest(contract)
        for old in data["authorizations"]:
            if old["id"] == authorization_id:
                if (
                    old is not data["authorizations"][-1]
                    or old["contract_digest"] != binding
                    or old["daily_budget_cny"] != str(daily_budget)
                ):
                    raise probe.ProviderQualificationError(
                        "authorization ID cannot be replayed or changed"
                    )
                return status_data(data)
        prior = data["authorizations"][-1] if data["authorizations"] else data["legacy"]["payload"]
        calls, cost = totals(data)
        if max_calls < max(prior["max_calls"], calls) or max_micro_cny < max(
            prior["max_micro_cny"], cost
        ):
            raise probe.ProviderQualificationError(
                "cumulative authorization cannot discard previous limits or spend"
            )
        data["authorizations"].append(
            {
                "id": authorization_id,
                "created_at": datetime.now(UTC).isoformat(),
                "reason": reason.strip(),
                "max_calls": max_calls,
                "max_micro_cny": max_micro_cny,
                "daily_budget_cny": str(daily_budget),
                "contract_digest": binding,
                "contract": asdict(contract),
                "attempts": [],
            }
        )
        _save(ledger_path, data, settings)
        return status_data(data)


def status_data(data: dict) -> dict:
    calls, cost = totals(data)
    current = data["authorizations"][-1]
    return {
        "authorization_id": current["id"],
        "calls_used": calls,
        "micro_cny_used": cost,
        "calls_remaining": max(0, current["max_calls"] - calls),
        "micro_cny_remaining": max(0, current["max_micro_cny"] - cost),
        "unresolved": [
            {"attempt_id": a["attempt_id"], "status": a["status"]} for a in _unresolved(data)
        ],
    }


def status(*, settings: Settings, ledger_path: Path) -> dict:
    _guard(settings, ledger_path)
    if probe._read_json(ledger_path).get("schema_version") != 3:
        legacy = _legacy(ledger_path)["payload"]
        calls, cost = probe._totals(legacy)
        return {
            "schema_version": 2,
            "calls_used": calls,
            "micro_cny_used": cost,
            "next": "explicit authorize imports history; no probe is performed",
        }
    return status_data(_load(ledger_path, settings))


def recover(
    *, settings: Settings, ledger_path: Path, attempt_id: str, confirm_quiescent: bool, reason: str
) -> dict:
    _guard(settings, ledger_path)
    if not confirm_quiescent or not reason.strip():
        raise probe.ProviderQualificationError(
            "recovery requires quiescence confirmation and reason"
        )
    with run_lock(ledger_path):
        data = _load(ledger_path, settings)
        match = [a for a in _attempts(data) if a["attempt_id"] == attempt_id]
        if len(match) != 1 or match[0]["status"] == "succeeded":
            raise probe.ProviderQualificationError("recovery needs a failed or unfinished attempt")
        if not any(r["attempt_id"] == attempt_id for r in data["recoveries"]):
            data["recoveries"].append(
                {
                    "attempt_id": attempt_id,
                    "reason": reason.strip(),
                    "confirmed_quiescent_at": datetime.now(UTC).isoformat(),
                    "accounting": "original facts retained; unknown at reservation",
                }
            )
            _save(ledger_path, data, settings)
        return status_data(data)


def reserve(
    path: Path,
    settings: Settings,
    contract,
    *,
    network_calls: int,
    reserved_micro_cny: int,
    now: datetime,
) -> str:
    data = _load(path, settings)
    current = data["authorizations"][-1]
    if current["id"] != contract.authorization_id or current[
        "contract_digest"
    ] != probe._probe_digest(contract):
        raise probe.ProviderQualificationError("local authorization configuration mismatch")
    if _unresolved(data):
        raise probe.ProviderQualificationError(
            "recover unresolved or failed attempts before probing"
        )
    calls, cost = totals(data)
    if calls + network_calls > current["max_calls"]:
        raise probe.ProviderQualificationError(
            "cumulative call envelope exhausted; explicit authorization required"
        )
    if cost + reserved_micro_cny > current["max_micro_cny"]:
        raise probe.ProviderQualificationError(
            "cumulative cost envelope exhausted; explicit authorization required"
        )
    attempt_id = str(uuid.uuid4())
    current["attempts"].append(
        {
            "attempt_id": attempt_id,
            "kind": "chat",
            "network_calls": network_calls,
            "beijing_date": now.astimezone(probe.BEIJING_TZ).date().isoformat(),
            "status": "sending",
            "reserved_micro_cny": reserved_micro_cny,
            "settled_micro_cny": reserved_micro_cny,
            "created_at": now.isoformat(),
            "settled_at": None,
        }
    )
    _save(path, data, settings)
    return attempt_id


def settle(
    path: Path,
    settings: Settings,
    contract,
    *,
    attempt_id: str,
    status: str,
    settled_micro_cny: int,
    now: datetime,
) -> None:
    data = _load(path, settings)
    current = data["authorizations"][-1]
    matches = [a for a in current["attempts"] if a["attempt_id"] == attempt_id]
    if (
        current["id"] != contract.authorization_id
        or len(matches) != 1
        or matches[0]["status"] != "sending"
        or any(r["attempt_id"] == attempt_id for r in data["recoveries"])
    ):
        raise probe.ProviderQualificationError(
            "attempt cannot be settled after recovery or authorization change"
        )
    attempt = matches[0]
    attempt.update(
        status=status, settled_micro_cny=max(0, settled_micro_cny), settled_at=now.isoformat()
    )
    if totals(data)[1] > current["max_micro_cny"]:
        attempt["status"] = "measured_fail"
    _save(path, data, settings)
