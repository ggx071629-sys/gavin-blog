from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from ..assistant_index.worker import ensure_pointer
from ..config import Settings, get_settings
from ..db import Database
from ..time_utils import utc_now
from .constants import ESTIMATOR_VERSION, POLICY_VERSION
from .crypto import hmac_hex, random_id
from .errors import AssistantNotReadyError
from .providers import (
    ModelAnswer,
    credential_fingerprint,
)
from .runtime_db import acquire_owner_lock, open_control
from .validation import validate_online_settings


def receipt_payload(settings: Settings, *, probed_at: datetime, generation) -> dict:
    return {
        "release_id": settings.assistant_release_id,
        "policy_version": settings.assistant_policy_version or POLICY_VERSION,
        "estimator_version": ESTIMATOR_VERSION,
        "history_turns": settings.assistant_history_turns,
        "chat_token_limits": {
            "max_input": settings.assistant_chat_max_input_tokens,
            "max_output": settings.assistant_chat_max_output_tokens,
            "context_window": settings.assistant_chat_context_window_tokens,
        },
        "chat_provider": settings.assistant_chat_provider,
        "chat_model": settings.assistant_chat_model,
        "chat_model_version": settings.assistant_chat_model_version,
        "chat_endpoint": settings.assistant_chat_endpoint,
        "embedding_provider": settings.assistant_embedding_provider,
        "embedding_model": settings.assistant_embedding_model,
        "embedding_model_version": settings.assistant_embedding_model_version,
        "embedding_endpoint": settings.assistant_embedding_endpoint,
        "embedding_dimension": settings.assistant_embedding_dimension,
        "qualification_profile_digest": settings.assistant_qualification_profile_digest,
        "provider_probe_sha256": settings.assistant_provider_probe_sha256,
        "schema_hash": ModelAnswer.model_json_schema().__str__()[:0] + _schema_hash(),
        "timeout_seconds": settings.assistant_provider_timeout_seconds,
        "chat_prices": {
            "input": str(settings.assistant_chat_input_price_cny_per_million),
            "output": str(settings.assistant_chat_output_price_cny_per_million),
        },
        "budgets": {
            "chat": str(settings.assistant_chat_daily_budget_cny),
            "query_embedding": str(settings.assistant_query_embedding_daily_budget_cny),
            "index_embedding": str(settings.assistant_index_embedding_daily_budget_cny),
        },
        "generation": {
            "id": None if generation is None else generation.id,
            "collection_name": None if generation is None else generation.collection_name,
            "distance": None if generation is None else generation.distance_metric,
            "pipeline": None if generation is None else generation.pipeline_version,
            "embedding_provider": None if generation is None else generation.embedding_provider,
            "embedding_model": None if generation is None else generation.embedding_model,
            "embedding_model_version": None
            if generation is None
            else generation.embedding_model_version,
            "dimension": None if generation is None else generation.vector_dimension,
        },
        "probed_at": probed_at.isoformat(),
        "chat_credential": credential_fingerprint(
            str(settings.assistant_readiness_hmac_secret),
            str(settings.assistant_chat_api_key),
            "chat",
        ),
        "embedding_credential": credential_fingerprint(
            str(settings.assistant_readiness_hmac_secret),
            str(settings.assistant_embedding_api_key),
            "embedding",
        ),
        "qdrant_credential": credential_fingerprint(
            str(settings.assistant_readiness_hmac_secret),
            str(settings.assistant_qdrant_api_key or settings.assistant_qdrant_path or "local"),
            "qdrant",
        ),
        "control_credentials": {
            label: credential_fingerprint(
                str(settings.assistant_readiness_hmac_secret),
                str(value),
                label,
            )
            for label, value in (
                ("session", settings.assistant_session_hmac_secret),
                ("csrf", settings.assistant_csrf_hmac_secret),
                ("ip", settings.assistant_ip_hmac_secret),
                ("proxy", settings.assistant_proxy_hmac_secret),
            )
        },
    }


def _schema_hash() -> str:
    from .crypto import digest

    return digest(json.dumps(ModelAnswer.model_json_schema(), sort_keys=True))


def write_receipt(
    settings: Settings,
    *,
    probe_live: bool,
    lock=None,
    qualification_profile: Path | None = None,
    provider_probe: Path | None = None,
    local_development: bool = False,
) -> str:
    validate_online_settings(settings)
    if local_development:
        from ..assistant_qualification.provider_probe import validate_local_chat_probe_artifact
        from .development import validate_real_development_settings

        validate_real_development_settings(settings)
        if not probe_live or provider_probe is None or qualification_profile is not None:
            raise AssistantNotReadyError("local readiness requires an explicit local probe")
        validate_local_chat_probe_artifact(provider_probe, settings)
    elif settings.assistant_chat_provider != "test":
        if not probe_live or qualification_profile is None or provider_probe is None:
            raise AssistantNotReadyError(
                "real-provider readiness requires an explicit reviewed qualification probe"
            )
        from ..assistant_qualification.profile import load_profile, profile_digest
        from ..assistant_qualification.provider_probe import (
            provider_probe_digest,
            validate_provider_probe_artifact,
        )
        from ..assistant_qualification.runtime_binding import selected_profile_path

        selected_path = selected_profile_path(settings)
        if qualification_profile.resolve() != selected_path:
            raise AssistantNotReadyError("readiness profile is not the selected production profile")
        profile = load_profile(selected_path)
        try:
            validate_provider_probe_artifact(provider_probe, profile, settings)
        except (OSError, ValueError) as exc:
            raise AssistantNotReadyError("real-provider qualification probe is invalid") from exc
        if settings.assistant_qualification_profile_digest != profile_digest(profile):
            raise AssistantNotReadyError("qualification profile readiness binding mismatch")
        if settings.assistant_provider_probe_sha256 != provider_probe_digest(provider_probe):
            raise AssistantNotReadyError("provider probe readiness binding mismatch")
    runtime_path = Path(str(settings.assistant_runtime_path))
    owned = lock is None
    lock = lock or acquire_owner_lock(runtime_path)
    try:
        control = open_control(runtime_path=runtime_path, owner="provision", verify=True)
        try:
            residue = control.read(
                lambda conn: (
                    int(conn.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0])
                    + int(conn.execute("SELECT COUNT(*) FROM writes").fetchone()[0])
                )
            )
            if residue:
                raise AssistantNotReadyError(
                    "checkpoint residue must be cleaned before readiness is signed"
                )
            database = Database(settings.database_url)
            generation = None
            with database.session_factory() as db:
                pointer = ensure_pointer(db)
                if pointer.active_generation_id is not None:
                    from ..models import AssistantIndexGeneration

                    generation = db.get(AssistantIndexGeneration, pointer.active_generation_id)
            payload = receipt_payload(settings, probed_at=utc_now(), generation=generation)
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            receipt_hmac = hmac_hex(
                str(settings.assistant_readiness_hmac_secret),
                canonical,
                context="assistant-receipt",
            )
            receipt_id = random_id()

            def _write(conn):
                conn.execute(
                    "UPDATE assistant_readiness_receipts "
                    "SET revoked_at = ? WHERE revoked_at IS NULL",
                    (utc_now(),),
                )
                conn.execute(
                    """
                    INSERT INTO assistant_readiness_receipts
                    (id, receipt_json, receipt_hmac, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (receipt_id, canonical, receipt_hmac, utc_now()),
                )

            control.immediate(_write)
            return receipt_id
        finally:
            control.dispose()
    finally:
        if owned:
            lock.release()


def verify_receipt(settings: Settings, conn, generation=None) -> None:
    from .store import current_receipt

    row = current_receipt(conn)
    if row is None:
        raise AssistantNotReadyError("readiness receipt missing")
    expected = hmac_hex(
        str(settings.assistant_readiness_hmac_secret),
        row["receipt_json"],
        context="assistant-receipt",
    )
    if expected != row["receipt_hmac"]:
        raise AssistantNotReadyError("readiness receipt HMAC mismatch")
    payload = json.loads(row["receipt_json"])
    live = receipt_payload(
        settings,
        probed_at=utc_now(),
        generation=generation,
    )
    for key in (
        "release_id",
        "policy_version",
        "estimator_version",
        "history_turns",
        "chat_token_limits",
        "chat_provider",
        "chat_model",
        "chat_model_version",
        "chat_endpoint",
        "embedding_provider",
        "embedding_model",
        "embedding_model_version",
        "embedding_endpoint",
        "embedding_dimension",
        "qualification_profile_digest",
        "provider_probe_sha256",
        "schema_hash",
        "timeout_seconds",
        "chat_prices",
        "budgets",
        "control_credentials",
    ):
        if payload.get(key) != live.get(key):
            raise AssistantNotReadyError("readiness receipt binding mismatch")
    if payload.get("chat_credential") != live.get("chat_credential"):
        raise AssistantNotReadyError("chat credential fingerprint mismatch")
    if payload.get("embedding_credential") != live.get("embedding_credential"):
        raise AssistantNotReadyError("embedding credential fingerprint mismatch")
    if payload.get("qdrant_credential") != live.get("qdrant_credential"):
        raise AssistantNotReadyError("qdrant credential fingerprint mismatch")
    if payload.get("generation") != live.get("generation"):
        raise AssistantNotReadyError("active generation compatibility mismatch")


class _Gen:
    def __init__(self, data: dict) -> None:
        self.id = data.get("id")
        self.collection_name = data.get("collection_name")
        self.distance_metric = data.get("distance")
        self.pipeline_version = data.get("pipeline")
        self.embedding_provider = data.get("embedding_provider")
        self.embedding_model = data.get("embedding_model")
        self.embedding_model_version = data.get("embedding_model_version")
        self.vector_dimension = data.get("dimension")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write an assistant readiness receipt")
    parser.add_argument("--probe-live", action="store_true")
    parser.add_argument("--qualification-profile", type=Path)
    parser.add_argument("--provider-probe", type=Path)
    args = parser.parse_args(argv)
    settings = get_settings()
    receipt_id = write_receipt(
        settings,
        probe_live=args.probe_live,
        qualification_profile=args.qualification_profile,
        provider_probe=args.provider_probe,
    )
    print(f"assistant readiness receipt {receipt_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
