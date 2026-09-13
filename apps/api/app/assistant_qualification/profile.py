from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Literal
from urllib.parse import urlparse

import yaml
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

PROFILE_SCHEMA_VERSION = 3
CHAT_DAILY_BUDGET_MICRO_CNY = 2_000_000
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
REQUIRED_SOAK_SCENARIOS = frozenset(
    {
        "cold_start",
        "idle",
        "two_hr_low_traffic",
        "three_concurrent_sse",
        "qdrant_degraded",
        "fts_degraded",
        "full_rebuild",
        "segment_optimization",
        "api_restart",
        "worker_restart",
        "qdrant_restart",
        "backup",
        "continuous_run",
    }
)
_FORBIDDEN_EXACT = frozenset(
    {
        "",
        "unknown",
        "unset",
        "none",
        "null",
        "n/a",
        "na",
        "todo",
        "tbd",
        "change-me",
        "replace-me",
        "placeholder",
        "example",
        "latest",
        "stable",
        "main",
        "master",
        "head",
    }
)
_VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+){1,3}(?:[-+][0-9A-Za-z.-]+)?$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_PROFILE_ID_RE = re.compile(r"^[0-9]{8}-[a-z0-9]+(?:-[a-z0-9]+)*$")
_HEADER_RE = re.compile(r"^X-[A-Za-z0-9-]{3,80}$", re.IGNORECASE)
_ENV_REF_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")
_NAMED_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{2,255}$")


def _require_text(value: str, field: str) -> str:
    text = value.strip()
    lowered = text.lower()
    if lowered in _FORBIDDEN_EXACT:
        raise ValueError(f"{field} is missing, floating, or a placeholder")
    if "example.com" in lowered or ".invalid" in lowered:
        raise ValueError(f"{field} cannot use an example or invalid domain")
    return text


def _absolute_path(value: str, field: str) -> str:
    text = _require_text(value, field)
    if not (PurePosixPath(text).is_absolute() or PureWindowsPath(text).is_absolute()):
        raise ValueError(f"{field} must be an absolute target path")
    return text


def _private_or_loopback(value: str, field: str) -> str:
    text = _require_text(value, field)
    try:
        address = ipaddress.ip_address(text)
    except ValueError as exc:
        raise ValueError(f"{field} must be an explicit IP address") from exc
    if address.is_unspecified or address.is_multicast or not (
        address.is_loopback or address.is_private
    ):
        raise ValueError(f"{field} must bind loopback or an approved private address")
    return str(address)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Approval(StrictModel):
    approved: Literal[True]
    approved_by: str = Field(min_length=2, max_length=120)
    approved_at: AwareDatetime
    rationale: str = Field(min_length=12, max_length=2000)

    @model_validator(mode="after")
    def validate_text(self) -> Approval:
        self.approved_by = _require_text(self.approved_by, "approved_by")
        self.rationale = _require_text(self.rationale, "rationale")
        return self


class PinnedArtifact(StrictModel):
    version: str = Field(min_length=3, max_length=120)
    digest: str
    source: str = Field(min_length=3, max_length=300)

    @model_validator(mode="after")
    def pinned(self) -> PinnedArtifact:
        self.version = _require_text(self.version, "artifact version")
        if not _VERSION_RE.fullmatch(self.version):
            raise ValueError("artifact version must be an exact semantic-style version")
        self.digest = self.digest.strip().lower()
        if not _SHA256_RE.fullmatch(self.digest):
            raise ValueError("artifact digest must be sha256:<64 lowercase hex characters>")
        self.source = _require_text(self.source, "artifact source")
        return self


class SecretSource(StrictModel):
    kind: Literal["environment", "file", "systemd-credential", "container-secret"]
    reference: str = Field(min_length=3, max_length=256)
    rotation_interval_days: int = Field(ge=1, le=365)
    rotation_procedure: str = Field(min_length=12, max_length=1000)

    @model_validator(mode="after")
    def validate_reference(self) -> SecretSource:
        self.reference = _require_text(self.reference, "secret reference")
        if self.kind == "environment" and not _ENV_REF_RE.fullmatch(self.reference):
            raise ValueError("environment secret references must be variable names, not values")
        if self.kind == "file":
            self.reference = _absolute_path(self.reference, "file secret reference")
        elif self.kind != "environment" and not _NAMED_REF_RE.fullmatch(self.reference):
            raise ValueError("secret reference must be a symbolic credential name")
        self.rotation_procedure = _require_text(
            self.rotation_procedure, "secret rotation procedure"
        )
        return self


class SecretSources(StrictModel):
    administrator_password: SecretSource
    session: SecretSource
    csrf: SecretSource
    assistant_ip_hmac: SecretSource
    proxy_identity_hmac: SecretSource
    readiness: SecretSource
    qualification_signing: SecretSource
    chat_api_key: SecretSource
    embedding_api_key: SecretSource
    qdrant_api_key: SecretSource
    backup_encryption: SecretSource

    @model_validator(mode="after")
    def independent_cryptographic_sources(self) -> SecretSources:
        independent = (
            self.session,
            self.csrf,
            self.assistant_ip_hmac,
            self.proxy_identity_hmac,
            self.readiness,
            self.qualification_signing,
        )
        refs = {(item.kind, item.reference) for item in independent}
        if len(refs) != len(independent):
            raise ValueError(
                "session, CSRF, IP, proxy, readiness, and signing secrets must be independent"
            )
        return self


class HostProfile(StrictModel):
    os_name: str = Field(min_length=3, max_length=120)
    os_version: str = Field(min_length=1, max_length=120)
    architecture: Literal["x86_64", "aarch64"]
    deployment_kind: Literal["systemd", "docker-compose", "windows-service"]
    cpu_cores: Literal[2]
    memory_mib: Literal[4096]
    filesystem_type: Literal["ext4", "xfs", "btrfs", "zfs", "ntfs"]
    disk_capacity_mib: int = Field(ge=16_384)
    approved_disk_watermark_percent: int = Field(ge=50, le=90)
    ntp_service: str = Field(min_length=2, max_length=120)
    max_clock_drift_seconds: int = Field(ge=1, le=60)

    @model_validator(mode="after")
    def concrete_host(self) -> HostProfile:
        self.os_name = _require_text(self.os_name, "target OS")
        self.os_version = _require_text(self.os_version, "target OS version")
        if not _VERSION_RE.fullmatch(self.os_version):
            raise ValueError("target OS version must be pinned")
        self.ntp_service = _require_text(self.ntp_service, "NTP service")
        is_windows = self.os_name.lower().startswith("windows")
        if is_windows != (self.deployment_kind == "windows-service"):
            raise ValueError("deployment kind must match the selected operating system")
        return self


class ServiceProfile(StrictModel):
    artifact: PinnedArtifact
    os_user: str = Field(min_length=2, max_length=80)
    bind_address: str
    port: int = Field(ge=1024, le=65535)
    replicas: Literal[1]
    startup_order: int = Field(ge=1, le=20)
    graceful_shutdown_seconds: int = Field(ge=1, le=300)
    restart_policy: Literal["on-failure", "always", "unless-stopped"]
    health_path: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def private_service(self) -> ServiceProfile:
        self.os_user = _require_text(self.os_user, "service OS user")
        self.bind_address = _private_or_loopback(self.bind_address, "service bind address")
        if self.health_path is not None and not self.health_path.startswith("/"):
            raise ValueError("health_path must be an absolute URL path")
        return self


class Services(StrictModel):
    web: ServiceProfile
    api: ServiceProfile
    index_worker: ServiceProfile
    qdrant: ServiceProfile
    e5: ServiceProfile | None = None

    @model_validator(mode="after")
    def unique_owners_and_ports(self) -> Services:
        services = (self.web, self.api, self.index_worker, self.qdrant)
        if self.e5 is not None:
            services += (self.e5,)
            if self.e5.startup_order >= min(
                self.api.startup_order, self.index_worker.startup_order
            ):
                raise ValueError("E5 must start before the API and index Worker")
        ports = [service.port for service in services]
        if len(set(ports)) != len(ports):
            raise ValueError("service ports must be unique on the single target host")
        orders = [service.startup_order for service in services]
        if len(set(orders)) != len(orders):
            raise ValueError("service startup_order values must be unique")
        if not (
            self.qdrant.startup_order < self.api.startup_order
            and self.qdrant.startup_order < self.index_worker.startup_order
        ):
            raise ValueError("Qdrant must start before the API and index Worker")
        return self


class CspDisposition(StrictModel):
    mode: Literal["enforced", "report-only-risk-accepted"]
    risk_expires_at: AwareDatetime | None = None
    remediation_reference: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def explicit_risk(self) -> CspDisposition:
        if self.mode == "report-only-risk-accepted":
            if self.risk_expires_at is None or self.remediation_reference is None:
                raise ValueError("Report-Only CSP requires expiry and remediation reference")
            self.remediation_reference = _require_text(
                self.remediation_reference, "CSP remediation reference"
            )
        elif self.risk_expires_at is not None or self.remediation_reference is not None:
            raise ValueError("enforced CSP cannot carry a Report-Only risk acceptance")
        return self


class EdgeProfile(StrictModel):
    product: PinnedArtifact
    kind: Literal["reverse-proxy", "cdn-reverse-proxy"]
    domain: str = Field(min_length=4, max_length=253)
    canonical_origin: str = Field(min_length=10, max_length=300)
    public_ports: list[int] = Field(min_length=1, max_length=2)
    trusted_proxy_cidrs: list[str] = Field(min_length=1, max_length=32)
    client_ip_header: str
    tls_minimum_version: Literal["1.2", "1.3"]
    hsts_max_age_seconds: int = Field(ge=15_552_000)
    idle_timeout_seconds: int = Field(ge=2, le=3600)
    request_timeout_seconds: int = Field(ge=3, le=3600)
    heartbeat_interval_seconds: int = Field(ge=1, le=300)
    strips_untrusted_forwarding_headers: Literal[True]
    sse_buffering_disabled: Literal[True]
    csp: CspDisposition

    @model_validator(mode="after")
    def validate_edge(self) -> EdgeProfile:
        self.domain = _require_text(self.domain, "public domain").lower()
        if "." not in self.domain or ":" in self.domain or "/" in self.domain:
            raise ValueError("domain must be a concrete DNS name")
        origin = urlparse(self.canonical_origin)
        if (
            origin.scheme != "https"
            or origin.hostname != self.domain
            or origin.path not in {"", "/"}
            or origin.params
            or origin.query
            or origin.fragment
        ):
            raise ValueError("canonical_origin must be the exact HTTPS origin for domain")
        if sorted(set(self.public_ports)) != sorted(self.public_ports):
            raise ValueError("public_ports must be unique and sorted")
        if 443 not in self.public_ports or any(port not in {80, 443} for port in self.public_ports):
            raise ValueError("the public edge may expose only approved HTTP(S) ports including 443")
        if not _HEADER_RE.fullmatch(self.client_ip_header):
            raise ValueError("client_ip_header must be a dedicated X-* header")
        forbidden_headers = {"x-forwarded-for", "x-real-ip", "forwarded"}
        if self.client_ip_header.lower() in forbidden_headers:
            raise ValueError("client_ip_header must not reuse a browser-spoofable standard header")
        parsed_networks: list[str] = []
        for value in self.trusted_proxy_cidrs:
            network = ipaddress.ip_network(value, strict=False)
            if network.is_multicast or network.is_unspecified:
                raise ValueError(
                    "trusted proxy CIDRs must be explicit private or loopback networks"
                )
            if not (network.is_private or network.is_loopback):
                raise ValueError("trusted proxy CIDRs must be private or loopback")
            parsed_networks.append(str(network))
        self.trusted_proxy_cidrs = parsed_networks
        if self.heartbeat_interval_seconds >= self.idle_timeout_seconds:
            raise ValueError("SSE heartbeat interval must be below the edge idle timeout")
        return self


class StoragePaths(StrictModel):
    content_sqlite: str
    content_write_fence: str
    assistant_runtime: str
    media_root: str
    qdrant_volume: str
    qualification_root: str
    rollback_root: str

    @model_validator(mode="after")
    def local_distinct_paths(self) -> StoragePaths:
        names = tuple(self.__class__.model_fields)
        values = []
        for name in names:
            value = _absolute_path(str(getattr(self, name)), name)
            setattr(self, name, value)
            values.append(value.lower())
        if len(set(values)) != len(values):
            raise ValueError(
                "content, write fence, runtime, media, Qdrant, qualification, "
                "and rollback paths differ"
            )
        return self


class StorageProfile(StrictModel):
    media_backend: Literal["local"]
    persistent_local_filesystem: Literal[True]
    paths: StoragePaths
    content_peak_mib: int = Field(ge=1)
    media_peak_mib: int = Field(ge=1)
    runtime_peak_mib: int = Field(ge=1)
    qdrant_peak_mib: int = Field(ge=1)
    rebuild_peak_extra_mib: int = Field(ge=1)
    backup_staging_mib: int = Field(ge=1)
    rollback_reserve_mib: int = Field(ge=1)


class ProviderEndpoint(StrictModel):
    scheme: Literal["https"]
    reference: str = Field(min_length=3, max_length=256)

    @model_validator(mode="after")
    def symbolic_reference(self) -> ProviderEndpoint:
        self.reference = _require_text(self.reference, "provider endpoint reference")
        if not _NAMED_REF_RE.fullmatch(self.reference) or "https://" in self.reference.lower():
            raise ValueError("provider endpoint must be a symbolic reference, not a raw endpoint")
        return self


class ProviderIdentity(StrictModel):
    protocol: Literal["openai-compatible"]
    provider: str = Field(min_length=2, max_length=120)
    endpoint: ProviderEndpoint
    model: str = Field(min_length=2, max_length=200)
    model_version: str = Field(min_length=1, max_length=200)
    model_identity_source: Literal[
        "response", "versioned-provider-contract", "operator-declaration"
    ]
    provider_contract_reference: str | None = Field(default=None, max_length=300)
    timeout_seconds: int = Field(ge=1, le=120)
    max_concurrency: int = Field(ge=1, le=8)
    reports_usage: bool

    @model_validator(mode="after")
    def concrete_identity(self) -> ProviderIdentity:
        self.provider = _require_text(self.provider, "provider")
        self.model = _require_text(self.model, "provider model")
        self.model_version = _require_text(self.model_version, "provider model version")
        if self.model_identity_source == "versioned-provider-contract":
            if self.provider_contract_reference is None:
                raise ValueError("versioned provider identity requires a contract reference")
            self.provider_contract_reference = _require_text(
                self.provider_contract_reference, "provider contract reference"
            )
        elif self.provider_contract_reference is not None:
            raise ValueError("provider contract reference is only valid for contract identity")
        return self


class ChatProvider(ProviderIdentity):
    output_protocol: Literal[
        "provider-json-schema", "deepseek-json-object"
    ] = "provider-json-schema"
    max_concurrency: int = Field(ge=3, le=8)
    max_input_tokens: int = Field(ge=1)
    max_output_tokens: int = Field(ge=1)
    context_window_tokens: int = Field(ge=2)
    reports_finish_reason: bool
    input_price_micro_cny_per_million: int = Field(ge=0)
    output_price_micro_cny_per_million: int = Field(ge=0)

    @model_validator(mode="after")
    def context_contract(self) -> ChatProvider:
        if self.max_input_tokens + self.max_output_tokens > self.context_window_tokens:
            raise ValueError("Chat input and output reservations exceed the context window")
        return self


class EmbeddingProvider(ProviderIdentity):
    max_concurrency: int = Field(ge=1, le=8)
    dimension: int = Field(ge=8)
    max_input_tokens: int = Field(ge=1)
    max_batch_items: int = Field(ge=1, le=2048)
    input_price_micro_cny_per_million: int = Field(ge=0)

    @model_validator(mode="after")
    def concurrency_contract(self) -> EmbeddingProvider:
        from ..local_embedding.artifact import MODEL

        if self.model == MODEL:
            if self.max_concurrency != 1 or self.max_batch_items != 1:
                raise ValueError("local E5 requires batch/concurrency 1")
        elif self.max_concurrency < 4:
            raise ValueError("remote embeddings require concurrency >= 4")
        return self


class E5Profile(StrictModel):
    model_directory: str
    ca_file: str
    ca_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    model_lock_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    single_owner: Literal[True]

    @model_validator(mode="after")
    def paths(self) -> E5Profile:
        self.model_directory = _absolute_path(self.model_directory, "E5 model directory")
        self.ca_file = _absolute_path(self.ca_file, "E5 CA file")
        return self


class BudgetProfile(StrictModel):
    chat_daily_micro_cny: Literal[2_000_000]
    query_embedding_daily_micro_cny: int = Field(ge=0)
    index_embedding_daily_micro_cny: int = Field(ge=0)
    qualification_max_calls: int = Field(ge=1, le=500)
    qualification_max_micro_cny: int = Field(ge=0)
    qualification_calls_approved: Literal[True]
    beijing_budget_timezone: Literal["Asia/Shanghai"]
    missing_usage_policy: Literal["conservative-settlement-and-open-circuit"]


class Providers(StrictModel):
    chat: ChatProvider
    embedding: EmbeddingProvider
    budgets: BudgetProfile


class QdrantProfile(StrictModel):
    server: PinnedArtifact
    request_timeout_seconds: int = Field(ge=1, le=120)
    authentication_required: Literal[True]
    tls_when_not_same_host: Literal[True]
    collection_prefix: str = Field(min_length=3, max_length=51, pattern=r"^[a-z][a-z0-9_]+$")
    pipeline_version: str = Field(min_length=3, max_length=120)
    distance: Literal["Cosine"]
    vector_dimension: int = Field(ge=8)
    disk_watermark_percent: int = Field(ge=50, le=90)

    @model_validator(mode="after")
    def concrete_collection(self) -> QdrantProfile:
        self.collection_prefix = _require_text(
            self.collection_prefix, "Qdrant collection prefix"
        )
        self.pipeline_version = _require_text(self.pipeline_version, "index pipeline version")
        return self


class BackupProfile(StrictModel):
    consistency_strategy: Literal["write-fence-and-online-backup", "atomic-volume-snapshot"]
    destination_reference: str = Field(min_length=3, max_length=300)
    outside_host_failure_domain: Literal[True]
    encrypted: Literal[True]
    frequency_seconds: int = Field(ge=60)
    retention_count: int = Field(ge=2)
    rpo_seconds: int = Field(ge=60)
    rto_seconds: int = Field(ge=60)
    failure_alert_after_seconds: int = Field(ge=60)
    runtime_excluded: Literal[True]
    wal_shm_excluded: Literal[True]
    langgraph_checkpoints_excluded: Literal[True]

    @model_validator(mode="after")
    def viable_schedule(self) -> BackupProfile:
        self.destination_reference = _require_text(
            self.destination_reference, "backup destination reference"
        )
        if self.frequency_seconds > self.rpo_seconds:
            raise ValueError("backup frequency cannot exceed the approved RPO")
        return self


class RunnerTiming(StrictModel):
    provider_timeout_seconds: int = Field(ge=1, le=120)
    cleanup_margin_seconds: int = Field(ge=1, le=120)
    settlement_margin_seconds: int = Field(ge=1, le=120)
    runner_horizon_seconds: int = Field(ge=3, le=1800)


class ResourceThresholds(StrictModel):
    approval: Approval
    basis_reference: str = Field(min_length=3, max_length=300)
    full_work_cycle_seconds: int = Field(ge=60)
    soak_duration_seconds: int = Field(ge=60)
    traffic_model: str = Field(min_length=12, max_length=2000)
    scenarios: list[str] = Field(min_length=1, max_length=64)
    max_total_rss_mib: int = Field(ge=512, le=3584)
    max_sustained_cpu_percent: int = Field(ge=1, le=200)
    max_swap_mib: int = Field(ge=0, le=2048)
    max_file_descriptors: int = Field(ge=64)
    max_disk_growth_mib_per_hour: int = Field(ge=0)
    max_qdrant_p95_ms: int = Field(ge=1)
    max_fts_p95_ms: int = Field(ge=1)
    max_graph_p50_ms: int = Field(ge=1)
    max_graph_p95_ms: int = Field(ge=1)
    max_process_restarts: int = Field(ge=0)

    @model_validator(mode="after")
    def complete_cycle(self) -> ResourceThresholds:
        self.basis_reference = _require_text(self.basis_reference, "threshold basis")
        self.traffic_model = _require_text(self.traffic_model, "traffic model")
        present = set(self.scenarios)
        missing = REQUIRED_SOAK_SCENARIOS - present
        if missing:
            raise ValueError(f"soak scenarios missing: {sorted(missing)}")
        if len(present) != len(self.scenarios):
            raise ValueError("soak scenarios must be unique")
        if self.soak_duration_seconds < self.full_work_cycle_seconds:
            raise ValueError("soak must cover the complete approved work cycle")
        if self.max_graph_p95_ms < self.max_graph_p50_ms:
            raise ValueError("graph P95 threshold cannot be below P50")
        return self


class EvidenceProfile(StrictModel):
    ttl_seconds: int = Field(ge=3600, le=2_592_000)
    invalidation_paths: list[str] = Field(min_length=1, max_length=64)
    raw_artifact_location_category: Literal[
        "encrypted-off-host-object-store", "encrypted-off-host-filesystem"
    ]
    raw_artifact_retention_days: int = Field(ge=1, le=365)
    reviewer_attests_hashes: Literal[True]

    @model_validator(mode="after")
    def complete_invalidation(self) -> EvidenceProfile:
        present = set(self.invalidation_paths)
        missing = REQUIRED_INVALIDATION_PATHS - present
        if missing:
            raise ValueError(f"evidence invalidation paths missing: {sorted(missing)}")
        if len(present) != len(self.invalidation_paths):
            raise ValueError("evidence invalidation paths must be unique")
        return self


class AlertChannel(StrictModel):
    kind: Literal["email", "webhook", "pager", "host-monitor"]
    reference: str = Field(min_length=3, max_length=200)
    retention_days: int = Field(ge=1, le=365)
    drill_observation_seconds: int = Field(ge=1, le=3600)

    @model_validator(mode="after")
    def symbolic_channel(self) -> AlertChannel:
        self.reference = _require_text(self.reference, "alert channel reference")
        if not _NAMED_REF_RE.fullmatch(self.reference):
            raise ValueError("alert channel must be a symbolic reference")
        return self


class ObservabilityProfile(StrictModel):
    channels: list[AlertChannel] = Field(min_length=1, max_length=8)
    backup_max_age_seconds: int = Field(ge=60)
    tls_expiry_alert_days: int = Field(ge=1, le=90)
    worker_heartbeat_stale_seconds: int = Field(ge=1, le=3600)
    log_retention_days: int = Field(ge=1, le=90)
    raw_questions_logged: Literal[False]
    raw_answers_logged: Literal[False]
    raw_ips_logged: Literal[False]
    raw_provider_payloads_logged: Literal[False]
    provider_account_budget_alert_configured: Literal[True]


class ProviderGovernance(StrictModel):
    data_retention_policy_reference: str = Field(min_length=3, max_length=300)
    processing_region: str = Field(min_length=2, max_length=120)
    visitor_disclosure_reference: str = Field(min_length=3, max_length=300)
    raw_langsmith_tracing_enabled: Literal[False]

    @model_validator(mode="after")
    def known_policy(self) -> ProviderGovernance:
        self.data_retention_policy_reference = _require_text(
            self.data_retention_policy_reference, "provider retention policy"
        )
        self.processing_region = _require_text(self.processing_region, "processing region")
        self.visitor_disclosure_reference = _require_text(
            self.visitor_disclosure_reference, "visitor disclosure"
        )
        return self


class SafetyState(StrictModel):
    web_launcher_enabled: Literal[False]
    api_capability_enabled: Literal[False]
    runtime_gate_enabled: Literal[False]
    destructive_tests_use_isolation: Literal[True]


class QualificationProfile(StrictModel):
    schema_version: Literal[2, 3]
    profile_id: str
    profile_revision: int = Field(ge=1)
    approval: Approval
    safety: SafetyState
    host: HostProfile
    services: Services
    edge: EdgeProfile
    storage: StorageProfile
    secrets: SecretSources
    providers: Providers
    qdrant: QdrantProfile
    backup: BackupProfile
    runner_timing: RunnerTiming
    thresholds: ResourceThresholds
    evidence: EvidenceProfile
    observability: ObservabilityProfile
    governance: ProviderGovernance
    e5: E5Profile | None = None

    @model_validator(mode="after")
    def validate_cross_contract(self) -> QualificationProfile:
        from ..local_embedding.artifact import DIMENSION, MODEL, PIPELINE, VERSION

        local_e5 = self.providers.embedding.model == MODEL
        json_object = self.providers.chat.output_protocol == "deepseek-json-object"
        if self.schema_version == 2 and (
            self.e5 is not None or self.services.e5 is not None or local_e5 or json_object
        ):
            raise ValueError("E5 and DeepSeek JSON mode require profile schema 3")
        if local_e5:
            embedding = self.providers.embedding
            if self.e5 is None or self.services.e5 is None:
                raise ValueError("local E5 requires service and TLS/artifact contracts")
            if (
                embedding.model_version != VERSION
                or embedding.dimension != DIMENSION
                or embedding.max_input_tokens != 512
                or self.qdrant.pipeline_version != PIPELINE
            ):
                raise ValueError("local E5 model, dimension, token and pipeline pins differ")
        elif self.e5 is not None or self.services.e5 is not None:
            raise ValueError("E5 contracts require the pinned E5 provider")
        if not _PROFILE_ID_RE.fullmatch(self.profile_id):
            raise ValueError("profile_id must be a dated lowercase task-style identifier")
        if self.providers.chat.timeout_seconds != self.runner_timing.provider_timeout_seconds:
            raise ValueError("Chat and runner provider timeout declarations must match")
        if (
            self.providers.embedding.timeout_seconds
            != self.runner_timing.provider_timeout_seconds
        ):
            raise ValueError("Embedding and runner provider timeout declarations must match")
        if self.services.qdrant.artifact != self.qdrant.server:
            raise ValueError("Qdrant service and server artifacts must be identical")
        minimum_horizon = (
            self.runner_timing.provider_timeout_seconds
            + self.runner_timing.cleanup_margin_seconds
            + self.runner_timing.settlement_margin_seconds
        )
        if minimum_horizon > self.runner_timing.runner_horizon_seconds:
            raise ValueError("provider timeout plus cleanup and settlement exceeds runner horizon")
        if self.runner_timing.runner_horizon_seconds >= self.edge.request_timeout_seconds:
            raise ValueError("runner horizon must remain below the edge request timeout")
        if self.runner_timing.runner_horizon_seconds >= self.edge.idle_timeout_seconds:
            raise ValueError("runner horizon must remain below the edge idle timeout")
        if self.qdrant.vector_dimension != self.providers.embedding.dimension:
            raise ValueError("Qdrant and final embedding dimensions must match")
        if self.qdrant.request_timeout_seconds > self.providers.embedding.timeout_seconds:
            raise ValueError("Qdrant timeout cannot exceed the embedding provider timeout")
        used_mib = sum(
            (
                self.storage.content_peak_mib,
                self.storage.media_peak_mib,
                self.storage.runtime_peak_mib,
                self.storage.qdrant_peak_mib,
                self.storage.rebuild_peak_extra_mib,
                self.storage.backup_staging_mib,
                self.storage.rollback_reserve_mib,
            )
        )
        approved_mib = (
            self.host.disk_capacity_mib * self.host.approved_disk_watermark_percent // 100
        )
        if used_mib > approved_mib:
            raise ValueError("backup, rebuild, rollback, and data peaks exceed disk watermark")
        if self.qdrant.disk_watermark_percent > self.host.approved_disk_watermark_percent:
            raise ValueError("Qdrant disk watermark cannot exceed the host watermark")
        if self.observability.backup_max_age_seconds < self.backup.frequency_seconds:
            raise ValueError("backup age alert cannot fire before one backup interval")
        if self.evidence.ttl_seconds <= (
            self.thresholds.soak_duration_seconds + self.backup.rto_seconds
        ):
            raise ValueError("evidence TTL must outlive the soak and restore qualification window")
        return self


def canonical_profile(profile: QualificationProfile) -> bytes:
    payload = profile.model_dump(mode="json", exclude_none=False)
    if profile.schema_version == 2:
        # Adding schema 3 must not invalidate already signed schema 2 receipts.
        payload.pop("e5")
        payload["services"].pop("e5")
        payload["providers"]["chat"].pop("output_protocol")
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def profile_digest(profile: QualificationProfile) -> str:
    return "sha256:" + hashlib.sha256(canonical_profile(profile)).hexdigest()


def load_profile(path: Path) -> QualificationProfile:
    raw = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        data: Any = json.loads(raw)
    elif suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(raw)
    else:
        raise ValueError("qualification profile must be JSON or YAML")
    if not isinstance(data, dict):
        raise ValueError("qualification profile root must be an object")
    return QualificationProfile.model_validate(data)


def schema_document() -> dict[str, Any]:
    return QualificationProfile.model_json_schema()
