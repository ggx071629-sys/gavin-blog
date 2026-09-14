from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, TypedDict, cast

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from ..assistant_resume.storage import usable_version
from .article_tools import (
    ArticleToolSelection,
    bind_article_tool_model,
    execute_article_tool,
    tool_prompt,
    wants_article_tool,
)
from .constants import (
    ATTEMPT_SENDING,
    ATTEMPT_SUCCEEDED,
    ATTEMPT_UNKNOWN,
    CODE_INPUT_BUDGET_EXCEEDED,
    CODE_INSUFFICIENT_EVIDENCE,
    CODE_PROMPT_BLOCKED,
    CODE_PROVIDER_UNKNOWN,
    ESTIMATOR_VERSION,
    GENERIC_ERROR_MESSAGE,
    INSUFFICIENT_EVIDENCE_MESSAGE,
    KIND_CHAT,
    KIND_QUERY_EMBEDDING,
    POLICY_VERSION,
    STAGE_CHECKING,
    STAGE_COMPOSING,
    STAGE_RETRIEVING,
    STAGE_VALIDATING,
    TERMINAL_ANSWER,
    TERMINAL_ERROR,
    TERMINAL_REFUSAL,
)
from .crypto import digest
from .hydrate import hydrate_descriptors, hydrate_evidence
from .identity import ExecutionIdentity, publish_receipt_valid
from .money import tokens_cost_micro
from .output import validate_model_answer
from .preflight import preflight_question
from .prompt import build_prompt
from .providers import LocalDeepSeekChatOpenAI, ModelAnswer, bind_answer_model
from .question_scope import preferred_page, scope_code
from .reference_context import needs_reference, reference_is_current, resolve_reference
from .store import (
    get_attempt,
    json_dumps,
    latest_attempt,
    list_attempts,
    mark_attempt_sending,
    persist_event,
    record_activity_event,
    settle_attempt,
    write_terminal,
)

logger = logging.getLogger("gavin.assistant")


class AssistantState(TypedDict, total=False):
    session_id: str
    turn_id: str
    thread_id: str
    question: str
    current_path: str | None
    reference_source: dict[str, Any] | None
    reference_invalid: bool
    article_tool: bool
    fencing_token: str
    fencing_epoch: int
    operational_epoch: int
    dense_skipped: bool
    generation_id: int | None
    evidence: list[dict[str, Any]]
    degraded: bool
    e5_query_overlong: bool
    generation_count: int
    provider_attempt_id: str | None
    query_attempt_id: str | None
    reservation_micro: int
    query_reservation_micro: int
    parsed: bool | None
    retry_reason: str | None
    candidate_count: int
    isolated_count: int
    terminal: dict[str, Any] | None


def build_graph(online: Any):
    graph = StateGraph(AssistantState)

    async def residual_guard(state: AssistantState) -> dict[str, Any]:
        await _emit(online, state, STAGE_CHECKING)
        result = preflight_question(state["question"])
        if result.blocked:
            return await _terminal(
                online,
                state,
                TERMINAL_REFUSAL,
                result.code or CODE_PROMPT_BLOCKED,
                result.message,
            )
        if wants_article_tool(state['question']):
            return {'article_tool': True, 'generation_count': 0, 'evidence': []}
        if code := scope_code(state['question']):
            message = ('召回片段不能证明全站完整清单或总数，请限定具体来源或范围。'
                       if code == 'completeness_unverified'
                       else '当前证据未核验全局最新状态或任职时效，请限定来源与事实时间。')
            return await _terminal(online, state, TERMINAL_REFUSAL, code, message)
        if needs_reference(state['question']):
            reference = await online.retrieval_io.run(lambda: resolve_reference(online, state))
            if reference is None:
                return await _terminal(
                    online, state, TERMINAL_REFUSAL, 'clarification_required',
                    '请明确具体的文章、项目或来源；目前无法唯一确定指代对象。',
                )
            return {'reference_source': reference}
        return {'reference_source': None}

    async def construct_query(state: AssistantState) -> dict[str, Any]:
        if state.get("terminal"):
            return {}
        return {"generation_count": 0, "evidence": []}

    async def retrieve_node(state: AssistantState) -> dict[str, Any]:
        if state.get("terminal"):
            return {}
        await _emit(online, state, STAGE_RETRIEVING)
        # Sessions and synchronous clients remain entirely inside the worker.
        # Copy graph state: the worker returns descriptors, never mutates checkpoint state.
        worker_state = cast(AssistantState, dict(state))
        return await online.retrieval_io.run(lambda: _retrieve_sync(online, worker_state))

    async def evidence_gate(state: AssistantState) -> dict[str, Any]:
        if state.get("terminal"):
            return {}
        if state.get('reference_invalid'):
            return await _terminal(
                online, state, TERMINAL_REFUSAL, 'clarification_required',
                '原指代来源已失效，请明确当前公开来源。',
            )
        if len(state.get("evidence") or []) < 1:
            _diagnostic(online, state, "retrieving", "no_usable_evidence")
            import re

            message = INSUFFICIENT_EVIDENCE_MESSAGE
            if re.search(r"简历|履历|\b(?:resume|résumé|cv)\b", state["question"], re.I):
                with online.content_session() as db:
                    if usable_version(db) is None:
                        message += " 简历当前不可用。"
            return await _terminal(
                online,
                state,
                TERMINAL_REFUSAL,
                CODE_INSUFFICIENT_EVIDENCE,
                message,
            )
        return {}

    async def generate_node(state: AssistantState) -> dict[str, Any]:
        if state.get("terminal"):
            return {}
        await _emit(online, state, STAGE_COMPOSING)
        slot = int(state.get("generation_count") or 0)
        attempts = online.control.immediate(
            lambda conn: list_attempts(conn, state["turn_id"], KIND_CHAT)
        )
        if slot >= len(attempts):
            return await _terminal(
                online,
                state,
                TERMINAL_ERROR,
                CODE_PROVIDER_UNKNOWN,
                GENERIC_ERROR_MESSAGE,
            )
        existing = attempts[slot]
        if existing["status"] == ATTEMPT_UNKNOWN:
            return await _terminal(
                online,
                state,
                TERMINAL_ERROR,
                CODE_PROVIDER_UNKNOWN,
                GENERIC_ERROR_MESSAGE,
            )
        attempt_id = existing["id"]
        fingerprint = digest(state["question"] + str(slot))
        max_cost = int(existing["max_cost_micro"])
        gate = getattr(online, "pause_before_send", None)
        if gate is not None:
            await asyncio.to_thread(gate.wait, 15)

        if state.get('article_tool'):
            messages = tool_prompt(
                state['question'], retry_reason=state.get('retry_reason'),
                max_input=int(online.settings.assistant_chat_max_input_tokens),
                max_output=int(online.settings.assistant_chat_max_output_tokens),
                context_window=int(online.settings.assistant_chat_context_window_tokens),
            )
            selected_evidence = []
        else:
            db = online.content_session()
            try:
                reference = state.get('reference_source')
                if reference and not reference_is_current(db, reference):
                    return await _terminal(
                        online, state, TERMINAL_REFUSAL, 'clarification_required',
                        '原指代来源已失效，请明确当前公开来源。',
                    )
                evidence = hydrate_descriptors(db, list(state.get("evidence") or []))
                resume_available = usable_version(db) is not None
            finally:
                db.close()
            if len(evidence) != len(state.get("evidence") or []):
                return await _terminal(
                    online, state, TERMINAL_REFUSAL, CODE_INSUFFICIENT_EVIDENCE,
                    INSUFFICIENT_EVIDENCE_MESSAGE,
                )
            prompt = build_prompt(
                question=state["question"], evidence=evidence, history=[],
                reference_title=(state.get('reference_source') or {}).get('title'),
                provider=online.chat,
                max_input_tokens=int(online.settings.assistant_chat_max_input_tokens),
                max_output_tokens=int(online.settings.assistant_chat_max_output_tokens),
                context_window_tokens=int(online.settings.assistant_chat_context_window_tokens),
                resume_available=resume_available, retry_reason=state.get("retry_reason"),
            )
            messages = prompt.messages if prompt is not None else None
            selected_evidence = [item.descriptor() for item in prompt.evidence] if prompt else []
        if messages is None:
            return await _terminal(
                online,
                state,
                TERMINAL_ERROR,
                CODE_INPUT_BUDGET_EXCEEDED,
                "Retrieved evidence and question exceed the configured model input budget; "
                "no further model request was sent.",
            )
        if existing["status"] == ATTEMPT_SUCCEEDED and existing.get("parsed_json"):
            return {
                "parsed": True,
                "provider_attempt_id": existing["id"],
                "generation_count": slot + 1,
                "evidence": selected_evidence,
            }

        from .operational import validate_enabled_binding

        try:
            gate = online.control.immediate(
                lambda conn: validate_enabled_binding(
                    conn,
                    settings=online.settings,
                    generation=online.active_generation(),
                    now=online.now(),
                    admin=str(state["session_id"]).startswith("admin_"),
                )
            )
            if gate.get("_blocked"):
                return {"terminal": {"event": TERMINAL_ERROR, "code": CODE_PROVIDER_UNKNOWN}}
        except Exception:
            logger.warning("assistant provider gate check failed", exc_info=True)
            return {"terminal": {"event": TERMINAL_ERROR, "code": CODE_PROVIDER_UNKNOWN}}

        def _prepare(conn):
            from .total_budget import attempt_permitted

            if not attempt_permitted(online, attempt_id):
                raise RuntimeError("common reservation is no longer active")
            if not mark_attempt_sending(
                conn,
                attempt_id=attempt_id,
                fencing_token=state["fencing_token"],
                now=online.now(),
                request_fingerprint=fingerprint,
                identity=_identity(state),
            ):
                raise RuntimeError("attempt already sending")

        try:
            online.control.immediate(_prepare)
        except Exception:
            logger.warning("assistant attempt prepare failed", exc_info=True)
            return await _terminal(
                online,
                state,
                TERMINAL_ERROR,
                CODE_PROVIDER_UNKNOWN,
                GENERIC_ERROR_MESSAGE,
            )
        call_started = time.perf_counter()
        try:
            bound = (bind_article_tool_model(online.chat) if state.get('article_tool')
                     else bind_answer_model(online.chat))
            result = await bound.ainvoke(messages)
            if result is None or (
                isinstance(result, dict)
                and result.get("raw") is None
                and result.get("parsed") is None
            ):
                raise RuntimeError("provider result unobserved")
        except Exception as exc:
            _diagnostic(online, state, "composing", "provider_unknown")
            logger.warning("assistant provider invocation failed type=%s", type(exc).__name__)
            refreshed = online.control.read(lambda conn: get_attempt(conn, attempt_id))
            if refreshed:
                online.control.immediate(
                    lambda conn: settle_attempt(
                        conn,
                        attempt=refreshed,
                        status=ATTEMPT_UNKNOWN,
                        settled_micro=max_cost,
                        now=online.now(),
                        open_circuit=True,
                        latency_ms=_elapsed_ms(call_started),
                    )
                )
            return await _terminal(
                online,
                state,
                TERMINAL_ERROR,
                CODE_PROVIDER_UNKNOWN,
                GENERIC_ERROR_MESSAGE,
            )
        raw = result.get("raw") if isinstance(result, dict) else None
        parsed = result.get("parsed") if isinstance(result, dict) else result
        finish, usage = _usage_from_raw(raw)
        settled, circuit = _settle_chat(online, usage, max_cost)
        usage_known = usage.get("usage_source") == "provider-response"
        parsed_dump = (
            parsed.model_dump() if parsed is not None and hasattr(parsed, "model_dump") else None
        )
        refreshed = online.control.read(lambda conn: get_attempt(conn, attempt_id))
        body_committed = False
        if refreshed:
            body_committed = online.control.immediate(
                lambda conn: settle_attempt(
                    conn,
                    attempt=refreshed,
                    # A returned response is observed even when its schema is invalid.
                    status=ATTEMPT_SUCCEEDED,
                    settled_micro=settled,
                    usage_json=json_dumps(usage),
                    finish_reason=finish,
                    parsed_json=json_dumps(parsed_dump) if parsed_dump else None,
                    now=online.now(),
                    open_circuit=circuit,
                    provider_fact_status=None if usage_known else "unknown",
                    provider_fact_reason=None if usage_known else "provider_usage_unknown",
                    provider_fact_outcome=None if usage_known else "unknown",
                    metered_outcome=None if usage_known else "unknown",
                    latency_ms=_elapsed_ms(call_started),
                )
            )
        if not body_committed:
            return {"terminal": {"event": TERMINAL_ERROR, "code": CODE_PROVIDER_UNKNOWN}}
        return {
            "parsed": bool(parsed_dump),
            "provider_attempt_id": attempt_id,
            "generation_count": slot + 1,
            "finish_reason": finish,
            "evidence": selected_evidence,
        }

    async def validate_node(state: AssistantState) -> dict[str, Any]:
        if state.get("terminal"):
            return {}
        await _emit(online, state, STAGE_VALIDATING)
        parsed_dump = state.get("parsed")
        if not parsed_dump:
            _diagnostic(online, state, "validating", "format")
            if int(state.get("generation_count") or 0) < 2:
                return {"parsed": None, "retry_reason": "format"}
            return await _terminal(
                online,
                state,
                TERMINAL_ERROR,
                "output_invalid",
                GENERIC_ERROR_MESSAGE,
            )
        provider_attempt_id = state.get("provider_attempt_id")
        attempt = online.control.immediate(
            lambda conn: get_attempt(conn, provider_attempt_id) if provider_attempt_id else None
        )
        if attempt is None or not attempt.get("parsed_json"):
            return await _terminal(
                online,
                state,
                TERMINAL_ERROR,
                CODE_PROVIDER_UNKNOWN,
                GENERIC_ERROR_MESSAGE,
            )
        import json

        if state.get('article_tool'):
            selection = ArticleToolSelection.model_validate_json(attempt['parsed_json'])
            if selection.arguments is None and attempt.get('finish_reason') == 'stop':
                return await _terminal(
                    online, state, TERMINAL_REFUSAL, 'clarification_required',
                    '可以查询最近发布或更新的公开文章（最多10篇），以及今天、本周、最近7天。'
                    '请明确查询方式；当前工具不支持按主题筛选、任意日期范围或内容分析。',
                )
            if attempt.get('finish_reason') != 'tool_calls':
                return await _terminal(
                    online, state, TERMINAL_ERROR, 'output_invalid', GENERIC_ERROR_MESSAGE,
                )
            return await _terminal(
                online, state, TERMINAL_ANSWER, 'answered', '', article_selection=selection,
            )
        parsed = ModelAnswer.model_validate(json.loads(attempt["parsed_json"]))
        db = online.content_session()
        try:
            live = hydrate_descriptors(db, list(state.get("evidence") or []))
            resume_available = usable_version(db) is not None
        finally:
            db.close()
        if len(live) < 1:
            _diagnostic(online, state, "validating", "evidence_revoked")
            return await _terminal(
                online,
                state,
                TERMINAL_REFUSAL,
                CODE_INSUFFICIENT_EVIDENCE,
                INSUFFICIENT_EVIDENCE_MESSAGE,
            )
        finish = "stop"
        if attempt:
            finish = attempt.get("finish_reason") or "stop"
        if (
            isinstance(online.chat, LocalDeepSeekChatOpenAI)
            and not parsed.blocks
            and finish == "stop"
        ):
            _diagnostic(online, state, "validating", "model_abstained")
            return await _terminal(
                online,
                state,
                TERMINAL_REFUSAL,
                CODE_INSUFFICIENT_EVIDENCE,
                INSUFFICIENT_EVIDENCE_MESSAGE,
            )
        validated = validate_model_answer(
            parsed, live, finish_reason=finish, resume_available=resume_available,
            question=state["question"],
        )
        if isinstance(validated, str):
            _diagnostic(online, state, "validating", validated)
            if int(state.get("generation_count") or 0) < 2:
                online.control.immediate(
                    lambda conn: conn.execute(
                        "UPDATE assistant_attempts SET parsed_json = NULL WHERE id = ?",
                        (state.get("provider_attempt_id"),),
                    )
                )
                return {"parsed": None, "retry_reason": validated}
            code = (
                "output_rejected" if validated in {"grounding", "citation", "relevance"}
                else "output_invalid"
            )
            event = TERMINAL_REFUSAL if code == CODE_INSUFFICIENT_EVIDENCE else TERMINAL_ERROR
            message = (
                INSUFFICIENT_EVIDENCE_MESSAGE
                if event == TERMINAL_REFUSAL
                else GENERIC_ERROR_MESSAGE
            )
            return await _terminal(online, state, event, code, message)
        if state.get("provider_attempt_id"):
            online.control.immediate(
                lambda conn: conn.execute(
                    "UPDATE assistant_attempts SET parsed_json = NULL WHERE id = ?",
                    (state["provider_attempt_id"],),
                )
            )
        return await _terminal(
            online,
            state,
            TERMINAL_ANSWER,
            "answered",
            validated.text,
            answer=validated.text,
            citations=validated.citations,
            sources=validated.sources,
            history=True,
            descriptors=list(state.get("evidence") or []),
            resume_notice=validated.resume_notice,
        )

    def after_guard(state: AssistantState) -> str:
        if state.get('terminal'):
            return END
        return 'generate' if state.get('article_tool') else 'construct_query'

    def after_evidence(state: AssistantState) -> str:
        return END if state.get("terminal") else "generate"

    def after_validate(state: AssistantState) -> str:
        if state.get("terminal"):
            return END
        if state.get("parsed") is None and int(state.get("generation_count") or 0) < 2:
            return "generate"
        return END

    def observed(stage, node):
        async def run(state):
            started = time.perf_counter()
            result = {}
            outcome = "error"
            try:
                result = await node(state)
                outcome = "terminal" if result.get("terminal") else "completed"
                return result
            except asyncio.CancelledError:
                outcome = "cancelled"
                raise
            finally:
                merged = {**state, **result}
                slot = int(merged.get("generation_count") or 0)
                elapsed = _elapsed_ms(started)
                online.control.immediate(lambda conn: record_activity_event(
                    conn, event_id=f"{state['turn_id']}:stage:{stage}:{slot}",
                    kind=f"stage_{stage}", outcome=outcome, now=online.now(), latency_ms=elapsed,
                ))
                descriptors = merged.get("evidence") or []
                logger.info(
                    "assistant_stage turn_id=%s stage=%s attempt=%d outcome=%s latency_ms=%d "
                    "candidates=%d isolated=%d selected=%d generation=%s "
                    "policy=%s estimator=%s evidence_version_digest=%s",
                    state['turn_id'], stage, slot, outcome, elapsed,
                    int(merged.get('candidate_count') or 0),
                    int(merged.get('isolated_count') or 0),
                    len(descriptors), merged.get('generation_id'),
                    POLICY_VERSION, ESTIMATOR_VERSION,
                    digest('|'.join(str(d.get('source_version', '')) for d in descriptors)),
                )
        return run

    graph.add_node("residual_guard", observed("checking", residual_guard))
    graph.add_node("construct_query", construct_query)
    graph.add_node("retrieve", observed("retrieving", retrieve_node))
    graph.add_node("evidence_gate", observed("evidence_gate", evidence_gate))
    graph.add_node("generate", observed("composing", generate_node))
    graph.add_node("validate", observed("validating", validate_node))
    graph.add_edge(START, "residual_guard")
    graph.add_conditional_edges(
        "residual_guard", after_guard,
        {"construct_query": "construct_query", "generate": "generate", END: END}
    )
    graph.add_edge("construct_query", "retrieve")
    graph.add_edge("retrieve", "evidence_gate")
    graph.add_conditional_edges("evidence_gate", after_evidence, {"generate": "generate", END: END})
    graph.add_edge("generate", "validate")
    graph.add_conditional_edges("validate", after_validate, {"generate": "generate", END: END})
    return graph.compile(checkpointer=online.saver)


def _identity(state: AssistantState) -> ExecutionIdentity:
    return ExecutionIdentity(
        session_id=state["session_id"],
        fencing_epoch=int(state["fencing_epoch"]),
        turn_id=state["turn_id"],
        thread_id=state["thread_id"],
        fencing_token=state["fencing_token"],
        operational_epoch=int(state["operational_epoch"]),
    )


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.perf_counter() - started) * 1000))


def _diagnostic(online, state: AssistantState, stage: str, reason: str) -> None:
    from .prompt import RETRY_REASONS

    if stage not in {"retrieving", "validating", "composing"} or reason not in (
        RETRY_REASONS
        | {"no_usable_evidence", "evidence_revoked", "model_abstained", "provider_unknown"}
    ):
        raise ValueError("unknown diagnostic classification")
    online.control.immediate(lambda conn: record_activity_event(
        conn,
        event_id=f"{state['turn_id']}:{stage}:{int(state.get('generation_count') or 0)}:{reason}",
        kind=f"diagnostic_{stage}", outcome=reason, now=online.now(),
    ))


def _retrieval_query(
    current_question: str, history_questions: list[str], *, max_chars: int = 1000
) -> str:
    current = str(current_question)[:max_chars]
    remaining = max_chars - len(current)
    selected: list[str] = []
    for question in reversed(history_questions):
        available = remaining - 1
        if available <= 0:
            break
        text = str(question)
        fragment = text if len(text) <= available else text[-available:]
        selected.append(fragment)
        remaining -= len(fragment) + 1
        if len(fragment) != len(text):
            break
    # FTS keeps a bounded prefix of terms. Current question first, then most
    # recent history, so older context cannot evict the new topic.
    return " ".join([current, *selected])


def _reusable_query_vector(
    online, attempt: dict[str, Any], retrieval_query: str
) -> list[float] | None:
    raw = attempt.get("vector_json")
    if not raw or attempt.get("request_fingerprint") != digest(retrieval_query):
        if raw:
            online.control.immediate(
                lambda conn: conn.execute(
                    "UPDATE assistant_attempts SET vector_json = NULL, updated_at = ? WHERE id = ?",
                    (online.now(), attempt["id"]),
                )
            )
        return None
    try:
        import json

        vector = json.loads(raw)
        return [float(value) for value in vector]
    except (TypeError, ValueError):
        online.control.immediate(
            lambda conn: conn.execute(
                "UPDATE assistant_attempts SET vector_json = NULL, updated_at = ? WHERE id = ?",
                (online.now(), attempt["id"]),
            )
        )
        return None


async def _emit(online, state: AssistantState, stage: str) -> None:
    identity = _identity(state)
    async with online.serialization.hold(identity.session_id):
        event = online.control.immediate(
            lambda conn: persist_event(
                conn,
                turn_id=state["turn_id"],
                event_name=stage,
                data={"stage": stage},
                now=online.now(),
                identity=identity,
            )
        )
        valid = bool(
            event.get("inserted")
            and online.control.read(lambda conn: publish_receipt_valid(conn, event, online.now()))
        )
        if valid:
            online.hub.publish(state["turn_id"], event["event_name"], event["data_json"])
            writer = get_stream_writer()
            writer(stage)


async def _terminal(
    online,
    state: AssistantState,
    event_name: str,
    code: str,
    message: str,
    *,
    answer: str | None = None,
    citations=None,
    sources=None,
    history: bool = False,
    descriptors: list[dict[str, Any]] | None = None,
    resume_notice: str | None = None,
    article_selection: ArticleToolSelection | None = None,
) -> dict[str, Any]:
    if state.get("e5_query_overlong") and event_name in {TERMINAL_ANSWER, TERMINAL_REFUSAL}:
        notice = "问题较长，本次仅使用关键词检索公开资料。\n\n"
        message = notice + message
        if answer is not None:
            answer = notice + answer
            code = "answered_lexical"
    identity = _identity(state)
    async with online.serialization.hold(identity.session_id):
        if article_selection is not None:
            # Read current public revisions at publication time, inside the
            # existing session fence; no catalog snapshot enters checkpoints.
            try:
                with online.content_session() as db:
                    catalog = execute_article_tool(
                        db, article_selection, online.now(), state['question'],
                    )
                message = answer = catalog.text
                citations, sources = catalog.citations, catalog.sources
                history = True
            except ValueError:
                event_name, code = TERMINAL_ERROR, 'output_rejected'
                message = GENERIC_ERROR_MESSAGE
        if descriptors is not None:
            db = online.content_session()
            try:
                live = hydrate_descriptors(db, descriptors)
                if resume_notice and usable_version(db) is not None:
                    suffix = "\n\n" + resume_notice
                    message = message.removesuffix(suffix)
                    if answer is not None:
                        answer = answer.removesuffix(suffix)
            finally:
                db.close()
            if len(live) != len(descriptors):
                event_name = TERMINAL_REFUSAL
                code = CODE_INSUFFICIENT_EVIDENCE
                message = INSUFFICIENT_EVIDENCE_MESSAGE
                answer = None
                citations = None
                sources = None
                history = False
            elif identity.session_id.startswith("admin_") and citations:
                by_alias = {item.alias: item for item in live}
                citations = [
                    {**item, "excerpt": by_alias[item["alias"]].body[:1200]}
                    for item in citations
                    if item.get("alias") in by_alias
                ]
        event = online.control.immediate(
            lambda conn: write_terminal(
                conn,
                turn_id=state["turn_id"],
                event_name=event_name,
                code=code,
                message=message,
                answer=answer,
                citations=citations,
                sources=sources,
                now=online.now(),
                identity=identity,
                history_question=state.get("question") if history else None,
                history_answer=answer if history else None,
            )
        )
        valid = bool(
            event.get("inserted")
            and online.control.read(lambda conn: publish_receipt_valid(conn, event, online.now()))
        )
        if valid:
            online.hub.publish(state["turn_id"], event["event_name"], event["data_json"])
    if valid:
        logger.info("assistant_terminal turn_id=%s event=%s code=%s",
                    state['turn_id'], event_name, code)
    return {"terminal": {"event": event_name, "code": code}}


def _usage_from_raw(raw) -> tuple[str, dict[str, Any]]:
    finish = "unknown"
    usage: dict[str, Any] = {
        "input_tokens": None,
        "output_tokens": None,
        "usage_source": "unknown",
        "model": None,
        "model_identity_source": "unknown",
        "model_version": None,
        "model_version_identity_source": "unknown",
    }
    if raw is None:
        return finish, usage
    meta = getattr(raw, "response_metadata", {}) or {}
    reported_finish = str(meta.get("finish_reason") or "").strip()
    finish = reported_finish or finish
    token_usage = meta.get("token_usage") or {}
    usage_meta = getattr(raw, "usage_metadata", None) or {}
    input_tokens = token_usage.get("prompt_tokens") or usage_meta.get("input_tokens")
    output_tokens = token_usage.get("completion_tokens") or usage_meta.get("output_tokens")
    input_tokens = int(input_tokens) if input_tokens is not None else None
    output_tokens = int(output_tokens) if output_tokens is not None else None
    reported_model = str(meta.get("model_name") or meta.get("model") or "").strip()
    reported_version = str(meta.get("model_version") or "").strip()
    usage = {
        "input_tokens": input_tokens if input_tokens and input_tokens > 0 else None,
        "output_tokens": output_tokens if output_tokens and output_tokens > 0 else None,
        "usage_source": (
            "provider-response"
            if input_tokens and input_tokens > 0 and output_tokens and output_tokens > 0
            else "unknown"
        ),
        "model": reported_model or None,
        "model_identity_source": "provider-response" if reported_model else "unknown",
        "model_version": reported_version or None,
        "model_version_identity_source": ("provider-response" if reported_version else "unknown"),
    }
    return finish, usage


def _settle_chat(online, usage: dict[str, Any], max_cost: int) -> tuple[int, bool]:
    settings = online.settings
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
        return max_cost, True
    known = tokens_cost_micro(
        input_tokens,
        settings.assistant_chat_input_price_cny_per_million,
    ) + tokens_cost_micro(
        output_tokens,
        settings.assistant_chat_output_price_cny_per_million,
    )
    if input_tokens <= 0 or output_tokens <= 0:
        return max(known, max_cost), True
    if known > max_cost:
        return known, True
    return known, False


def _worst_chat_cost(online) -> int:
    settings = online.settings
    return 2 * (
        tokens_cost_micro(
            int(settings.assistant_chat_max_input_tokens),
            settings.assistant_chat_input_price_cny_per_million,
        )
        + tokens_cost_micro(
            int(settings.assistant_chat_max_output_tokens),
            settings.assistant_chat_output_price_cny_per_million,
        )
    )


def _retrieve_sync(online, state: AssistantState) -> dict[str, Any]:
    reference = state.get('reference_source')
    if reference:
        with online.content_session() as db:
            if not reference_is_current(db, reference):
                return {'reference_invalid': True, 'evidence': []}
    history_questions = [reference['title'] + ' ' + reference['public_path']] if reference else []
    retrieval_query = _retrieval_query(state["question"], history_questions)
    vector = None
    skip = bool(state.get("dense_skipped"))
    overlong = False
    prepare = getattr(online.embeddings, "prepare_retrieval_query", None)
    if prepare is not None:
        retrieval_query, overlong = prepare(state["question"], history_questions)
        skip = skip or overlong
    query_attempt_id = state.get("query_attempt_id")
    if query_attempt_id and not skip:
        attempt = online.control.immediate(lambda conn: get_attempt(conn, query_attempt_id))
        if attempt and attempt["status"] == ATTEMPT_SUCCEEDED:
            vector = _reusable_query_vector(online, attempt, retrieval_query)
            if vector is None:
                skip = True
        elif attempt and attempt["status"] in {ATTEMPT_UNKNOWN}:
            skip = True
        elif attempt is None or attempt["status"] != ATTEMPT_SUCCEEDED:
            skip = _run_query_embedding(online, state, retrieval_query)
            if not skip:
                attempt = online.control.immediate(
                    lambda conn: get_attempt(conn, query_attempt_id)
                )
                if attempt and attempt.get("vector_json"):
                    import json

                    vector = json.loads(attempt["vector_json"])
                else:
                    skip = True
    db = online.content_session()
    try:
        hydrated = hydrate_evidence(
            db,
            online.index_runtime,
            retrieval_query,
            limit=online.settings.assistant_retrieve_limit,
            query_vector=vector,
            skip_dense=skip,
            current_path=preferred_page(state['question'], state.get('current_path'), reference),
            max_chars=online.settings.assistant_evidence_max_chars,
        )
    finally:
        db.close()
    evidence = [item.descriptor() for item in hydrated.evidence]
    if query_attempt_id:
        online.control.immediate(
            lambda conn: conn.execute(
                "UPDATE assistant_attempts SET vector_json = NULL, updated_at = ? WHERE id = ?",
                (online.now(), query_attempt_id),
            )
        )
    return {
        "evidence": evidence,
        "degraded": hydrated.degraded,
        "generation_id": hydrated.generation_id,
        "dense_skipped": skip or hydrated.degraded,
        "e5_query_overlong": overlong,
        "candidate_count": hydrated.candidate_count,
        "isolated_count": len(hydrated.isolated_chunk_ids),
    }


def _run_query_embedding(online, state: AssistantState, retrieval_query: str) -> bool:
    """Return True when dense should be skipped. Performs at most one metered query embedding."""
    attempt = online.control.immediate(
        lambda conn: latest_attempt(conn, state["turn_id"], KIND_QUERY_EMBEDDING)
    )
    if attempt is None:
        return True
    if attempt["status"] == ATTEMPT_SUCCEEDED:
        state["query_attempt_id"] = attempt["id"]
        return False
    if attempt["status"] in {ATTEMPT_UNKNOWN, ATTEMPT_SENDING}:
        return True
    from .operational import validate_enabled_binding

    try:
        gate = online.control.immediate(
            lambda conn: validate_enabled_binding(
                conn,
                settings=online.settings,
                generation=online.active_generation(),
                now=online.now(),
                admin=str(state["session_id"]).startswith("admin_"),
            )
        )
        if gate.get("_blocked"):
            return True
    except Exception:
        logger.warning("assistant retrieval gate check failed", exc_info=True)
        return True
    from .total_budget import attempt_permitted

    if not attempt_permitted(online, attempt["id"]):
        return True
    sent = online.control.immediate(
        lambda conn: mark_attempt_sending(
            conn,
            attempt_id=attempt["id"],
            fencing_token=state["fencing_token"],
            now=online.now(),
            request_fingerprint=digest(retrieval_query),
            identity=_identity(state),
        )
    )
    if not sent:
        return True
    # Settlement must observe the sending snapshot, not the original reservation.
    attempt = online.control.read(lambda conn: get_attempt(conn, attempt['id']))
    call_started = time.perf_counter()
    try:
        usage = online.embeddings.embed_query_metered(retrieval_query)
    except Exception:
        logger.warning("assistant retrieval embedding failed", exc_info=True)
        online.control.immediate(
            lambda conn: settle_attempt(
                conn,
                attempt=attempt,
                status=ATTEMPT_UNKNOWN,
                settled_micro=attempt["max_cost_micro"],
                now=online.now(),
                open_circuit=True,
                latency_ms=_elapsed_ms(call_started),
            )
        )
        return True
    import json

    usage_known = usage.input_tokens is not None and usage.input_tokens > 0
    actual = (
        tokens_cost_micro(
            usage.input_tokens,
            online.settings.assistant_embedding_input_price_cny_per_million,
        )
        if usage_known
        else int(attempt["max_cost_micro"])
    )
    usage_payload = {
        "input_tokens": usage.input_tokens,
        "usage_source": usage.usage_source,
        "model": usage.model,
        "model_identity_source": usage.model_identity_source,
        "version": usage.version,
        "version_identity_source": usage.version_identity_source,
    }
    body_committed = online.control.immediate(
        lambda conn: settle_attempt(
            conn,
            attempt=attempt,
            status=ATTEMPT_SUCCEEDED,
            settled_micro=actual,
            usage_json=json_dumps(usage_payload),
            vector_json=json.dumps(usage.vector),
            now=online.now(),
            open_circuit=not usage_known or actual > int(attempt["max_cost_micro"]),
            provider_fact_status=None if usage_known else "unknown",
            provider_fact_reason=None if usage_known else "provider_usage_unknown",
            provider_fact_outcome=None if usage_known else "unknown",
            metered_outcome=None if usage_known else "unknown",
            latency_ms=_elapsed_ms(call_started),
        )
    )
    if not body_committed:
        return True
    state["query_attempt_id"] = attempt["id"]
    return False
