from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Literal

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .admin_scope import cookie_name
from .errors import disabled, not_ready
from .origin import require_origin, require_read_metadata
from .sse import encode_sse, parse_event_payload

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.get("/resume/{version_id}", response_class=Response, responses={
    200: {"content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}}},
    404: {"description": "Resume version is not available"},
})
def resume_snapshot(version_id: str, request: Request) -> Response:
    import re

    from ..assistant_resume.storage import usable_version

    headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
    if not re.fullmatch(r"[0-9a-f]{32}", version_id):
        return Response(status_code=404, headers=headers)
    with request.app.state.database.session_factory() as db:
        version = usable_version(db)
        if version is None or version.id != version_id:
            return Response(status_code=404, headers=headers)
        body = version.pdf_bytes
    headers["Content-Disposition"] = 'attachment; filename="gavin-resume.pdf"'
    return Response(content=body, media_type="application/pdf", headers=headers)


class PublicAvailability(BaseModel):
    available: bool


@router.get("/availability", response_model=PublicAvailability)
def public_availability(request: Request, response: Response) -> PublicAvailability:
    """Passive, anonymous projection. Never creates a session or probes a provider."""
    from .money import cny_to_micro
    from .operational import validate_enabled_binding
    from .total_budget import view
    online = getattr(request.app.state, "assistant", None)
    response.headers["Cache-Control"] = "no-store"
    available = False
    if online is not None:
        try:
            online.control.read(lambda conn: validate_enabled_binding(
                conn, settings=online.settings, generation=online.active_generation(),
                now=online.now(), block_on_drift=False,
            ))
            with online.content_session() as db:
                budget = view(db, online.settings, online.beijing_day())
            chat = online.control.read(lambda conn: conn.execute(
                "SELECT reserved_micro, settled_micro, circuit_open "
                "FROM assistant_chat_budgets WHERE beijing_date = ?",
                (online.beijing_day(),),
            ).fetchone())
            chat_remaining = cny_to_micro(online.settings.assistant_chat_daily_budget_cny)
            if chat:
                chat_remaining -= chat["settled_micro"] + chat["reserved_micro"]
            available = (
                not budget["restore_locked"]
                and not (chat and chat["circuit_open"])
                and chat_remaining >= budget["chat_headroom_micro_cny"]
                and budget["remaining_micro_cny"] >= budget["question_headroom_micro_cny"]
            )
        except Exception:
            pass
    return PublicAvailability(available=available)


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class AssistantClientPolicy(BaseModel):
    question_max_chars: int
    session_idle_seconds: int
    session_absolute_seconds: int
    body_retention_seconds: int


class AssistantCitation(BaseModel):
    n: str
    alias: str | None = None
    title: str
    heading_path: str | None = None
    path: str


class AssistantSource(BaseModel):
    n: str
    title: str
    heading_path: str | None = None
    path: str


class SessionCreateResponse(BaseModel):
    session_id: str
    csrf_token: str
    idle_expires_at: str
    absolute_expires_at: str
    policy: AssistantClientPolicy


class SessionTurn(BaseModel):
    turn_id: str
    created_at: str
    status: str | None = None
    code: str | None = None
    message: str | None = None
    question: str | None = None
    answer: str | None = None
    citations: list[AssistantCitation] | None = None
    sources: list[AssistantSource] | None = None
    body_available: bool = True
    feedback: Literal["helpful", "unhelpful"] | None = None


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    value: Literal["helpful", "unhelpful"] | None


class FeedbackResponse(FeedbackRequest):
    turn_id: str


class ActiveTurn(BaseModel):
    turn_id: str
    question: str | None = None
    created_at: str
    stage: str | None = None


class SessionStatusResponse(BaseModel):
    session_id: str
    created_at: str
    idle_expires_at: str
    absolute_expires_at: str
    policy: AssistantClientPolicy
    turns: list[SessionTurn]
    active_turn: ActiveTurn | None = None


class QuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    question: str = Field(default="", max_length=2000)
    current_path: str | None = Field(default=None, max_length=300)


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorEnvelope, "description": "invalid_request"},
    401: {
        "model": ErrorEnvelope,
        "description": "assistant_session_missing|assistant_session_expired",
    },
    403: {"model": ErrorEnvelope, "description": "origin_rejected|csrf_failed"},
    409: {"model": ErrorEnvelope, "description": "idempotency_conflict|event_cursor_invalid"},
    410: {"model": ErrorEnvelope, "description": "idempotency_result_expired"},
    429: {
        "model": ErrorEnvelope,
        "description": (
            "rate_limited|concurrency_limited|budget_exhausted|stream_connection_limited"
        ),
    },
    503: {"model": ErrorEnvelope, "description": "assistant_disabled|assistant_not_ready"},
}


IDEMPOTENCY_HEADER = {
    "name": "Idempotency-Key",
    "in": "header",
    "required": True,
    "schema": {"type": "string", "minLength": 16, "maxLength": 128},
}
CSRF_HEADER_PARAM = {
    "name": "X-Assistant-CSRF",
    "in": "header",
    "required": True,
    "schema": {"type": "string"},
}
LAST_EVENT_HEADER = {
    "name": "Last-Event-ID",
    "in": "header",
    "required": False,
    "schema": {"type": "string"},
}
QUESTION_REQUEST_BODY = {
    "required": True,
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "question": {"type": "string", "maxLength": 2000},
                    "current_path": {
                        "anyOf": [{"type": "string", "maxLength": 300}, {"type": "null"}]
                    },
                },
                "required": ["question"],
            }
        }
    },
}


def require_online(request: Request):
    assistant = getattr(request.app.state, "assistant", None)
    if assistant is None:
        if request.app.state.settings.assistant_online_enabled:
            raise not_ready()
        raise disabled()
    return assistant


def _set_session_cookies(
    response: Response, request: Request, cookie: str, csrf: str | None
) -> None:
    settings = request.app.state.settings
    secure = settings.cookie_secure
    max_age = settings.assistant_session_absolute_seconds
    response.set_cookie(
        cookie_name(request),
        cookie,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
        max_age=max_age,
    )
    if csrf:
        response.set_cookie(
            cookie_name(request, csrf=True),
            csrf,
            httponly=False,
            secure=secure,
            samesite="lax",
            path="/",
            max_age=max_age,
        )


def _clear_session_cookies(response: Response, request: Request) -> None:
    response.delete_cookie(cookie_name(request), path="/")
    response.delete_cookie(cookie_name(request, csrf=True), path="/")


@router.post(
    "/sessions",
    response_model=SessionCreateResponse,
    responses=ERROR_RESPONSES,
)
def create_assistant_session(request: Request, response: Response) -> SessionCreateResponse:
    from .service import client_policy, create_session

    online = require_online(request)
    result = create_session(request, online)
    session = result["session"]
    csrf = result["csrf"] or ""
    _set_session_cookies(response, request, result["cookie"], csrf)
    response.headers["Cache-Control"] = "no-store"
    return SessionCreateResponse(
        session_id=session["id"],
        csrf_token=csrf,
        idle_expires_at=_as_iso(session["idle_expires_at"]),
        absolute_expires_at=_as_iso(session["absolute_expires_at"]),
        policy=AssistantClientPolicy(**client_policy(online.settings)),
    )


@router.get(
    "/session",
    response_model=SessionStatusResponse,
    responses=ERROR_RESPONSES,
)
def get_assistant_session(request: Request, response: Response) -> SessionStatusResponse:
    from .service import charge_envelope, load_session, session_view

    online = require_online(request)
    require_read_metadata(request, request.app.state.settings)
    charge_envelope(request, online)
    session = load_session(request, online, require_csrf=False)
    view = session_view(online, session)
    response.headers["Cache-Control"] = "no-store"
    return SessionStatusResponse(**view)


@router.delete(
    "/session",
    status_code=204,
    responses={**ERROR_RESPONSES, 202: {"model": ErrorEnvelope}},
    openapi_extra={"parameters": [CSRF_HEADER_PARAM]},
)
async def delete_assistant_session(request: Request, response: Response) -> Response:
    from .service import charge_envelope, delete_session, load_session

    online = require_online(request)
    settings = request.app.state.settings
    require_origin(request, settings, require_fetch_metadata=settings.environment == "production")
    await asyncio.to_thread(charge_envelope, request, online)
    session = load_session(request, online, require_csrf=True)
    status_code, code = await delete_session(online, session)
    response.headers["Cache-Control"] = "no-store"
    _clear_session_cookies(response, request)
    if status_code == 202:
        payload = JSONResponse(
            status_code=202,
            content={"error": {"code": code, "message": "Assistant session is revoking."}},
            headers={"Cache-Control": "no-store"},
        )
        _clear_session_cookies(payload, request)
        return payload
    response.status_code = 204
    return response


@router.put("/turns/{turn_id}/feedback", response_model=FeedbackResponse,
            responses=ERROR_RESPONSES, openapi_extra={"parameters": [CSRF_HEADER_PARAM]})
async def update_feedback(turn_id: str, payload: FeedbackRequest, request: Request,
                          response: Response) -> FeedbackResponse:
    from .feedback import set_feedback
    from .service import charge_envelope, load_session

    online = require_online(request)
    settings = request.app.state.settings
    require_origin(request, settings, require_fetch_metadata=settings.environment == "production")
    charge_envelope(request, online)
    session = load_session(request, online, require_csrf=True)
    async with online.serialization.hold(session["id"]):
        result = online.control.immediate(lambda conn: set_feedback(
            conn, session=session, turn_id=turn_id, value=payload.value, now=online.now(),
        ))
    response.headers["Cache-Control"] = "no-store"
    return FeedbackResponse(**result)


@router.post(
    "/questions",
    responses={
        **ERROR_RESPONSES,
        200: {
            "description": (
                "SSE stream of checking|retrieving|composing|validating and a terminal event"
            ),
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
        },
    },
    openapi_extra={
        "parameters": [IDEMPOTENCY_HEADER, CSRF_HEADER_PARAM, LAST_EVENT_HEADER],
        "requestBody": QUESTION_REQUEST_BODY,
    },
)
async def ask_assistant(request: Request) -> StreamingResponse:
    from .errors import invalid_request
    from .service import accept_question
    from .store import events_after

    online = require_online(request)
    content_type = (request.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise invalid_request("application/json is required")
    body = await request.body()
    if len(body) > 16 * 1024:
        raise invalid_request("request body is too large")
    try:
        raw = json.loads(body.decode("utf-8"))
        payload = QuestionRequest.model_validate(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise invalid_request("question request is invalid") from exc
    accepted = accept_question(request, online, payload.model_dump())
    turn = accepted["turn"]
    cursor = accepted["cursor"]
    ip = accepted["ip"]
    queue = online.hub.subscribe(turn["id"], ip)

    async def events():
        last_sent = cursor
        last_wire_write = time.monotonic()
        heartbeat_seconds = float(online.settings.assistant_sse_heartbeat_seconds or 15)
        try:
            replay = online.control.read(lambda conn: events_after(conn, turn["id"], cursor))
            for item in replay:
                seq = int(item["seq"])
                if seq <= last_sent:
                    continue
                if seq > last_sent + 1:
                    return
                data = parse_event_payload(item["data_json"])
                yield encode_sse(event_id=seq, event_name=item["event_name"], data=data)
                last_wire_write = time.monotonic()
                last_sent = seq
                if item["event_name"] in {"answer", "refusal", "error"}:
                    await _wait_runner_idle(online, turn["id"])
                    return
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=1.0)
                except TimeoutError:
                    turn_row = online.control.read(
                        lambda conn: conn.execute(
                            "SELECT status, terminal_event FROM assistant_turns WHERE id = ?",
                            (turn["id"],),
                        ).fetchone()
                    )
                    if turn_row and turn_row["status"] == "terminal":
                        await _wait_runner_idle(online, turn["id"])
                        return
                    if time.monotonic() - last_wire_write >= heartbeat_seconds:
                        yield ": keep-alive\n\n"
                        last_wire_write = time.monotonic()
                    continue
                if item["event"] == "_end":
                    await _wait_runner_idle(online, turn["id"])
                    return
                data = parse_event_payload(item["data"])
                seq = int(data.get("event_id") or 0)
                if seq <= last_sent:
                    continue
                if seq > last_sent + 1:
                    cursor_at_gap = last_sent
                    filled = online.control.read(
                        lambda conn, cursor=cursor_at_gap: events_after(conn, turn["id"], cursor)
                    )
                    gap_ok = True
                    for fill in filled:
                        fill_seq = int(fill["seq"])
                        if fill_seq <= last_sent:
                            continue
                        if fill_seq > last_sent + 1:
                            gap_ok = False
                            break
                        fill_data = parse_event_payload(fill["data_json"])
                        yield encode_sse(
                            event_id=fill_seq,
                            event_name=fill["event_name"],
                            data=fill_data,
                        )
                        last_wire_write = time.monotonic()
                        last_sent = fill_seq
                        if fill["event_name"] in {"answer", "refusal", "error"}:
                            await _wait_runner_idle(online, turn["id"])
                            return
                    if not gap_ok or seq > last_sent + 1:
                        return
                    if seq <= last_sent:
                        continue
                yield encode_sse(
                    event_id=seq,
                    event_name=item["event"],
                    data=data,
                )
                last_wire_write = time.monotonic()
                last_sent = seq
                if item["event"] in {"answer", "refusal", "error"}:
                    await _wait_runner_idle(online, turn["id"])
                    return
        finally:
            online.hub.unsubscribe(turn["id"], queue)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


async def _wait_runner_idle(online, turn_id: str) -> None:
    for _ in range(200):
        if turn_id not in getattr(online, "tasks", {}):
            return
        await asyncio.sleep(0.05)


def _as_iso(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)
