from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status

from ..assistant.admin_operations import (
    build_snapshot,
    finalize_rebuild,
    get_operation,
    list_tasks,
    request_rebuild,
    retry_task,
    update_availability,
)
from ..assistant.admin_schemas import (
    AdminErrorEnvelope,
    AssistantAdminSnapshot,
    AvailabilityRequest,
    AvailabilityView,
    FinalizeRequest,
    IndexTaskList,
    OperationView,
    ReadinessRenewalRequest,
    ReadinessRenewalResponse,
    RebuildRequest,
    RetryTaskRequest,
    RetryTaskResponse,
)
from ..assistant.management import (
    BudgetRequest,
    ManagementTasks,
    ManagementView,
    TotalBudgetView,
    TrialSession,
    management_tasks,
    management_view,
)
from ..assistant.routes import (
    CSRF_HEADER_PARAM,
    IDEMPOTENCY_HEADER,
    LAST_EVENT_HEADER,
    QUESTION_REQUEST_BODY,
    SessionCreateResponse,
)
from ..assistant.routes import (
    ERROR_RESPONSES as TRIAL_ERRORS,
)
from ..dependencies import DbSession, require_admin, require_session_csrf
from ..models import AdminSession

router = APIRouter(prefix="/admin/assistant", tags=["admin assistant"])


def _trial_scope(request: Request, admin: AdminSession) -> None:
    request.state.assistant_admin_scope = admin.token_hash


@router.post("/trial/sessions", response_model=SessionCreateResponse)
def create_trial(
    request: Request,
    response: Response,
    admin: Annotated[AdminSession, Depends(require_session_csrf)],
):
    from ..assistant.routes import create_assistant_session

    _trial_scope(request, admin)
    return create_assistant_session(request, response)


@router.get("/trial/session", response_model=TrialSession)
def read_trial(
    request: Request,
    response: Response,
    admin: Annotated[AdminSession, Depends(require_admin)],
):
    from ..assistant.origin import require_read_metadata
    from ..assistant.routes import require_online
    from ..assistant.service import charge_envelope, load_session, session_view

    _trial_scope(request, admin)
    online = require_online(request)
    require_read_metadata(request, online.settings)
    charge_envelope(request, online)
    result = session_view(online, load_session(request, online, require_csrf=False))
    _no_store(response)
    for turn in result["turns"]:
        # Public reader feedback is not part of the existing admin trial contract.
        turn.pop("feedback", None)
        # Older catalog answers did not persist excerpts. Preserve their links
        # without inventing historical evidence or rewriting the stored answer.
        for citation in turn.get("citations") or []:
            citation.setdefault("excerpt", "")
        rows = online.control.read(
            lambda conn, turn_id=turn["turn_id"]: conn.execute(
                "SELECT status, settled_micro FROM assistant_attempts WHERE turn_id = ?", (turn_id,)
            ).fetchall()
        )
        turn["cost_micro_cny"] = (
            sum(int(row["settled_micro"]) for row in rows)
            if all(row["status"] not in {"prepared", "sending"} for row in rows)
            else None
        )
    return result


@router.post(
    "/trial/questions",
    responses={
        **TRIAL_ERRORS,
        200: {
            "description": "Administrator trial SSE with validated citation excerpts",
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
        },
    },
    openapi_extra={
        "parameters": [IDEMPOTENCY_HEADER, CSRF_HEADER_PARAM, LAST_EVENT_HEADER],
        "requestBody": QUESTION_REQUEST_BODY,
    },
)
async def ask_trial(
    request: Request,
    admin: Annotated[AdminSession, Depends(require_session_csrf)],
):
    from ..assistant.routes import ask_assistant

    _trial_scope(request, admin)
    return await ask_assistant(request)


@router.delete("/trial/session", status_code=204)
async def clear_trial(
    request: Request,
    response: Response,
    admin: Annotated[AdminSession, Depends(require_session_csrf)],
):
    from ..assistant.routes import delete_assistant_session

    _trial_scope(request, admin)
    return await delete_assistant_session(request, response)


@router.post("/emergency-stop")
def emergency_stop(
    request: Request,
    response: Response,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
):
    from ..assistant.admin_scope import stop_admin
    from ..assistant.operational import disable_gate, gate_json
    from ..assistant.routes import require_online

    online = require_online(request)

    def stop(conn):
        stop_admin(conn)
        return gate_json(disable_gate(conn, now=online.now()))

    _no_store(response)
    return online.control.immediate(stop)


@router.post("/trial/resume")
def resume_trial(
    request: Request,
    response: Response,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
):
    from ..assistant.admin_scope import (
        validate_admin_binding,
        validate_admin_recovery_conditions,
    )
    from ..assistant.routes import require_online

    online = require_online(request)
    online.control.read(
        lambda conn: validate_admin_recovery_conditions(
            conn, settings=online.settings, now=online.now(),
        )
    )
    # Only the explicit real-local lifespan installs this owner-bound callback.
    # Production continues to require externally qualified readiness.
    revalidate = getattr(request.app.state, "assistant_local_revalidate", None)
    if revalidate is not None:
        revalidate()
    online.control.immediate(
        lambda conn: validate_admin_binding(
            conn,
            settings=online.settings,
            generation=online.active_generation(),
            now=online.now(),
            resume=True,
        )
    )
    _no_store(response)
    return {"resumed": True}


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    code: {"model": AdminErrorEnvelope} for code in (400, 401, 403, 404, 409, 429, 503)
}


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.post(
    "/readiness/renew", response_model=ReadinessRenewalResponse, responses=ERROR_RESPONSES,
)
def renew_readiness(
    payload: ReadinessRenewalRequest,
    request: Request,
    response: Response,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
):
    from ..assistant.readiness_renewal import renew_index_readiness

    _no_store(response)
    return renew_index_readiness(
        getattr(request.app.state, "assistant", None),
        expected_generation_id=payload.expected_generation_id,
        expected_version=payload.expected_version,
        content_fence_held=True,
    )


@router.get("/management", response_model=ManagementView)
def get_management(
    request: Request,
    response: Response,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
) -> ManagementView:
    from ..time_utils import utc_now

    online = getattr(request.app.state, "assistant", None)
    _no_store(response)
    return management_view(
        db, request.app.state.settings, online, online.now() if online else utc_now()
    )


@router.patch("/budget", response_model=TotalBudgetView)
def patch_budget(
    payload: BudgetRequest,
    request: Request,
    response: Response,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> TotalBudgetView:
    from ..assistant.time_beijing import beijing_date
    from ..assistant.total_budget import set_cap
    from ..time_utils import utc_now

    online = getattr(request.app.state, "assistant", None)
    _no_store(response)
    return TotalBudgetView(
        **set_cap(
            db,
            request.app.state.settings,
            amount=payload.cap_micro_cny,
            expected_version=payload.expected_version,
            day=beijing_date(online.now() if online else utc_now()).isoformat(),
        )
    )


@router.get("/sync", response_model=ManagementTasks)
def get_sync(
    request: Request,
    response: Response,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    status_filter: Annotated[
        Literal["pending", "leased", "succeeded", "failed"] | None, Query(alias="status")
    ] = None,
) -> ManagementTasks:
    _no_store(response)
    online = getattr(request.app.state, "assistant", None)
    return management_tasks(db, limit=limit, offset=offset, status=status_filter,
                            runtime=online.index_runtime if online is not None else None)


@router.get("", response_model=AssistantAdminSnapshot, responses=ERROR_RESPONSES)
def get_assistant_admin(
    request: Request,
    response: Response,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
) -> AssistantAdminSnapshot:
    _no_store(response)
    return build_snapshot(
        settings=request.app.state.settings,
        online=getattr(request.app.state, "assistant", None),
        db=db,
        launcher_source="web_runtime_config",
    )


@router.patch(
    "/availability",
    response_model=AvailabilityView,
    responses=ERROR_RESPONSES,
)
def patch_availability(
    payload: AvailabilityRequest,
    request: Request,
    response: Response,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
) -> AvailabilityView:
    _no_store(response)
    return update_availability(
        getattr(request.app.state, "assistant", None),
        enabled=payload.enabled,
        expected_version=payload.expected_version,
    )


@router.get(
    "/index/tasks",
    response_model=IndexTaskList,
    responses=ERROR_RESPONSES,
)
def get_index_tasks(
    response: Response,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    status_filter: Annotated[
        Literal["pending", "leased", "succeeded", "failed"] | None,
        Query(alias="status"),
    ] = None,
) -> IndexTaskList:
    _no_store(response)
    return list_tasks(db, limit=limit, offset=offset, status=status_filter)


@router.post(
    "/index/tasks/{task_id}/retry",
    response_model=RetryTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=ERROR_RESPONSES,
)
def post_retry_task(
    task_id: int,
    payload: RetryTaskRequest,
    response: Response,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> RetryTaskResponse:
    _no_store(response)
    return retry_task(
        db,
        task_id=task_id,
        expected_version=payload.expected_version,
        expected_status=payload.expected_status,
        operator_authorized=payload.operator_authorized,
        idempotency_key=idempotency_key,
    )


@router.post(
    "/index/rebuilds",
    response_model=OperationView,
    status_code=status.HTTP_202_ACCEPTED,
    responses=ERROR_RESPONSES,
)
def post_rebuild(
    _payload: RebuildRequest,
    response: Response,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> OperationView:
    _no_store(response)
    operation, _idempotent = request_rebuild(db, idempotency_key=idempotency_key)
    return operation


@router.get(
    "/index/rebuilds/{operation_id}",
    response_model=OperationView,
    responses=ERROR_RESPONSES,
)
def get_rebuild(
    operation_id: str,
    response: Response,
    db: DbSession,
    _: Annotated[AdminSession, Depends(require_admin)],
) -> OperationView:
    _no_store(response)
    return get_operation(db, operation_id)


@router.post(
    "/index/rebuilds/{operation_id}/finalize",
    response_model=OperationView,
    responses=ERROR_RESPONSES,
)
def post_finalize(
    operation_id: str,
    payload: FinalizeRequest,
    request: Request,
    response: Response,
    _: Annotated[AdminSession, Depends(require_session_csrf)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> OperationView:
    _no_store(response)
    return finalize_rebuild(
        getattr(request.app.state, "assistant", None),
        operation_id=operation_id,
        expected_version=payload.expected_version,
        idempotency_key=idempotency_key,
    )
