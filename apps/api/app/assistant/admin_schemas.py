from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


ObservationStatus = Literal["healthy", "degraded", "blocked", "disabled", "stale", "unknown"]
BudgetKind = Literal["chat", "query_embedding", "index_embedding"]
OperationKind = Literal["rebuild"]
OperationStatus = Literal[
    "pending",
    "running",
    "waiting",
    "catch_up",
    "ready_to_switch",
    "switch_pending",
    "switched",
    "failed",
    "abandoned",
]
TaskSourceType = Literal["article", "project", "book", "profile", "about", "resume"]
IndexTaskOperation = Literal["upsert", "delete", "purge"]
IndexTaskStatus = Literal["pending", "leased", "succeeded", "failed"]


class AdminErrorBody(StrictModel):
    code: str
    message: str


class AdminErrorEnvelope(StrictModel):
    error: AdminErrorBody


class AvailabilityRequest(StrictModel):
    enabled: bool
    expected_version: int = Field(ge=0)


class ReadinessRenewalRequest(StrictModel):
    expected_generation_id: int = Field(ge=1)
    expected_version: int = Field(ge=1)


class ReadinessRenewalResponse(StrictModel):
    qualified: Literal[True]
    generation_id: int


class RetryTaskRequest(StrictModel):
    expected_status: Literal["failed"]
    expected_version: int = Field(ge=1)
    operator_authorized: bool = False


class RebuildRequest(StrictModel):
    pass


class FinalizeRequest(StrictModel):
    expected_version: int = Field(ge=1)


class ObservedFact(StrictModel):
    status: ObservationStatus
    reason_code: str
    observed_at: str | None
    freshness_seconds: int | None
    stale: bool


class AvailabilityView(StrictModel):
    requested_state: Literal["disabled", "enabled"]
    effective_state: Literal["disabled", "enabled", "blocked"]
    version: int
    operational_epoch: int
    blocked_reason: str | None
    switch_pending_operation_id: str | None
    switch_target_generation_id: int | None
    updated_at: str | None
    draining_attempts: int


class DeploymentView(StrictModel):
    api_capability: bool
    single_api_owner: bool
    launcher_source: Literal["web_runtime_config"]
    launcher_mounted: None = None


class ManifestView(StrictModel):
    generation_id: int | None
    provider: str | None
    model: str | None
    model_version: str | None
    dimension: int | None
    pipeline_version: str | None
    collection_present: bool | None


class QueueView(StrictModel):
    pending: int
    leased: int
    succeeded: int
    failed: int
    latest_success_at: str | None


class BudgetView(StrictModel):
    kind: BudgetKind
    beijing_date: str
    cap_micro_cny: int | None
    settled_micro_cny: int | None
    reserved_micro_cny: int | None
    remaining_micro_cny: int | None
    overage_micro_cny: int | None
    circuit_open: bool | None
    calls: int | None
    input_tokens: int | None
    output_tokens: int | None
    usage_known: bool
    observed_at: str | None
    authority: Literal["runtime", "content"]


class StageActivityView(StrictModel):
    stage: str
    count: int
    latency_ms_min: int | None
    latency_ms_max: int | None


class DailyActivityView(StrictModel):
    accepted_questions: int | None
    rate_limit_decisions: int | None
    refusals: int | None
    errors: int | None
    security_events: int | None
    latency_ms_min: int | None
    latency_ms_max: int | None
    feedback_helpful: int | None = None
    feedback_unhelpful: int | None = None
    stages: list[StageActivityView] = Field(default_factory=list)


class OperationView(StrictModel):
    operation_id: str
    kind: OperationKind
    status: OperationStatus
    version: int
    generation_id: int | None
    previous_generation_id: int | None
    source_cursor: str | None
    outbox_high_water: int | None
    safe_error_code: str | None
    message: str | None
    created_at: str
    updated_at: str
    terminal_at: str | None


class AssistantAdminSnapshot(StrictModel):
    status: Literal["complete", "partial"]
    observed_at: str
    runtime_observed_at: str | None
    content_observed_at: str
    deployment: DeploymentView
    availability: AvailabilityView
    readiness: ObservedFact
    cleanup: ObservedFact
    restore: ObservedFact
    qdrant: ObservedFact
    chat_provider: ObservedFact
    embedding_provider: ObservedFact
    worker: ObservedFact
    manifest: ManifestView
    queue: QueueView
    operation: OperationView | None
    budgets: list[BudgetView]
    daily_activity: DailyActivityView


class IndexTaskView(StrictModel):
    id: int
    source_type: TaskSourceType
    source_id: int
    target_version: str
    pipeline_version: str
    operation: IndexTaskOperation
    status: IndexTaskStatus
    version: int
    attempt_count: int
    safe_error_code: str | None
    message: str | None
    parent_task_id: int | None
    operator_authorized: bool
    created_at: str
    updated_at: str


class IndexTaskList(StrictModel):
    items: list[IndexTaskView]
    limit: int
    offset: int


class RetryTaskResponse(StrictModel):
    task: IndexTaskView
    idempotent: bool
