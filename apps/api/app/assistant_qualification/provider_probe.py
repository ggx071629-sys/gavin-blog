from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from ..assistant.constants import BEIJING_TZ
from ..assistant.crypto import hmac_hex
from ..assistant.graph import _usage_from_raw
from ..assistant.money import cny_to_micro
from ..assistant.owner_lock import ExclusiveFileLock
from ..assistant.prompt import estimate_tokens
from ..assistant.providers import (
    EmbeddingUsage,
    MeteredEmbeddings,
    ModelAnswer,
    bind_answer_model,
    build_chat_model,
    build_metered_embeddings,
)
from ..config import Settings
from .profile import QualificationProfile, load_profile, profile_digest

PROBE_SCHEMA_VERSION = 2
LEDGER_SCHEMA_VERSION = 2


class ProviderQualificationError(RuntimeError):
    """A fail-closed qualification precondition or evidence error."""


@dataclass(frozen=True)
class LocalChatProbeContract:
    """Local budget/identity binding, deliberately not a production profile."""

    model: str
    model_version: str
    max_input_tokens: int
    max_output_tokens: int
    context_window_tokens: int
    input_price_micro_cny_per_million: int
    output_price_micro_cny_per_million: int
    max_calls: int
    max_micro_cny: int
    timeout_seconds: int
    credential_binding: str
    model_identity_source: str = "versioned-provider-contract"
    scope: str = "local-development-chat"
    authorization_id: str | None = None


ProbeContract = QualificationProfile | LocalChatProbeContract


def _probe_digest(profile: ProbeContract) -> str:
    if isinstance(profile, LocalChatProbeContract):
        fields = asdict(profile)
        if fields["authorization_id"] is None:
            del fields["authorization_id"]  # Preserve legacy ledger digests exactly.
        canonical = json.dumps(fields, sort_keys=True, separators=(",", ":"))
        return "local-sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
    return profile_digest(profile)


def _probe_limits(profile: ProbeContract) -> tuple[int, int]:
    if isinstance(profile, LocalChatProbeContract):
        return profile.max_calls, profile.max_micro_cny
    budgets = profile.providers.budgets
    return budgets.qualification_max_calls, budgets.qualification_max_micro_cny


def provider_probe_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def validate_provider_probe_artifact(
    path: Path,
    profile: QualificationProfile,
    settings: Settings,
) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProviderQualificationError("provider probe artifact is unreadable") from exc
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "profile_digest",
        "real_provider",
        "started_at",
        "completed_at",
        "beijing_date",
        "endpoint_binding_hmac",
        "chat",
        "embedding",
        "ledger",
        "content_retained",
        "raw_provider_payload_retained",
    }:
        raise ProviderQualificationError("provider probe artifact fields are invalid")
    if payload["schema_version"] != PROBE_SCHEMA_VERSION:
        raise ProviderQualificationError("provider probe artifact schema is unsupported")
    if payload["profile_digest"] != profile_digest(profile):
        raise ProviderQualificationError("provider probe profile binding has drifted")
    if payload["real_provider"] is not True:
        raise ProviderQualificationError("provider probe did not use the final real provider")
    binding_secret = str(settings.assistant_readiness_hmac_secret or "")
    if len(binding_secret) < 32:
        raise ProviderQualificationError(
            "readiness HMAC secret is required to validate provider endpoint binding"
        )
    expected_endpoint_binding = {
        "chat": hmac_hex(
            binding_secret,
            str(settings.assistant_chat_endpoint),
            context="provider-probe-chat-endpoint-v1",
        ),
        "embedding": hmac_hex(
            binding_secret,
            str(settings.assistant_embedding_endpoint),
            context="provider-probe-embedding-endpoint-v1",
        ),
    }
    if payload["endpoint_binding_hmac"] != expected_endpoint_binding:
        raise ProviderQualificationError("provider endpoint binding has drifted")
    if (
        payload["content_retained"] is not False
        or payload["raw_provider_payload_retained"] is not False
    ):
        raise ProviderQualificationError("provider probe retained forbidden content")
    chat = payload["chat"]
    embedding = payload["embedding"]
    ledger = payload["ledger"]
    if (
        not isinstance(chat, dict)
        or not isinstance(embedding, dict)
        or not isinstance(ledger, dict)
    ):
        raise ProviderQualificationError("provider probe is incomplete")
    if chat.get("status") != "pass" or embedding.get("status") != "pass":
        raise ProviderQualificationError("provider probe contains a measured failure")
    if (
        not chat.get("usage_proven")
        or chat.get("finish_reason") != "stop"
        or not chat.get("strict_schema")
    ):
        raise ProviderQualificationError("Chat provider contract is not proven")
    if not embedding.get("usage_proven") or not embedding.get("finite_vectors"):
        raise ProviderQualificationError("Embedding provider contract is not proven")
    if (
        chat.get("model_identity_source") == "operator-declaration"
        or chat.get("version_identity_source") == "operator-declaration"
    ):
        raise ProviderQualificationError("Chat model identity is only an operator declaration")
    if (
        embedding.get("model_identity_source") == "operator-declaration"
        or embedding.get("version_identity_source") == "operator-declaration"
    ):
        raise ProviderQualificationError("Embedding model identity is only an operator declaration")
    if ledger.get("within_envelope") is not True:
        raise ProviderQualificationError("provider qualification envelope was exceeded")
    if (
        chat.get("model") != profile.providers.chat.model
        or chat.get("version") != profile.providers.chat.model_version
    ):
        raise ProviderQualificationError("Chat model identity drifted from profile")
    if (
        embedding.get("model") != profile.providers.embedding.model
        or embedding.get("version") != profile.providers.embedding.model_version
    ):
        raise ProviderQualificationError("Embedding model identity drifted from profile")
    if embedding.get("dimension") != profile.providers.embedding.dimension:
        raise ProviderQualificationError("Embedding dimension drifted from profile")
    return payload


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": LEDGER_SCHEMA_VERSION,
            "profile_digest": "",
            "max_calls": 0,
            "max_micro_cny": 0,
            "attempts": [],
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProviderQualificationError("qualification ledger is unreadable") from exc
    if not isinstance(payload, dict):
        raise ProviderQualificationError("qualification ledger root must be an object")
    return payload


def _validate_ledger(payload: dict[str, Any], profile: ProbeContract) -> None:
    if set(payload) != {
        "schema_version",
        "profile_digest",
        "max_calls",
        "max_micro_cny",
        "attempts",
    }:
        raise ProviderQualificationError("qualification ledger fields are invalid")
    if payload["schema_version"] != LEDGER_SCHEMA_VERSION:
        raise ProviderQualificationError("qualification ledger schema is unsupported")
    expected = _probe_digest(profile)
    if payload["profile_digest"] not in {"", expected}:
        raise ProviderQualificationError("qualification ledger belongs to another profile")
    max_calls, max_cost = _probe_limits(profile)
    if payload["max_calls"] not in {0, max_calls}:
        raise ProviderQualificationError("qualification call envelope has drifted")
    if payload["max_micro_cny"] not in {0, max_cost}:
        raise ProviderQualificationError("qualification cost envelope has drifted")
    if not isinstance(payload["attempts"], list):
        raise ProviderQualificationError("qualification ledger attempts must be an array")
    for attempt in payload["attempts"]:
        if not isinstance(attempt, dict) or set(attempt) != {
            "attempt_id",
            "kind",
            "network_calls",
            "beijing_date",
            "status",
            "reserved_micro_cny",
            "settled_micro_cny",
            "created_at",
            "settled_at",
        }:
            raise ProviderQualificationError("qualification ledger attempt is invalid")
        if attempt["kind"] not in {"chat", "embedding"}:
            raise ProviderQualificationError("qualification ledger kind is invalid")
        if not isinstance(attempt["network_calls"], int) or attempt["network_calls"] < 1:
            raise ProviderQualificationError("qualification ledger network_calls is invalid")
        if attempt["status"] not in {"sending", "succeeded", "measured_fail", "unknown"}:
            raise ProviderQualificationError("qualification ledger status is invalid")
        if not isinstance(attempt["reserved_micro_cny"], int) or not isinstance(
            attempt["settled_micro_cny"], int
        ):
            raise ProviderQualificationError("qualification ledger costs must be integers")


def _totals(payload: dict[str, Any]) -> tuple[int, int]:
    attempts = payload["attempts"]
    return sum(int(item["network_calls"]) for item in attempts), sum(
        max(int(item["reserved_micro_cny"]), int(item["settled_micro_cny"]))
        if item["status"] == "sending"
        else int(item["settled_micro_cny"])
        for item in attempts
    )


def _reserve(
    ledger_path: Path,
    profile: ProbeContract,
    *,
    kind: str,
    network_calls: int = 1,
    reserved_micro_cny: int,
    now: datetime,
    settings: Settings | None = None,
) -> str:
    if isinstance(profile, LocalChatProbeContract) and profile.authorization_id:
        if settings is None:
            raise ProviderQualificationError("authorized local ledger requires runtime settings")
        from . import local_ledger

        return local_ledger.reserve(
            ledger_path,
            settings,
            profile,
            network_calls=network_calls,
            reserved_micro_cny=reserved_micro_cny,
            now=now,
        )
    lock = ExclusiveFileLock(ledger_path.with_suffix(ledger_path.suffix + ".lock"))
    with lock:
        payload = _read_json(ledger_path)
        _validate_ledger(payload, profile)
        if isinstance(profile, LocalChatProbeContract) and any(
            attempt["status"] != "succeeded" for attempt in payload["attempts"]
        ):
            raise ProviderQualificationError("local probe has an unresolved or failed attempt")
        max_calls, max_cost = _probe_limits(profile)
        payload["profile_digest"] = _probe_digest(profile)
        payload["max_calls"] = max_calls
        payload["max_micro_cny"] = max_cost
        calls, cost = _totals(payload)
        if calls + network_calls > max_calls:
            raise ProviderQualificationError("qualification call envelope is exhausted")
        if cost + reserved_micro_cny > max_cost:
            raise ProviderQualificationError("qualification cost envelope is exhausted")
        attempt_id = str(uuid.uuid4())
        payload["attempts"].append(
            {
                "attempt_id": attempt_id,
                "kind": kind,
                "network_calls": network_calls,
                "beijing_date": now.astimezone(BEIJING_TZ).date().isoformat(),
                "status": "sending",
                "reserved_micro_cny": reserved_micro_cny,
                "settled_micro_cny": reserved_micro_cny,
                "created_at": now.astimezone(UTC).isoformat(),
                "settled_at": None,
            }
        )
        _atomic_json(ledger_path, payload)
        return attempt_id


def _settle(
    ledger_path: Path,
    profile: ProbeContract,
    *,
    attempt_id: str,
    status: str,
    settled_micro_cny: int,
    now: datetime,
    settings: Settings | None = None,
) -> None:
    if isinstance(profile, LocalChatProbeContract) and profile.authorization_id:
        if settings is None:
            raise ProviderQualificationError("authorized local ledger requires runtime settings")
        from . import local_ledger

        local_ledger.settle(
            ledger_path,
            settings,
            profile,
            attempt_id=attempt_id,
            status=status,
            settled_micro_cny=settled_micro_cny,
            now=now,
        )
        return
    lock = ExclusiveFileLock(ledger_path.with_suffix(ledger_path.suffix + ".lock"))
    with lock:
        payload = _read_json(ledger_path)
        _validate_ledger(payload, profile)
        match = [item for item in payload["attempts"] if item["attempt_id"] == attempt_id]
        if len(match) != 1 or match[0]["status"] != "sending":
            raise ProviderQualificationError("qualification attempt cannot be settled")
        attempt = match[0]
        attempt["status"] = status
        attempt["settled_micro_cny"] = max(
            int(settled_micro_cny),
            0,
        )
        attempt["settled_at"] = now.astimezone(UTC).isoformat()
        if _totals(payload)[1] > int(payload["max_micro_cny"]):
            attempt["status"] = "measured_fail"
        _atomic_json(ledger_path, payload)


def _micro_cost(tokens: int, price_micro_cny_per_million: int) -> int:
    if tokens <= 0 or price_micro_cny_per_million <= 0:
        return 0
    return (tokens * price_micro_cny_per_million + 999_999) // 1_000_000


def _settings_price(value: Decimal | None, label: str) -> int:
    if value is None:
        raise ProviderQualificationError(f"{label} is missing from runtime settings")
    return cny_to_micro(value)


def _validate_settings(settings: Settings, profile: QualificationProfile) -> None:
    if settings.environment != "production":
        raise ProviderQualificationError("real provider qualification requires production mode")
    if settings.assistant_online_enabled or settings.assistant_index_worker_enabled:
        raise ProviderQualificationError(
            "provider qualification requires API capability and index Worker switches off"
        )
    chat = profile.providers.chat
    embedding = profile.providers.embedding
    expected: tuple[tuple[Any, Any, str], ...] = (
        (settings.assistant_chat_provider, chat.protocol, "Chat protocol"),
        (settings.assistant_chat_model, chat.model, "Chat model"),
        (settings.assistant_chat_model_version, chat.model_version, "Chat model version"),
        (settings.assistant_chat_max_input_tokens, chat.max_input_tokens, "Chat input cap"),
        (settings.assistant_chat_max_output_tokens, chat.max_output_tokens, "Chat output cap"),
        (
            settings.assistant_chat_context_window_tokens,
            chat.context_window_tokens,
            "Chat context window",
        ),
        (settings.assistant_provider_timeout_seconds, chat.timeout_seconds, "provider timeout"),
        (settings.assistant_embedding_provider, embedding.protocol, "Embedding protocol"),
        (settings.assistant_embedding_model, embedding.model, "Embedding model"),
        (
            settings.assistant_embedding_model_version,
            embedding.model_version,
            "Embedding model version",
        ),
        (
            settings.assistant_embedding_dimension,
            embedding.dimension,
            "Embedding dimension",
        ),
        (
            settings.assistant_embedding_max_batch_items,
            embedding.max_batch_items,
            "Embedding batch cap",
        ),
    )
    for actual, configured, label in expected:
        if actual != configured:
            raise ProviderQualificationError(f"{label} does not match the approved profile")
    prices = (
        (
            settings.assistant_chat_input_price_cny_per_million,
            chat.input_price_micro_cny_per_million,
            "Chat input price",
        ),
        (
            settings.assistant_chat_output_price_cny_per_million,
            chat.output_price_micro_cny_per_million,
            "Chat output price",
        ),
        (
            settings.assistant_embedding_input_price_cny_per_million,
            embedding.input_price_micro_cny_per_million,
            "Embedding input price",
        ),
        (
            settings.assistant_chat_daily_budget_cny,
            profile.providers.budgets.chat_daily_micro_cny,
            "Chat budget",
        ),
        (
            settings.assistant_query_embedding_daily_budget_cny,
            profile.providers.budgets.query_embedding_daily_micro_cny,
            "query Embedding budget",
        ),
        (
            settings.assistant_index_embedding_daily_budget_cny,
            profile.providers.budgets.index_embedding_daily_micro_cny,
            "index Embedding budget",
        ),
    )
    for actual, configured, label in prices:
        if _settings_price(actual, label) != configured:
            raise ProviderQualificationError(f"{label} does not match the approved profile")
    for field in (
        "assistant_chat_api_key",
        "assistant_chat_endpoint",
        "assistant_embedding_api_key",
        "assistant_embedding_endpoint",
    ):
        if not str(getattr(settings, field) or "").strip():
            raise ProviderQualificationError(f"{field} is required for the explicit probe")
    if len(str(settings.assistant_readiness_hmac_secret or "")) < 32:
        raise ProviderQualificationError(
            "assistant_readiness_hmac_secret is required for endpoint binding"
        )


def _identity_source(
    reported: str | None,
    reported_source: str | None,
    expected: str,
    approved_source: str,
) -> tuple[bool, str]:
    if reported and reported == expected and reported_source == "provider-response":
        return True, "provider-response"
    if approved_source == "versioned-provider-contract":
        return True, "versioned-provider-contract"
    return False, "operator-declaration"


def _chat_probe(
    settings: Settings,
    profile: ProbeContract,
    ledger_path: Path,
    now: Callable[[], datetime],
    factory: Callable[[Settings], Any],
) -> dict[str, Any]:
    local = isinstance(profile, LocalChatProbeContract)
    contract = profile if isinstance(profile, LocalChatProbeContract) else profile.providers.chat
    messages = [
        SystemMessage(
            content=(
                "Return only the requested strict structured object. "
                "Do not include credentials or private configuration."
            )
        ),
        HumanMessage(
            content=(
                "Return one block whose text is qualification-ok and whose "
                "citation_ids and supports arrays are empty."
            )
        ),
    ]
    chat = None
    if local:
        chat = factory(settings)
        count = estimate_tokens([(m.type, str(m.content)) for m in messages], chat)
        if count > contract.max_input_tokens:
            raise ProviderQualificationError("local probe prompt exceeds input budget")
    reservation = _micro_cost(
        contract.max_input_tokens,
        contract.input_price_micro_cny_per_million,
    ) + _micro_cost(
        contract.max_output_tokens,
        contract.output_price_micro_cny_per_million,
    )
    started = now()
    attempt_id = _reserve(
        ledger_path,
        profile,
        kind="chat",
        settings=settings,
        reserved_micro_cny=reservation,
        now=started,
    )
    try:
        bound = bind_answer_model(chat if chat is not None else factory(settings))
        result = bound.invoke(messages)
        raw = result.get("raw") if isinstance(result, dict) else None
        parsed = result.get("parsed") if isinstance(result, dict) else result
        parsing_error = result.get("parsing_error") if isinstance(result, dict) else None
        finish_reason, usage = _usage_from_raw(raw)
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        usage_known = isinstance(input_tokens, int) and isinstance(output_tokens, int)
        settled = (
            _micro_cost(input_tokens, contract.input_price_micro_cny_per_million)
            + _micro_cost(output_tokens, contract.output_price_micro_cny_per_million)
            if isinstance(input_tokens, int) and isinstance(output_tokens, int)
            else reservation
        )
        schema_valid = isinstance(parsed, ModelAnswer) and parsing_error is None
        model_ok, model_source = _identity_source(
            usage.get("model"),
            usage.get("model_identity_source"),
            contract.model,
            contract.model_identity_source,
        )
        version_ok, version_source = _identity_source(
            usage.get("model_version"),
            usage.get("model_version_identity_source"),
            contract.model_version,
            contract.model_identity_source,
        )
        passed = bool(
            schema_valid
            and usage_known
            and finish_reason == "stop"
            and model_ok
            and version_ok
            and settled <= reservation
        )
        if local:
            passed = bool(
                schema_valid and usage_known and finish_reason == "stop"
                and settled <= reservation
                and usage.get("model") == contract.model
                and isinstance(input_tokens, int)
                and isinstance(output_tokens, int)
                and isinstance(parsed, ModelAnswer)
                and input_tokens <= contract.max_input_tokens
                and output_tokens <= contract.max_output_tokens
                and parsed.model_dump()
                == {"blocks": [{"text": "qualification-ok", "citation_ids": [], "supports": []}]}
            )
        _settle(
            ledger_path,
            profile,
            attempt_id=attempt_id,
            status="succeeded" if passed else "measured_fail",
            settled_micro_cny=settled,
            settings=settings,
            now=now(),
        )
        return {
            "status": "pass" if passed else "measured_fail",
            "call_count": 1,
            "reserved_micro_cny": reservation,
            "settled_micro_cny": settled,
            "strict_schema": schema_valid and not local,
            **({"application_schema": schema_valid} if local else {}),
            "usage_proven": usage_known,
            "input_tokens": input_tokens if usage_known else None,
            "output_tokens": output_tokens if usage_known else None,
            "finish_reason": finish_reason,
            "model": contract.model,
            "version": contract.model_version,
            "model_identity_source": model_source,
            "version_identity_source": version_source,
            "response_model_match": bool(usage.get("model") == contract.model),
            "response_version_match": bool(usage.get("model_version") == contract.model_version),
            "error_type": None,
        }
    except Exception as exc:
        _settle(
            ledger_path,
            profile,
            attempt_id=attempt_id,
            status="unknown",
            settled_micro_cny=reservation,
            settings=settings,
            now=now(),
        )
        return {
            "status": "measured_fail",
            "call_count": 1,
            "reserved_micro_cny": reservation,
            "settled_micro_cny": reservation,
            "strict_schema": False,
            **({"application_schema": False} if local else {}),
            "usage_proven": False,
            "input_tokens": None,
            "output_tokens": None,
            "finish_reason": "unknown",
            "model": contract.model,
            "version": contract.model_version,
            "model_identity_source": "operator-declaration",
            "version_identity_source": "operator-declaration",
            "response_model_match": False,
            "response_version_match": False,
            "error_type": type(exc).__name__,
        }


def _embedding_probe(
    settings: Settings,
    profile: QualificationProfile,
    ledger_path: Path,
    now: Callable[[], datetime],
    factory: Callable[[Settings], MeteredEmbeddings],
) -> dict[str, Any]:
    contract = profile.providers.embedding
    network_calls = math.ceil(2 / contract.max_batch_items)
    reservation = _micro_cost(
        2 * contract.max_input_tokens,
        contract.input_price_micro_cny_per_million,
    )
    attempt_id = _reserve(
        ledger_path,
        profile,
        kind="embedding",
        network_calls=network_calls,
        reserved_micro_cny=reservation,
        now=now(),
    )
    try:
        usage: EmbeddingUsage = factory(settings).embed_documents_metered(
            ["qualification-vector-a", "qualification-vector-b"]
        )
        vectors_ok = bool(
            len(usage.vectors) == 2
            and all(len(vector) == contract.dimension for vector in usage.vectors)
            and all(math.isfinite(value) for vector in usage.vectors for value in vector)
        )
        embedding_tokens = usage.input_tokens
        usage_known = embedding_tokens is not None and embedding_tokens > 0
        settled = (
            _micro_cost(
                embedding_tokens,
                contract.input_price_micro_cny_per_million,
            )
            if embedding_tokens is not None and embedding_tokens > 0
            else reservation
        )
        model_ok, model_source = _identity_source(
            usage.model,
            usage.model_identity_source,
            contract.model,
            contract.model_identity_source,
        )
        version_ok, version_source = _identity_source(
            usage.version,
            usage.version_identity_source,
            contract.model_version,
            contract.model_identity_source,
        )
        passed = bool(
            vectors_ok and usage_known and model_ok and version_ok and settled <= reservation
        )
        _settle(
            ledger_path,
            profile,
            attempt_id=attempt_id,
            status="succeeded" if passed else "measured_fail",
            settled_micro_cny=settled,
            now=now(),
        )
        return {
            "status": "pass" if passed else "measured_fail",
            "call_count": network_calls,
            "reserved_micro_cny": reservation,
            "settled_micro_cny": settled,
            "usage_proven": usage_known,
            "input_tokens": usage.input_tokens if usage_known else None,
            "finite_vectors": vectors_ok,
            "vector_count": len(usage.vectors),
            "dimension": contract.dimension,
            "model": contract.model,
            "version": contract.model_version,
            "model_identity_source": model_source,
            "version_identity_source": version_source,
            "response_model_match": usage.model == contract.model,
            "response_version_match": usage.version == contract.model_version,
            "error_type": None,
        }
    except Exception as exc:
        _settle(
            ledger_path,
            profile,
            attempt_id=attempt_id,
            status="unknown",
            settled_micro_cny=reservation,
            now=now(),
        )
        return {
            "status": "measured_fail",
            "call_count": network_calls,
            "reserved_micro_cny": reservation,
            "settled_micro_cny": reservation,
            "usage_proven": False,
            "input_tokens": None,
            "finite_vectors": False,
            "vector_count": 0,
            "dimension": contract.dimension,
            "model": contract.model,
            "version": contract.model_version,
            "model_identity_source": "operator-declaration",
            "version_identity_source": "operator-declaration",
            "response_model_match": False,
            "response_version_match": False,
            "error_type": type(exc).__name__,
        }


def _inside_qualification_root(path: Path, profile: QualificationProfile) -> Path:
    root = Path(profile.storage.paths.qualification_root).resolve()
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ProviderQualificationError(
            "provider qualification artifacts must stay under qualification_root"
        )
    return resolved


def run_provider_probe(
    *,
    settings: Settings,
    profile: QualificationProfile,
    approved_profile_digest: str,
    ledger_path: Path,
    output_path: Path,
    probe_chat: bool,
    probe_embedding: bool,
    now: Callable[[], datetime] | None = None,
    chat_factory: Callable[[Settings], Any] = build_chat_model,
    embedding_factory: Callable[[Settings], MeteredEmbeddings] = build_metered_embeddings,
) -> dict[str, Any]:
    if not probe_chat and not probe_embedding:
        raise ProviderQualificationError("select at least one explicit provider probe")
    expected_digest = profile_digest(profile)
    if approved_profile_digest != expected_digest:
        raise ProviderQualificationError("explicit profile digest approval does not match")
    _validate_settings(settings, profile)
    ledger_path = _inside_qualification_root(ledger_path, profile)
    output_path = _inside_qualification_root(output_path, profile)
    clock = now or (lambda: datetime.now(UTC))
    started = clock().astimezone(UTC)
    chat = _chat_probe(settings, profile, ledger_path, clock, chat_factory) if probe_chat else None
    embedding = (
        _embedding_probe(settings, profile, ledger_path, clock, embedding_factory)
        if probe_embedding
        else None
    )
    ledger = _read_json(ledger_path)
    _validate_ledger(ledger, profile)
    calls, cost = _totals(ledger)
    completed = clock().astimezone(UTC)
    payload = {
        "schema_version": PROBE_SCHEMA_VERSION,
        "profile_digest": expected_digest,
        "real_provider": True,
        "started_at": started.isoformat(),
        "completed_at": completed.isoformat(),
        "beijing_date": completed.astimezone(BEIJING_TZ).date().isoformat(),
        "endpoint_binding_hmac": {
            "chat": hmac_hex(
                str(settings.assistant_readiness_hmac_secret),
                str(settings.assistant_chat_endpoint),
                context="provider-probe-chat-endpoint-v1",
            ),
            "embedding": hmac_hex(
                str(settings.assistant_readiness_hmac_secret),
                str(settings.assistant_embedding_endpoint),
                context="provider-probe-embedding-endpoint-v1",
            ),
        },
        "chat": chat,
        "embedding": embedding,
        "ledger": {
            "calls_used": calls,
            "micro_cny_used": cost,
            "max_calls": profile.providers.budgets.qualification_max_calls,
            "max_micro_cny": profile.providers.budgets.qualification_max_micro_cny,
            "within_envelope": bool(
                calls <= profile.providers.budgets.qualification_max_calls
                and cost <= profile.providers.budgets.qualification_max_micro_cny
            ),
        },
        "content_retained": False,
        "raw_provider_payload_retained": False,
    }
    _atomic_json(output_path, payload)
    return payload


def load_and_run(
    *,
    settings: Settings,
    profile_path: Path,
    approved_profile_digest: str,
    ledger_path: Path,
    output_path: Path,
    probe_chat: bool,
    probe_embedding: bool,
) -> dict[str, Any]:
    return run_provider_probe(
        settings=settings,
        profile=load_profile(profile_path),
        approved_profile_digest=approved_profile_digest,
        ledger_path=ledger_path,
        output_path=output_path,
        probe_chat=probe_chat,
        probe_embedding=probe_embedding,
    )


def _local_chat_contract(
    *,
    settings: Settings,
    approved_max_micro_cny: int,
    max_calls: int,
    approved_daily_budget: Decimal = Decimal("2"),
    authorization_id: str | None = None,
) -> LocalChatProbeContract:
    if (
        settings.environment != "development"
        or settings.assistant_local_dev_mode
        or settings.assistant_test_startup_bootstrap
        or settings.assistant_chat_provider != "openai-compatible"
        or (settings.assistant_chat_endpoint or "").rstrip("/")
        not in {"https://api.deepseek.com", "https://api.deepseek.com/v1"}
        or settings.assistant_chat_model not in {"deepseek-v4-flash", "deepseek-flash"}
        or settings.assistant_chat_model_version != "DeepSeek-V4-Flash-0731"
    ):
        raise ProviderQualificationError(
            "local probe requires reviewed development DeepSeek config"
        )
    input_limit = settings.assistant_chat_max_input_tokens or 0
    output_limit = settings.assistant_chat_max_output_tokens or 0
    context_limit = settings.assistant_chat_context_window_tokens or 0
    timeout = settings.assistant_provider_timeout_seconds or 0
    if min(input_limit, output_limit, context_limit, timeout) <= 0:
        raise ProviderQualificationError("local probe requires explicit token limits and timeout")
    if (
        input_limit + output_limit > context_limit
        or context_limit > 1_000_000
        or not 1 <= approved_max_micro_cny <= (2**63 - 1 if authorization_id else 1_000_000)
        or not 1 <= max_calls <= (2**31 - 1 if authorization_id else 100)
        or not approved_daily_budget.is_finite()
        or settings.assistant_chat_daily_budget_cny is None
        or not Decimal("0") < settings.assistant_chat_daily_budget_cny <= approved_daily_budget
        or not settings.assistant_chat_api_key
        or len(settings.assistant_readiness_hmac_secret or "") < 32
        or settings.assistant_langsmith_tracing
    ):
        raise ProviderQualificationError(
            "local probe limits, credentials or approved budget invalid"
        )
    input_price = _settings_price(settings.assistant_chat_input_price_cny_per_million, "chat input")
    output_price = _settings_price(
        settings.assistant_chat_output_price_cny_per_million, "chat output"
    )
    if input_price <= 0 or output_price <= 0:
        raise ProviderQualificationError("local Chat price must be positive")
    return LocalChatProbeContract(
        authorization_id=authorization_id,
        model=settings.assistant_chat_model,
        model_version=settings.assistant_chat_model_version,
        max_input_tokens=input_limit,
        max_output_tokens=output_limit,
        context_window_tokens=context_limit,
        input_price_micro_cny_per_million=input_price,
        output_price_micro_cny_per_million=output_price,
        max_calls=max_calls,
        max_micro_cny=approved_max_micro_cny,
        timeout_seconds=timeout,
        # The new local alias is explicitly operator-approved. Do not infer a
        # versioned provider contract from the alias or upgrade production proof.
        model_identity_source=(
            "operator-declaration" if settings.assistant_chat_model == "deepseek-flash"
            else "versioned-provider-contract"
        ),
        credential_binding=hmac_hex(
            str(settings.assistant_readiness_hmac_secret),
            str(settings.assistant_chat_endpoint) + "\n" + str(settings.assistant_chat_api_key),
            context="local-provider-probe-v1",
        ),
    )


def run_local_chat_probe(
    *,
    settings: Settings,
    ledger_path: Path,
    output_path: Path,
    approved_max_micro_cny: int,
    max_calls: int,
    chat_factory: Callable[[Settings], Any] = build_chat_model,
    authorization_id: str | None = None,
) -> dict[str, Any]:
    from . import local_ledger

    local_ledger._guard(settings, ledger_path)
    with local_ledger.run_lock(ledger_path):
        daily_budget = Decimal("2")
        if authorization_id:
            approved = local_ledger.policy(ledger_path, settings, authorization_id)
            daily_budget = Decimal(approved["daily_budget_cny"])
        return _run_local_chat_probe(
            settings=settings,
            ledger_path=ledger_path,
            output_path=output_path,
            approved_max_micro_cny=approved_max_micro_cny,
            max_calls=max_calls,
            chat_factory=chat_factory,
            authorization_id=authorization_id,
            approved_daily_budget=daily_budget,
        )


def _run_local_chat_probe(
    *,
    settings: Settings,
    ledger_path: Path,
    output_path: Path,
    approved_max_micro_cny: int,
    max_calls: int,
    chat_factory: Callable[[Settings], Any],
    authorization_id: str | None,
    approved_daily_budget: Decimal,
) -> dict[str, Any]:
    """Use the existing probe and ledger with an explicitly non-production binding."""
    if settings.assistant_online_enabled:
        raise ProviderQualificationError("local probe requires online disabled")
    contract = _local_chat_contract(
        settings=settings,
        approved_max_micro_cny=approved_max_micro_cny,
        max_calls=max_calls,
        authorization_id=authorization_id,
        approved_daily_budget=approved_daily_budget,
    )
    root = Path(__file__).resolve().parents[2] / "data"
    paths = [ledger_path.resolve(), output_path.resolve()]
    if paths[0] == paths[1] or any(not p.is_relative_to(root) for p in paths):
        raise ProviderQualificationError("local probe needs distinct artifact paths under API data")
    if authorization_id and output_path.exists():
        raise ProviderQualificationError(
            "authorized revalidation requires a new output to retain history"
        )

    def now() -> datetime:
        return datetime.now(UTC)

    result = _chat_probe(settings, contract, paths[0], now, chat_factory)
    if authorization_id:
        from . import local_ledger

        calls, cost = local_ledger.totals(local_ledger._load(paths[0], settings))
    else:
        calls, cost = _totals(_read_json(paths[0]))
    payload = {
        "scope": "local-development-chat",
        "production_qualified": False,
        "schema_version": 2,
        "configuration_digest": _probe_digest(contract),
        "compatibility_digest": _local_compatibility_digest(contract),
        "approved_daily_budget_cny": str(approved_daily_budget),
        "authorization_id": authorization_id,
        "completed_at": now().isoformat(),
        "chat": result,
        "model_version_reference": "https://api-docs.deepseek.com/zh-cn/updates/",
        "ledger": {
            "calls_used": calls,
            "micro_cny_used": cost,
            "max_calls": max_calls,
            "max_micro_cny": approved_max_micro_cny,
            "within_envelope": cost <= approved_max_micro_cny and calls <= max_calls,
        },
        "content_retained": False,
        "raw_provider_payload_retained": False,
    }
    payload["probe_hmac"] = hmac_hex(
        str(settings.assistant_readiness_hmac_secret),
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
        context="local-chat-probe-artifact-v1",
    )
    _atomic_json(paths[1], payload)
    return payload


def _local_compatibility_digest(contract: LocalChatProbeContract) -> str:
    from ..assistant.readiness import _schema_hash

    fields = asdict(contract)
    for key in (
        "input_price_micro_cny_per_million",
        "output_price_micro_cny_per_million",
        "max_calls",
        "max_micro_cny",
        "authorization_id",
    ):
        fields.pop(key)
    fields["output_protocol"] = "local-deepseek-json-v1:" + _schema_hash()
    return (
        "sha256:"
        + hashlib.sha256(
            json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )


def migrate_local_chat_evidence(source: Path, output: Path, settings: Settings) -> dict:
    """Offline conversion requires the original v1 configuration; never rewrite its facts."""
    if source.resolve() == output.resolve() or output.exists():
        raise ProviderQualificationError("migration requires a distinct new output file")
    original = source.read_bytes()
    payload = validate_local_chat_probe_artifact(source, settings)
    if payload["schema_version"] != 1:
        raise ProviderQualificationError("only legacy v1 evidence needs conversion")
    contract = _local_chat_contract(
        settings=settings,
        approved_max_micro_cny=payload["ledger"]["max_micro_cny"],
        max_calls=payload["ledger"]["max_calls"],
    )
    payload.update(
        schema_version=2,
        compatibility_digest=_local_compatibility_digest(contract),
        approved_daily_budget_cny="2",
        legacy_evidence=json.loads(original),
        legacy_sha256=hashlib.sha256(original).hexdigest(),
    )
    payload["probe_hmac"] = hmac_hex(
        str(settings.assistant_readiness_hmac_secret),
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
        context="local-chat-probe-artifact-v1",
    )
    _atomic_json(output, payload)
    return payload


def rebind_local_chat_costs(
    source: Path,
    output: Path,
    settings: Settings,
    ledger_path: Path,
    authorization_id: str,
) -> dict:
    """Apply a separately approved cost policy without changing compatibility evidence time."""
    from . import local_ledger

    local_ledger._guard(settings, ledger_path)
    if source.resolve() == output.resolve() or output.exists():
        raise ProviderQualificationError("cost rebind requires a distinct new output file")
    with local_ledger.run_lock(ledger_path):
        approved = local_ledger.policy(ledger_path, settings, authorization_id)
        current = _local_chat_contract(
            settings=settings,
            approved_max_micro_cny=approved["max_micro_cny"],
            max_calls=approved["max_calls"],
            approved_daily_budget=Decimal(approved["daily_budget_cny"]),
            authorization_id=authorization_id,
        )
        if _probe_digest(current) != approved["contract_digest"]:
            raise ProviderQualificationError("cost authorization configuration mismatch")
        # Never trust this cap to grant anything: the old signature is validated below.
        original = json.loads(source.read_text(encoding="utf-8"))
        previous_cap = Decimal(original.get("approved_daily_budget_cny", "2"))
        payload = validate_local_chat_probe_artifact(
            source,
            settings.model_copy(update={"assistant_chat_daily_budget_cny": previous_cap}),
        )
        if payload["schema_version"] != 2:
            raise ProviderQualificationError(
                "convert legacy evidence under its original config first"
            )
        payload.update(
            approved_daily_budget_cny=approved["daily_budget_cny"],
            authorization_id=authorization_id,
            previous_evidence=original,
            cost_authorization_digest=approved["contract_digest"],
        )
        payload["probe_hmac"] = hmac_hex(
            str(settings.assistant_readiness_hmac_secret),
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
            context="local-chat-probe-artifact-v1",
        )
        _atomic_json(output, payload)
        return payload


def local_chat_probe_notice(path: Path, settings: Settings) -> str:
    """Describe authenticated evidence without suggesting an automatic paid refresh."""
    payload = validate_local_chat_probe_artifact(path, settings)
    completed = datetime.fromisoformat(payload["completed_at"])
    age = (datetime.now(UTC) - completed).total_seconds()
    message = f"Chat 最后验证时间：{completed.astimezone(UTC).isoformat()}。"
    if age > 86400:
        message += "记录已超过 24 小时；年龄仅作提示，不要求付费复验。"
    return message + "历史成功不保证供应商当前可用；启动不会自动调用付费 Chat。"


def validate_local_chat_probe_artifact(path: Path, settings: Settings) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("artifact must be an object")
        signature = payload.pop("probe_hmac")
        expected = hmac_hex(
            str(settings.assistant_readiness_hmac_secret),
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
            context="local-chat-probe-artifact-v1",
        )
        if not hmac.compare_digest(str(signature), expected):
            raise ValueError("signature")
        contract = _local_chat_contract(
            settings=settings,
            approved_max_micro_cny=payload["ledger"]["max_micro_cny"],
            max_calls=payload["ledger"]["max_calls"],
            approved_daily_budget=Decimal(payload.get("approved_daily_budget_cny", "2")),
            authorization_id=payload.get("authorization_id"),
        )
        age = (datetime.now(UTC) - datetime.fromisoformat(payload["completed_at"])).total_seconds()
        if (
            payload["schema_version"] not in {1, 2}
            or (
                payload["schema_version"] == 1
                and payload["configuration_digest"] != _probe_digest(contract)
            )
            or (
                payload["schema_version"] == 2
                and payload["compatibility_digest"] != _local_compatibility_digest(contract)
            )
            or payload["scope"] != "local-development-chat"
            or payload["production_qualified"]
            or payload["chat"]["status"] != "pass"
            or not payload["chat"]["application_schema"]
            or not payload["ledger"]["within_envelope"]
            or age < 0
        ):
            raise ValueError("binding, success evidence or future timestamp")
        return payload
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ProviderQualificationError(
            "local Chat probe is missing, invalid, future-dated or mismatched; "
            "check signed evidence and configuration; age alone does not require a paid refresh"
        ) from exc
