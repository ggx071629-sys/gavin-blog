from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .config import harness_root, load_config, project_root

ALGORITHM = "rsa-sha256-pkcs1-v1_5"
MANIFEST_SCHEMA_VERSION = 1
PUBLIC_KEY_SCHEMA_VERSION = 1
REQUIRED_RESULT_SECTIONS = frozenset(
    {
        "profile_validation",
        "deployment",
        "provider_contract",
        "tls_proxy",
        "qdrant",
        "backup_restore",
        "saver",
        "resources",
        "conformance",
        "observability",
        "dark_launch",
    }
)
REQUIRED_TOP_LEVEL = frozenset(
    {
        "schema_version",
        "task_id",
        "qualification_state",
        "source_commit",
        "artifact_digest",
        "profile_digest",
        "case_suite_digest",
        "started_at",
        "completed_at",
        "expires_at",
        "invalidation_paths",
        "target",
        "provider",
        "active_generation",
        "switches",
        "qualification_usage",
        "results",
        "cases",
        "artifacts",
        "operator",
        "signature",
    }
)
REQUIRED_INVALIDATION_PATHS = frozenset(
    {
        "source_commit",
        "artifact_digest",
        "profile_digest",
        "case_suite_digest",
        "provider_contract",
        "model_identity",
        "provider_pricing",
        "active_generation",
        "tls_proxy_contract",
        "qdrant_contract",
        "secret_rotation",
        "qualification_trust_policy",
    }
)
CASE_CATEGORIES = frozenset(
    {
        "profile",
        "deployment",
        "provider",
        "security",
        "streaming",
        "retrieval",
        "qdrant",
        "backup_restore",
        "saver",
        "resource",
        "conformance",
        "observability",
        "dark_launch",
    }
)
CASE_CLASSIFICATIONS = frozenset({"deterministic", "manual-rubric", "measured"})
_CASE_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$")
_TASK_ID_RE = re.compile(r"^[0-9]{8}-[a-z0-9]+(?:-[a-z0-9]+)*$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_KEY_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_FORBIDDEN_KEYS = frozenset(
    {
        "question",
        "answer",
        "evidence_body",
        "raw_ip",
        "api_key",
        "secret_value",
        "secret_fingerprint",
        "private_endpoint",
        "provider_raw_response",
        "checkpoint",
        "database_copy",
        "query_vector",
    }
)
_SHA256_DIGEST_INFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


class QualificationError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise QualificationError(f"qualification artifact is missing: {path}") from error
    except (OSError, json.JSONDecodeError) as error:
        raise QualificationError(f"qualification artifact is unreadable: {path}: {error}") from error


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QualificationError(f"{label} must be an object")
    return value


def _exact_fields(value: dict[str, Any], expected: set[str] | frozenset[str], label: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unexpected " + ", ".join(extra))
        raise QualificationError(f"{label} fields are invalid: {'; '.join(details)}")


def _text(value: Any, label: str, *, minimum: int = 1) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum:
        raise QualificationError(f"{label} must be a non-empty string")
    lowered = value.strip().lower()
    if lowered in {"unknown", "missing", "stale", "skipped", "todo", "tbd", "placeholder"}:
        raise QualificationError(f"{label} cannot be {lowered}")
    return value.strip()


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise QualificationError(f"{label} must be an integer >= {minimum}")
    return value


def _timestamp(value: Any, label: str) -> datetime:
    text = _text(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise QualificationError(f"{label} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise QualificationError(f"{label} must include an explicit offset")
    return parsed.astimezone(timezone.utc)


def _b64url_decode(value: str, label: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (binascii.Error, ValueError, TypeError) as error:
        raise QualificationError(f"{label} is not valid base64url") from error


def _int_from_b64url(value: Any, label: str) -> int:
    text = _text(value, label)
    raw = _b64url_decode(text, label)
    if not raw:
        raise QualificationError(f"{label} cannot be empty")
    return int.from_bytes(raw, "big")


def _int_to_b64url(value: int, size: int | None = None) -> str:
    length = size or max(1, (value.bit_length() + 7) // 8)
    return base64.urlsafe_b64encode(value.to_bytes(length, "big")).decode().rstrip("=")


def _signature_payload(manifest: dict[str, Any]) -> bytes:
    payload = dict(manifest)
    signature = _object(payload.pop("signature"), "signature")
    _exact_fields(signature, {"key_id", "algorithm", "value"}, "signature")
    payload["signature"] = {
        "key_id": signature.get("key_id"),
        "algorithm": signature.get("algorithm"),
    }
    return _canonical(payload)


def _emsa_pkcs1_v1_5(message: bytes, modulus_bytes: int) -> bytes:
    digest_info = _SHA256_DIGEST_INFO_PREFIX + hashlib.sha256(message).digest()
    padding_length = modulus_bytes - len(digest_info) - 3
    if padding_length < 8:
        raise QualificationError("RSA modulus is too small for SHA-256 signature encoding")
    return b"\x00\x01" + b"\xff" * padding_length + b"\x00" + digest_info


def sign_manifest(manifest: dict[str, Any], private_key: dict[str, Any]) -> dict[str, Any]:
    unsigned = dict(manifest)
    if "signature" in unsigned:
        raise QualificationError("unsigned qualification manifest must not contain signature")
    _validate_manifest_structure({**unsigned, "signature": _placeholder_signature(private_key)})
    key = _validate_private_key(private_key)
    signed = {
        **unsigned,
        "signature": {
            "key_id": key["key_id"],
            "algorithm": ALGORITHM,
            "value": "",
        },
    }
    encoded = _signature_payload(signed)
    modulus_bytes = (key["n"].bit_length() + 7) // 8
    em = _emsa_pkcs1_v1_5(encoded, modulus_bytes)
    signature = pow(int.from_bytes(em, "big"), key["d"], key["n"])
    signed["signature"]["value"] = _int_to_b64url(signature, modulus_bytes)
    return signed


def _placeholder_signature(private_key: dict[str, Any]) -> dict[str, str]:
    return {
        "key_id": str(private_key.get("key_id", "invalid")),
        "algorithm": str(private_key.get("algorithm", ALGORITHM)),
        "value": "AA",
    }


def _validate_private_key(payload: dict[str, Any]) -> dict[str, Any]:
    _exact_fields(payload, {"schema_version", "key_id", "algorithm", "n", "e", "d"}, "private key")
    if payload.get("schema_version") != PUBLIC_KEY_SCHEMA_VERSION:
        raise QualificationError("private key schema_version must be 1")
    key_id = _text(payload.get("key_id"), "private key key_id")
    if _KEY_ID_RE.fullmatch(key_id) is None:
        raise QualificationError("private key key_id is invalid")
    if payload.get("algorithm") != ALGORITHM:
        raise QualificationError("private key algorithm is unsupported")
    n = _int_from_b64url(payload.get("n"), "private key modulus")
    d = _int_from_b64url(payload.get("d"), "private key exponent")
    e = payload.get("e")
    if e != 65537:
        raise QualificationError("private key public exponent must be 65537")
    if n.bit_length() < 3072:
        raise QualificationError("qualification signing key must be at least RSA-3072")
    return {"key_id": key_id, "n": n, "e": e, "d": d}


def _load_public_keys(payload: dict[str, Any], at: datetime) -> dict[str, dict[str, Any]]:
    _exact_fields(payload, {"schema_version", "keys"}, "public key set")
    if payload.get("schema_version") != PUBLIC_KEY_SCHEMA_VERSION:
        raise QualificationError("public key set schema_version must be 1")
    raw_keys = payload.get("keys")
    if not isinstance(raw_keys, list) or not raw_keys:
        raise QualificationError("public key set keys must be a non-empty array")
    keys: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(raw_keys, start=1):
        key = _object(raw, f"public key {index}")
        _exact_fields(
            key,
            {"key_id", "algorithm", "n", "e", "not_before", "not_after"},
            f"public key {index}",
        )
        key_id = _text(key.get("key_id"), f"public key {index} key_id")
        if _KEY_ID_RE.fullmatch(key_id) is None or key_id in keys:
            raise QualificationError("public key IDs must be unique lowercase tokens")
        if key.get("algorithm") != ALGORITHM or key.get("e") != 65537:
            raise QualificationError(f"public key {key_id} algorithm or exponent is invalid")
        n = _int_from_b64url(key.get("n"), f"public key {key_id} modulus")
        if n.bit_length() < 3072:
            raise QualificationError("qualification public key must be at least RSA-3072")
        not_before = _timestamp(key.get("not_before"), f"public key {key_id} not_before")
        not_after = _timestamp(key.get("not_after"), f"public key {key_id} not_after")
        if not_before > at or at > not_after:
            continue
        keys[key_id] = {"n": n, "e": 65537}
    return keys


def _verify_signature(
    manifest: dict[str, Any], public_keys: dict[str, Any], completed_at: datetime
) -> None:
    signature = _object(manifest.get("signature"), "signature")
    _exact_fields(signature, {"key_id", "algorithm", "value"}, "signature")
    if signature.get("algorithm") != ALGORITHM:
        raise QualificationError("qualification signature algorithm is unsupported")
    key_id = _text(signature.get("key_id"), "signature key_id")
    keys = _load_public_keys(public_keys, completed_at)
    key = keys.get(key_id)
    if key is None:
        raise QualificationError("qualification signature key is not pinned and valid")
    raw_signature = _int_from_b64url(signature.get("value"), "signature value")
    modulus_bytes = (key["n"].bit_length() + 7) // 8
    if raw_signature >= key["n"]:
        raise QualificationError("qualification signature is outside the RSA modulus")
    actual = pow(raw_signature, key["e"], key["n"]).to_bytes(modulus_bytes, "big")
    expected = _emsa_pkcs1_v1_5(_signature_payload(manifest), modulus_bytes)
    if actual != expected:
        raise QualificationError("qualification signature verification failed")


def _validate_status(value: Any, label: str) -> tuple[str, str | None]:
    text = _text(value, label)
    if text == "pass" or text == "measured_fail":
        return text, None
    if text.startswith("blocked_by:"):
        blocker = text.split(":", 1)[1]
        if _CASE_ID_RE.fullmatch(blocker) is None:
            raise QualificationError(f"{label} blocked_by case ID is invalid")
        return "blocked_by", blocker
    raise QualificationError(f"{label} must be pass, measured_fail, or blocked_by:<case_id>")


def _validate_case(raw: Any, index: int) -> dict[str, Any]:
    case = _object(raw, f"case {index}")
    _exact_fields(
        case,
        {
            "case_id",
            "suite_version",
            "status",
            "category",
            "classification",
            "reviewer",
            "reviewed_at",
            "artifact_hashes",
        },
        f"case {index}",
    )
    case_id = _text(case.get("case_id"), f"case {index} ID")
    if _CASE_ID_RE.fullmatch(case_id) is None:
        raise QualificationError(f"case {index} ID is invalid")
    _text(case.get("suite_version"), f"case {case_id} suite_version")
    status, blocker = _validate_status(case.get("status"), f"case {case_id} status")
    if case.get("category") not in CASE_CATEGORIES:
        raise QualificationError(f"case {case_id} category is invalid")
    if case.get("classification") not in CASE_CLASSIFICATIONS:
        raise QualificationError(f"case {case_id} classification is invalid")
    _text(case.get("reviewer"), f"case {case_id} reviewer", minimum=2)
    _timestamp(case.get("reviewed_at"), f"case {case_id} reviewed_at")
    hashes = case.get("artifact_hashes")
    if not isinstance(hashes, list) or not hashes:
        raise QualificationError(f"case {case_id} artifact_hashes must be non-empty")
    if len(set(hashes)) != len(hashes) or any(
        not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None for value in hashes
    ):
        raise QualificationError(f"case {case_id} artifact_hashes are invalid")
    return {
        "case_id": case_id,
        "status": status,
        "blocker": blocker,
        "suite_version": case["suite_version"],
        "category": case["category"],
        "classification": case["classification"],
    }


def _validate_result(
    raw: Any,
    name: str,
    cases: dict[str, dict[str, Any]],
) -> tuple[str, str | None]:
    result = _object(raw, f"result {name}")
    _exact_fields(result, {"status", "case_ids", "summary"}, f"result {name}")
    status, blocker = _validate_status(result.get("status"), f"result {name} status")
    linked = result.get("case_ids")
    if not isinstance(linked, list) or not linked or len(set(linked)) != len(linked):
        raise QualificationError(f"result {name} case_ids must be unique and non-empty")
    if any(not isinstance(value, str) or value not in cases for value in linked):
        raise QualificationError(f"result {name} references an unknown case")
    linked_statuses = {cases[value]["status"] for value in linked}
    if status == "pass" and linked_statuses != {"pass"}:
        raise QualificationError(f"result {name} cannot pass with a failed or blocked case")
    if status == "measured_fail" and "measured_fail" not in linked_statuses:
        raise QualificationError(f"result {name} measured_fail lacks a measured fail case")
    if status == "blocked_by" and blocker not in linked:
        raise QualificationError(f"result {name} must link its direct blocker case")
    _text(result.get("summary"), f"result {name} summary", minimum=12)
    return status, blocker


def _validate_artifacts(raw: Any) -> None:
    if not isinstance(raw, list) or not raw:
        raise QualificationError("artifacts must be a non-empty array")
    seen: set[str] = set()
    for index, item in enumerate(raw, start=1):
        artifact = _object(item, f"artifact {index}")
        _exact_fields(
            artifact,
            {"artifact_id", "kind", "sha256", "location_category", "retention_days", "reviewed"},
            f"artifact {index}",
        )
        artifact_id = _text(artifact.get("artifact_id"), f"artifact {index} ID")
        if artifact_id in seen:
            raise QualificationError("artifact IDs must be unique")
        seen.add(artifact_id)
        _text(artifact.get("kind"), f"artifact {artifact_id} kind")
        if not isinstance(artifact.get("sha256"), str) or _DIGEST_RE.fullmatch(
            artifact["sha256"]
        ) is None:
            raise QualificationError(f"artifact {artifact_id} sha256 is invalid")
        if artifact.get("location_category") not in {
            "encrypted-off-host-object-store",
            "encrypted-off-host-filesystem",
        }:
            raise QualificationError(f"artifact {artifact_id} location category is invalid")
        _integer(artifact.get("retention_days"), f"artifact {artifact_id} retention", minimum=1)
        if artifact.get("reviewed") is not True:
            raise QualificationError(f"artifact {artifact_id} must be reviewed")


def _reject_sensitive_fields(value: Any, path: str = "manifest") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in _FORBIDDEN_KEYS:
                raise QualificationError(f"{path}.{key} is forbidden in the compact manifest")
            _reject_sensitive_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sensitive_fields(child, f"{path}[{index}]")


def _validate_manifest_structure(manifest: dict[str, Any]) -> dict[str, Any]:
    _exact_fields(manifest, REQUIRED_TOP_LEVEL, "qualification manifest")
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise QualificationError("qualification manifest schema_version must be 1")
    task_id = _text(manifest.get("task_id"), "task_id")
    if _TASK_ID_RE.fullmatch(task_id) is None:
        raise QualificationError("qualification manifest task_id is invalid")
    state = manifest.get("qualification_state")
    if state not in {"QUALIFICATION_GO_CANDIDATE", "QUALIFICATION_NO_GO"}:
        raise QualificationError("qualification_state is invalid")
    source_commit = manifest.get("source_commit")
    if not isinstance(source_commit, str) or _COMMIT_RE.fullmatch(source_commit) is None:
        raise QualificationError("source_commit must be a full lowercase Git SHA")
    for key in ("artifact_digest", "profile_digest", "case_suite_digest"):
        value = manifest.get(key)
        if not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None:
            raise QualificationError(f"{key} must be a sha256 digest")
    started = _timestamp(manifest.get("started_at"), "started_at")
    completed = _timestamp(manifest.get("completed_at"), "completed_at")
    expires = _timestamp(manifest.get("expires_at"), "expires_at")
    if not started <= completed < expires:
        raise QualificationError("qualification timestamps must satisfy started <= completed < expires")
    invalidation = manifest.get("invalidation_paths")
    if not isinstance(invalidation, list) or set(invalidation) != REQUIRED_INVALIDATION_PATHS:
        raise QualificationError("qualification invalidation_paths are incomplete or duplicated")
    _validate_target(manifest.get("target"))
    provider_contract_ok, embedding_dimension = _validate_provider(manifest.get("provider"))
    generation_dimension = _validate_generation(manifest.get("active_generation"))
    if embedding_dimension != generation_dimension:
        raise QualificationError("provider and active generation dimensions do not match")
    _validate_switches(manifest.get("switches"))
    _validate_usage(manifest.get("qualification_usage"))
    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) < 30:
        raise QualificationError("qualification manifest must contain at least 30 cases")
    parsed_cases = [_validate_case(item, index) for index, item in enumerate(cases, start=1)]
    case_map = {item["case_id"]: item for item in parsed_cases}
    case_ids = set(case_map)
    if len(case_map) != len(parsed_cases):
        raise QualificationError("qualification case IDs must be unique")
    measured_failures = {
        item["case_id"] for item in parsed_cases if item["status"] == "measured_fail"
    }
    for item in parsed_cases:
        if item["status"] == "blocked_by" and item["blocker"] not in measured_failures:
            raise QualificationError(
                f"case {item['case_id']} must be blocked directly by a measured_fail case"
            )
    results = _object(manifest.get("results"), "results")
    _exact_fields(results, REQUIRED_RESULT_SECTIONS, "results")
    result_statuses = []
    for name in sorted(REQUIRED_RESULT_SECTIONS):
        status, blocker = _validate_result(results[name], name, case_map)
        if status == "blocked_by" and blocker not in measured_failures:
            raise QualificationError(
                f"result {name} must be blocked directly by a measured_fail case"
            )
        result_statuses.append(status)
    provider_result = _validate_status(
        results["provider_contract"]["status"], "result provider_contract status"
    )[0]
    if not provider_contract_ok and provider_result == "pass":
        raise QualificationError(
            "unproven provider usage, finish reason, or identity requires provider_contract failure"
        )
    has_failure = bool(measured_failures) or any(
        status != "pass" for status in result_statuses
    )
    expected_state = "QUALIFICATION_NO_GO" if has_failure else "QUALIFICATION_GO_CANDIDATE"
    if state != expected_state:
        raise QualificationError("qualification_state does not match the complete case results")
    _validate_artifacts(manifest.get("artifacts"))
    operator_reviewed_at = _validate_operator(manifest.get("operator"), state)
    if operator_reviewed_at < completed:
        raise QualificationError("operator review must occur after qualification completion")
    _reject_sensitive_fields(manifest)
    return {
        "task_id": task_id,
        "started_at": started,
        "completed_at": completed,
        "expires_at": expires,
        "case_ids": case_ids,
        "state": state,
    }


def _validate_target(raw: Any) -> None:
    target = _object(raw, "target")
    _exact_fields(
        target,
        {
            "real_target",
            "cpu_cores",
            "memory_mib",
            "os_name",
            "os_version",
            "architecture",
            "filesystem",
            "deployment_kind",
            "host_class",
        },
        "target",
    )
    if target.get("real_target") is not True or target.get("cpu_cores") != 2:
        raise QualificationError("qualification target must be the real 2 vCPU host")
    if target.get("memory_mib") != 4096:
        raise QualificationError("qualification target must have 4096 MiB memory")
    for key in ("os_name", "os_version", "architecture", "filesystem", "deployment_kind", "host_class"):
        _text(target.get(key), f"target {key}")


def _validate_provider(raw: Any) -> tuple[bool, int]:
    provider = _object(raw, "provider")
    _exact_fields(provider, {"real_provider", "chat", "embedding"}, "provider")
    if provider.get("real_provider") is not True:
        raise QualificationError("qualification must use the final real provider")
    chat = _object(provider.get("chat"), "provider chat")
    _exact_fields(
        chat,
        {
            "provider",
            "model",
            "version",
            "model_identity_source",
            "input_price_micro_cny_per_million",
            "output_price_micro_cny_per_million",
            "reports_usage",
            "reports_finish_reason",
        },
        "provider chat",
    )
    embedding = _object(provider.get("embedding"), "provider embedding")
    _exact_fields(
        embedding,
        {
            "provider",
            "model",
            "version",
            "model_identity_source",
            "dimension",
            "input_price_micro_cny_per_million",
            "reports_usage",
        },
        "provider embedding",
    )
    for label, item in (("chat", chat), ("embedding", embedding)):
        for key in ("provider", "model", "version"):
            _text(item.get(key), f"provider {label} {key}")
        if item.get("model_identity_source") not in {
            "provider-response",
            "versioned-provider-contract",
            "operator-declaration",
        }:
            raise QualificationError(f"provider {label} model identity source is invalid")
        _integer(
            item.get("input_price_micro_cny_per_million"),
            f"provider {label} input price",
        )
    _integer(chat.get("output_price_micro_cny_per_million"), "provider chat output price")
    _integer(embedding.get("dimension"), "provider embedding dimension", minimum=8)
    if not isinstance(chat.get("reports_usage"), bool) or not isinstance(
        chat.get("reports_finish_reason"), bool
    ):
        raise QualificationError("provider chat capabilities must be measured booleans")
    if not isinstance(embedding.get("reports_usage"), bool):
        raise QualificationError("provider embedding usage capability must be measured")
    contract_ok = bool(
        chat["reports_usage"]
        and chat["reports_finish_reason"]
        and embedding["reports_usage"]
        and chat["model_identity_source"] != "operator-declaration"
        and embedding["model_identity_source"] != "operator-declaration"
    )
    return contract_ok, int(embedding["dimension"])


def _validate_generation(raw: Any) -> int:
    generation = _object(raw, "active_generation")
    _exact_fields(
        generation,
        {"id", "collection", "dimension", "distance", "pipeline_version"},
        "active_generation",
    )
    _integer(generation.get("id"), "active_generation id", minimum=1)
    _text(generation.get("collection"), "active_generation collection")
    _integer(generation.get("dimension"), "active_generation dimension", minimum=8)
    if generation.get("distance") != "Cosine":
        raise QualificationError("active_generation distance must be Cosine")
    _text(generation.get("pipeline_version"), "active_generation pipeline_version")
    return int(generation["dimension"])


def _validate_switches(raw: Any) -> None:
    switches = _object(raw, "switches")
    _exact_fields(
        switches,
        {"before", "canary", "after", "runner_auto_enabled"},
        "switches",
    )
    for phase in ("before", "after"):
        values = _object(switches.get(phase), f"switches {phase}")
        _exact_fields(
            values,
            {"web_launcher", "api_capability", "runtime_gate"},
            f"switches {phase}",
        )
        if set(values.values()) != {False}:
            raise QualificationError(f"all switches must be disabled {phase} qualification")
    canary = _object(switches.get("canary"), "switches canary")
    _exact_fields(canary, {"edge_restricted", "administrator_enabled"}, "switches canary")
    if set(canary.values()) != {True} or switches.get("runner_auto_enabled") is not False:
        raise QualificationError("canary must be edge-restricted and manually enabled only")


def _validate_usage(raw: Any) -> None:
    usage = _object(raw, "qualification_usage")
    _exact_fields(
        usage,
        {
            "beijing_dates",
            "chat_calls",
            "query_embedding_calls",
            "index_embedding_calls",
            "total_micro_cny",
            "max_calls",
            "max_micro_cny",
            "within_envelope",
        },
        "qualification_usage",
    )
    dates = usage.get("beijing_dates")
    if not isinstance(dates, list) or not dates or len(set(dates)) != len(dates):
        raise QualificationError("qualification Beijing dates must be unique and non-empty")
    for value in dates:
        try:
            date.fromisoformat(str(value))
        except ValueError as error:
            raise QualificationError("qualification Beijing date is invalid") from error
    calls = sum(
        _integer(usage.get(key), f"qualification usage {key}")
        for key in ("chat_calls", "query_embedding_calls", "index_embedding_calls")
    )
    maximum_calls = _integer(usage.get("max_calls"), "qualification max_calls", minimum=1)
    total_cost = _integer(usage.get("total_micro_cny"), "qualification total cost")
    maximum_cost = _integer(usage.get("max_micro_cny"), "qualification max cost")
    if usage.get("within_envelope") is not True or calls > maximum_calls or total_cost > maximum_cost:
        raise QualificationError("qualification calls or cost exceeded the approved envelope")


def _validate_operator(raw: Any, state: str) -> datetime:
    operator = _object(raw, "operator")
    _exact_fields(
        operator,
        {"reviewer", "reviewed_at", "decision_reason", "residual_risks", "remediation_tasks"},
        "operator",
    )
    _text(operator.get("reviewer"), "operator reviewer", minimum=2)
    reviewed_at = _timestamp(operator.get("reviewed_at"), "operator reviewed_at")
    _text(operator.get("decision_reason"), "operator decision_reason", minimum=12)
    for key in ("residual_risks", "remediation_tasks"):
        values = operator.get(key)
        if not isinstance(values, list) or any(
            not isinstance(value, str) or len(value.strip()) < 3 for value in values
        ):
            raise QualificationError(f"operator {key} must be a string array")
    if state == "QUALIFICATION_NO_GO" and not operator["remediation_tasks"]:
        raise QualificationError("QUALIFICATION_NO_GO requires a remediation task reference")
    return reviewed_at


def verify_manifest(
    manifest: dict[str, Any],
    public_keys: dict[str, Any],
    *,
    expected_task_id: str | None = None,
    expected_profile_digest: str | None = None,
    expected_case_suite_digest: str | None = None,
    expected_case_ids: set[str] | None = None,
    expected_case_contracts: dict[str, dict[str, str]] | None = None,
    active: bool,
    now: datetime | None = None,
) -> dict[str, Any]:
    facts = _validate_manifest_structure(manifest)
    _verify_signature(manifest, public_keys, facts["completed_at"])
    if expected_task_id is not None and facts["task_id"] != expected_task_id:
        raise QualificationError("qualification manifest task does not match configuration")
    if expected_profile_digest is not None and manifest["profile_digest"] != expected_profile_digest:
        raise QualificationError("qualification profile digest has drifted")
    if expected_case_suite_digest is not None and manifest["case_suite_digest"] != expected_case_suite_digest:
        raise QualificationError("qualification case-suite digest has drifted")
    if expected_case_ids is not None and facts["case_ids"] != expected_case_ids:
        raise QualificationError("qualification cases do not exactly match the versioned suite")
    if expected_case_contracts is not None:
        actual = {
            case["case_id"]: {
                "suite_version": case["suite_version"],
                "category": case["category"],
                "classification": case["classification"],
            }
            for case in manifest["cases"]
        }
        if actual != expected_case_contracts:
            raise QualificationError("qualification case metadata has drifted from the suite")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if active and current > facts["expires_at"]:
        raise QualificationError("active qualification manifest is stale")
    return facts


def _task_config(task_id: str, config: dict[str, Any] | None = None) -> dict[str, Any] | None:
    config = config or load_config()
    qualifications = config.get("verification", {}).get("qualifications", {})
    tasks = qualifications.get("tasks", {}) if isinstance(qualifications, dict) else {}
    raw = tasks.get(task_id) if isinstance(tasks, dict) else None
    if raw is None:
        return None
    definition = _object(raw, f"qualification task {task_id}")
    _exact_fields(definition, {"manifest", "profile", "case_suite"}, f"qualification task {task_id}")
    return definition


def _configured_path(relative: Any, label: str) -> Path:
    text = _text(relative, label)
    if text.startswith(('/', '\\')) or "\\" in text or any(
        part in {"", ".", ".."} for part in text.split("/")
    ):
        raise QualificationError(f"{label} must be a safe harness-relative path")
    root = harness_root().resolve()
    path = root.joinpath(*text.split("/")).resolve()
    if not path.is_relative_to(root):
        raise QualificationError(f"{label} escapes the harness root")
    return path


def _profile_digest(path: Path) -> str:
    api_root = project_root() / "apps" / "api"
    added = False
    if str(api_root) not in sys.path:
        sys.path.insert(0, str(api_root))
        added = True
    try:
        from app.assistant_qualification.profile import load_profile, profile_digest

        return profile_digest(load_profile(path))
    except (OSError, ValueError) as error:
        raise QualificationError(f"qualification profile is invalid: {error}") from error
    finally:
        if added:
            sys.path.remove(str(api_root))


def _case_suite(path: Path) -> tuple[str, dict[str, dict[str, str]]]:
    payload = _object(_load_json(path), "qualification case suite")
    _exact_fields(payload, {"schema_version", "suite_id", "suite_version", "cases"}, "case suite")
    if payload.get("schema_version") != 1:
        raise QualificationError("qualification case suite schema_version must be 1")
    _text(payload.get("suite_id"), "case suite ID")
    _text(payload.get("suite_version"), "case suite version")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) < 30:
        raise QualificationError("qualification case suite must contain at least 30 cases")
    contracts: dict[str, dict[str, str]] = {}
    dependencies: dict[str, list[str]] = {}
    conformance_count = 0
    for index, raw in enumerate(cases, start=1):
        case = _object(raw, f"case suite item {index}")
        _exact_fields(
            case,
            {
                "case_id",
                "category",
                "mode",
                "conformance",
                "billable",
                "destructive_isolation",
                "depends_on",
                "fixture",
                "description",
                "assertions",
            },
            f"case suite item {index}",
        )
        case_id = _text(case.get("case_id"), f"case suite item {index} ID")
        if _CASE_ID_RE.fullmatch(case_id) is None or case_id in contracts:
            raise QualificationError("qualification case suite IDs must be unique and valid")
        category = case.get("category")
        if category not in CASE_CATEGORIES:
            raise QualificationError(f"qualification case {case_id} category is invalid")
        mode = case.get("mode")
        classifications = {
            "deterministic-offline": "deterministic",
            "real-provider": "measured",
            "target-observation": "measured",
            "manual-rubric": "manual-rubric",
        }
        if mode not in classifications:
            raise QualificationError(f"qualification case {case_id} mode is invalid")
        if not isinstance(case.get("conformance"), bool):
            raise QualificationError(f"qualification case {case_id} conformance must be boolean")
        if case["conformance"]:
            conformance_count += 1
        if not isinstance(case.get("billable"), bool) or (
            case["billable"] and mode != "real-provider"
        ):
            raise QualificationError(
                f"qualification case {case_id} billable is incompatible with its mode"
            )
        if mode == "real-provider" and case.get("billable") is not True:
            raise QualificationError(f"real-provider case {case_id} must be billable")
        if not isinstance(case.get("destructive_isolation"), bool):
            raise QualificationError(
                f"qualification case {case_id} destructive_isolation must be boolean"
            )
        depends_on = case.get("depends_on")
        if not isinstance(depends_on, list) or len(set(depends_on)) != len(depends_on):
            raise QualificationError(f"qualification case {case_id} dependencies are invalid")
        _text(case.get("description"), f"qualification case {case_id} description", minimum=12)
        _text(case.get("fixture"), f"qualification case {case_id} fixture", minimum=3)
        assertions = case.get("assertions")
        if not isinstance(assertions, list) or not assertions or any(
            not isinstance(value, str) or len(value.strip()) < 3 for value in assertions
        ):
            raise QualificationError(f"qualification case {case_id} assertions are invalid")
        contracts[case_id] = {
            "suite_version": str(payload["suite_version"]),
            "category": str(category),
            "classification": classifications[str(mode)],
        }
        dependencies[case_id] = [str(value) for value in depends_on]
    if conformance_count < 30:
        raise QualificationError("qualification suite must contain at least 30 conformance cases")
    for case_id, values in dependencies.items():
        unknown = sorted(set(values) - set(contracts))
        if case_id in values or unknown:
            raise QualificationError(
                f"qualification case {case_id} has cyclic or unknown dependencies"
            )
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(case_id: str) -> None:
        if case_id in visiting:
            raise QualificationError("qualification case dependencies contain a cycle")
        if case_id in visited:
            return
        visiting.add(case_id)
        for dependency in dependencies[case_id]:
            visit(dependency)
        visiting.remove(case_id)
        visited.add(case_id)

    for case_id in contracts:
        visit(case_id)
    return _digest(payload), contracts


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=project_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise QualificationError(result.stderr.strip() or "Git qualification check failed")
    return result.stdout.strip()


def _source_binding_errors(
    task_id: str, source_commit: str, manifest_relative: str, config: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    head = _git("rev-parse", "HEAD")
    try:
        _git("merge-base", "--is-ancestor", source_commit, head)
    except QualificationError:
        errors.append("qualification source_commit is not reachable from HEAD")
        return errors
    active_relative = f"harness/specs/active/{task_id}.md"
    introduction = _git("log", "--diff-filter=A", "--format=%H", "--", active_relative)
    baseline = [value for value in introduction.splitlines() if value]
    if not baseline:
        errors.append("qualification active spec introduction commit is unavailable")
    else:
        try:
            _git("merge-base", "--is-ancestor", baseline[-1], source_commit)
        except QualificationError:
            errors.append("qualification source_commit predates the active spec")
    changed = [
        value
        for value in _git("diff", "--name-only", "-z", f"{source_commit}..{head}").split("\0")
        if value
    ]
    qualifications = config.get("verification", {}).get("qualifications", {})
    prefixes = tuple(str(value) for value in qualifications.get("runtime_source_prefixes", []))
    files = {str(value) for value in qualifications.get("runtime_source_files", [])}
    risky = sorted(
        path
        for path in changed
        if (path in files or path.startswith(prefixes)) and path != f"harness/{manifest_relative}"
    )
    if risky:
        errors.append(
            "qualification source has unqualified runtime/deploy changes: "
            + ", ".join(risky[:8])
        )
    return errors


def validate_task_qualification(
    task_id: str,
    *,
    now: datetime | None = None,
    active: bool = True,
    config: dict[str, Any] | None = None,
) -> tuple[list[str], dict[str, Any] | None]:
    config = config or load_config()
    definition = _task_config(task_id, config)
    if definition is None:
        return [], None
    errors: list[str] = []
    try:
        manifest_path = _configured_path(definition["manifest"], "qualification manifest")
        profile_path = _configured_path(definition["profile"], "qualification profile")
        suite_path = _configured_path(definition["case_suite"], "qualification case suite")
        qualifications = config.get("verification", {}).get("qualifications", {})
        keys_path = _configured_path(
            qualifications.get("trusted_public_keys"), "qualification public keys"
        )
        manifest = _object(_load_json(manifest_path), "qualification manifest")
        profile_hash = _profile_digest(profile_path)
        suite_hash, case_contracts = _case_suite(suite_path)
        facts = verify_manifest(
            manifest,
            _object(_load_json(keys_path), "qualification public keys"),
            expected_task_id=task_id,
            expected_profile_digest=profile_hash,
            expected_case_suite_digest=suite_hash,
            expected_case_ids=set(case_contracts),
            expected_case_contracts=case_contracts,
            active=active,
            now=now,
        )
        errors.extend(
            _source_binding_errors(
                task_id,
                manifest["source_commit"],
                str(definition["manifest"]),
                config,
            )
            if active
            else []
        )
        bindings = {
            "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "profile_digest": profile_hash,
            "case_suite_digest": suite_hash,
            "qualification_state": facts["state"],
            "source_commit": manifest["source_commit"],
            "artifact_digest": manifest["artifact_digest"],
            "expires_at": manifest["expires_at"],
            "active_freshness_enforced": active,
        }
        return errors, bindings
    except (QualificationError, OSError, ValueError) as error:
        errors.append(str(error))
        return errors, None


def validate_repository_manifests(now: datetime | None = None) -> list[str]:
    config = load_config()
    qualifications = config.get("verification", {}).get("qualifications", {})
    tasks = qualifications.get("tasks", {}) if isinstance(qualifications, dict) else {}
    errors: list[str] = []
    if not isinstance(tasks, dict):
        return ["verification.qualifications.tasks must be a table"]
    for task_id, raw in sorted(tasks.items()):
        try:
            definition = _object(raw, f"qualification task {task_id}")
            manifest_path = _configured_path(definition.get("manifest"), "qualification manifest")
        except QualificationError as error:
            errors.append(f"{task_id}: {error}")
            continue
        if not manifest_path.exists():
            continue
        active = (harness_root() / "specs" / "active" / f"{task_id}.md").is_file()
        task_errors, _ = validate_task_qualification(
            task_id,
            now=now,
            active=active,
            config=config,
        )
        errors.extend(f"{task_id}: {error}" for error in task_errors)
    return errors


def sign_manifest_file(input_path: Path, private_key_path: Path, output_path: Path) -> None:
    manifest = _object(_load_json(input_path), "unsigned qualification manifest")
    private_key = _object(_load_json(private_key_path), "qualification private key")
    signed = sign_manifest(manifest, private_key)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(signed, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
