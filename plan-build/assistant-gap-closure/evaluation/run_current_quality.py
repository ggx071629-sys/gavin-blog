"""Current corpus retrieval/prompt/model/validation evaluation, never production qualification.

Prepare is the default. Paid execution uses the existing cumulative signed ledger.
Raw output remains in ignored API data; no automatic retry or failed-ledger recovery.
HTTP delivery, durable runtime races and independent human grading are separate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

API_ROOT = Path(__file__).resolve().parents[3] / "apps/api"
sys.path.insert(0, str(API_ROOT))

from app.assistant.graph import _usage_from_raw  # noqa: E402
from app.assistant.hydrate import hydrate_evidence  # noqa: E402
from app.assistant.output import validate_model_answer  # noqa: E402
from app.assistant.preflight import preflight_question  # noqa: E402
from app.assistant.prompt import build_prompt  # noqa: E402
from app.assistant.providers import ModelAnswer, bind_answer_model, build_chat_model  # noqa: E402
from app.assistant.question_scope import preferred_page, scope_code  # noqa: E402
from app.assistant.reference_context import needs_reference, resolve_reference  # noqa: E402
from app.assistant_index.projector import (  # noqa: E402
    iter_public_sources,
    source_revision_set_digest,
)
from app.assistant_index.runtime import build_runtime  # noqa: E402
from app.assistant_qualification import local_ledger  # noqa: E402
from app.assistant_qualification import provider_probe as probe  # noqa: E402
from app.config import Settings  # noqa: E402
from app.db import Database  # noqa: E402

AUTHORIZATION = "assistant-gap-closure-q5-250-4-20260913"
MAX_CALLS, MAX_MICRO_CNY = 250, 4_000_000
BASE = Path(__file__).resolve().parent


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def checksum(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def validate_dataset(corpus, dataset, documents=None):
    if dataset["source_set_sha256"] != corpus["source_set_sha256"]:
        raise ValueError("dataset/corpus mismatch")
    rows = dataset["rows"]
    if not rows or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("invalid case identities")
    if {r["split"] for r in rows} != {"debug", "evaluation"}:
        raise ValueError("debug and evaluation must remain separate")
    keys = {s["key"] for s in corpus["sources"]}
    for row in rows:
        if row["expected"] == "answer" and not row["expected_support"]:
            raise ValueError("answer expectation requires support")
        for support in [
            *row["expected_support"],
            *row.get("followup", {}).get("expected_support", []),
        ]:
            if support["source"] not in keys or not support["quote"]:
                raise ValueError("unknown/empty expected support")
    if documents is not None:
        if source_revision_set_digest(documents) != corpus["source_set_sha256"]:
            raise ValueError("current corpus changed; freeze and review a new version")
        by_key = {f"{d.source_type}:{d.source_id}": d for d in documents}
        for source in corpus["sources"]:
            d = by_key[source["key"]]
            if (
                d.source_version != source["version"]
                or hashlib.sha256(d.body.encode()).hexdigest() != source["body_sha256"]
            ):
                raise ValueError("source version/body changed")
        for row in rows:
            for support in [
                *row["expected_support"],
                *row.get("followup", {}).get("expected_support", []),
            ]:
                if support["quote"] not in by_key[support["source"]].body:
                    raise ValueError("expected quote not present in fixed source")


def contract_for(settings):
    contract = probe._local_chat_contract(
        settings=settings,
        approved_max_micro_cny=MAX_MICRO_CNY,
        max_calls=MAX_CALLS,
        approved_daily_budget=Decimal("2"),
        authorization_id=AUTHORIZATION,
    )
    if (
        contract.model != "deepseek-flash"
        or contract.max_input_tokens != 32000
        or contract.max_output_tokens != 512
        or contract.input_price_micro_cny_per_million != 3_000_000
        or contract.output_price_micro_cny_per_million != 9_000_000
    ):
        raise ValueError("reviewed provider configuration changed")
    return contract


def max_cost(contract, input_tokens=None):
    return probe._micro_cost(
        contract.max_input_tokens if input_tokens is None else input_tokens,
        contract.input_price_micro_cny_per_million
    ) + probe._micro_cost(contract.max_output_tokens, contract.output_price_micro_cny_per_million)


def check_envelope(status, planned_calls, reserve):
    if (
        status["authorization_id"] != AUTHORIZATION
        or status["unresolved"]
        or planned_calls > status["calls_remaining"]
        or planned_calls * reserve > status["micro_cny_remaining"]
    ):
        raise ValueError("cumulative authorization unavailable or insufficient")


def paid_call(settings, contract, ledger, bound, messages, estimated_input):
    if type(estimated_input) is not int or not 0 < estimated_input <= contract.max_input_tokens:
        raise ValueError("invalid admitted input estimate")
    reserve = max_cost(contract, estimated_input)
    # The same signed authority validates config, all prior calls/cost and pending failures.
    attempt = probe._reserve(
        ledger,
        contract,
        kind="chat",
        settings=settings,
        reserved_micro_cny=reserve,
        now=datetime.now(UTC),
    )
    started = time.monotonic()
    try:
        response = bound.invoke(messages)
        raw = response.get("raw")
        finish, usage = _usage_from_raw(raw)
        ins, outs = usage.get("input_tokens"), usage.get("output_tokens")
        known = type(ins) is int and type(outs) is int and ins >= 0 and outs >= 0
        cost = (
            probe._micro_cost(ins, contract.input_price_micro_cny_per_million)
            + probe._micro_cost(outs, contract.output_price_micro_cny_per_million)
            if known
            else reserve
        )
        ok = (
            known
            and finish == "stop"
            and usage.get("model") == contract.model
            and ins <= estimated_input
            and outs <= contract.max_output_tokens
            and cost <= reserve
        )
        result = dict(
            transport_ok=ok,
            finish_reason=finish,
            usage=usage,
            cost_micro_cny=cost,
            reserved_micro_cny=reserve,
            elapsed_seconds=time.monotonic() - started,
            raw_output=getattr(raw, "content", ""),
            attempt_id=attempt,
        )
    except Exception as exc:
        probe._settle(
            ledger,
            contract,
            attempt_id=attempt,
            status="unknown",
            settled_micro_cny=reserve,
            settings=settings,
            now=datetime.now(UTC),
        )
        return dict(
            transport_ok=False,
            status="unknown",
            error_type=type(exc).__name__,
            elapsed_seconds=time.monotonic() - started,
            cost_micro_cny=reserve,
            reserved_micro_cny=reserve,
            attempt_id=attempt,
        ), None
    probe._settle(
        ledger,
        contract,
        attempt_id=attempt,
        status="succeeded" if ok else "measured_fail",
        settled_micro_cny=cost,
        settings=settings,
        now=datetime.now(UTC),
    )
    return result, response.get("parsed")


def reference_for(database, question, previous):
    """Exercise the production resolver against transient prior-result metadata.

    This is not a durable-session or HTTP test. The in-memory schema contains only
    fields read by the production resolver, and is discarded before returning.
    """
    now = datetime.now(UTC)
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript("""
            CREATE TABLE assistant_sessions(
              id, tombstoned_at, idle_expires_at, absolute_expires_at);
            CREATE TABLE assistant_history(id INTEGER PRIMARY KEY, session_id, turn_id);
            CREATE TABLE assistant_turns(id, created_at, terminal_at, terminal_event,
              terminal_code, terminal_message, question, answer, citations_json,
              sources_json, body_purged_at);
        """)
        expires = (now + timedelta(minutes=5)).isoformat()
        conn.execute("INSERT INTO assistant_sessions VALUES (?,NULL,?,?)", ("q5", expires, expires))
        if previous:
            conn.execute("INSERT INTO assistant_history VALUES (1,'q5','previous')")
            conn.execute(
                "INSERT INTO assistant_turns VALUES (?,?,?,?,?,?,?,?,?,?,NULL)",
                (
                    "previous",
                    now.isoformat(),
                    now.isoformat(),
                    "answer",
                    "answered",
                    "",
                    "",
                    "",
                    json.dumps(previous["citations"]),
                    json.dumps(previous["sources"]),
                ),
            )
        online = SimpleNamespace(
            now=lambda: now,
            content_session=database.session_factory,
            control=SimpleNamespace(read=lambda fn: fn(conn)),
        )
        return resolve_reference(online, dict(question=question, session_id="q5"))
    finally:
        conn.close()


def prepare_case(row, database, runtime, chat, contract, previous=None):
    question = row["question"]
    preflight = preflight_question(question)
    code = preflight.code if preflight.blocked else scope_code(question)
    reference = None
    if not code and needs_reference(question):
        reference = reference_for(database, question, previous)
        if reference is None:
            code = "clarification_required"
    if code:
        return dict(code=code, chat_called=False), None
    hint = [reference["title"] + " " + reference["public_path"]] if reference else []
    query, overlong = runtime.embeddings.prepare_retrieval_query(question, hint)
    started = time.monotonic()
    with database.session_factory() as db:
        db.info["settings"] = runtime.settings
        hydrated = hydrate_evidence(
            db,
            runtime,
            query,
            limit=runtime.settings.assistant_retrieve_limit,
            skip_dense=overlong,
            max_chars=runtime.settings.assistant_evidence_max_chars,
            current_path=preferred_page(question, row.get("current_path"), reference),
        )
    info = dict(
        retrieval_seconds=time.monotonic() - started,
        degraded=hydrated.degraded,
        candidate_count=hydrated.candidate_count,
        generation_id=hydrated.generation_id,
        query_sha256=checksum(query),
        reference_title=(reference or {}).get("title"),
    )
    if not hydrated.evidence:
        return {**info, "code": "insufficient_evidence", "chat_called": False}, None
    built = build_prompt(
        question=question,
        evidence=hydrated.evidence,
        history=[],
        provider=chat,
        max_input_tokens=contract.max_input_tokens,
        max_output_tokens=contract.max_output_tokens,
        context_window_tokens=contract.context_window_tokens,
        reference_title=(reference or {}).get("title"),
        resume_available=True,
    )
    if built is None:
        return {**info, "code": "input_budget_exceeded", "chat_called": False}, None
    selected = [e.descriptor() for e in built.evidence]
    info.update(
        estimated_input=built.estimated_tokens,
        selected=selected,
        prompt_sha256=checksum(built.messages),
        chat_called=False,
    )
    return info, built


def evaluation_settings():
    # Latest user decision expands the reviewed input cap to 32000; corpus size does not
    # determine per-question input size. No production configuration override.
    return Settings(_env_file=API_ROOT / ".env")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--case", action="append", dest="cases")
    parser.add_argument("--dataset", choices=("regression", "holdout"), default="regression")
    args = parser.parse_args()
    settings = evaluation_settings()
    retrieval_settings = Settings(_env_file=API_ROOT / ".env.e5")
    if settings.assistant_online_enabled or retrieval_settings.assistant_online_enabled:
        raise ValueError("offline development configuration required")
    contract = contract_for(settings)
    dataset_path = BASE / ("Q5-holdout.json" if args.dataset == "holdout" else "Q5-cases.json")
    corpus, dataset = read_json(BASE / "Q5-corpus.json"), read_json(dataset_path)
    validate_dataset(corpus, dataset)
    rows = dataset["rows"]
    if args.cases:
        if len(args.cases) != len(set(args.cases)) or not set(args.cases) <= {
            r["id"] for r in rows
        }:
            raise ValueError("unknown/duplicate case")
        rows = [r for r in rows if r["id"] in args.cases]
    database = Database(retrieval_settings.database_url)
    runtime = build_runtime(retrieval_settings, database)
    chat = build_chat_model(settings)
    ledger = API_ROOT / "data/assistant-qualification/local-provider-ledger.json"
    output = (
        API_ROOT / "data" / ("qa-current-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + ".json")
    )
    if output.exists():
        raise ValueError("output already exists")
    report = dict(
        mode="run" if args.run else "prepare",
        production_qualified=False,
        dataset_sha256=checksum(dataset),
        dataset_name=args.dataset,
        corpus_sha256=checksum(corpus),
        review_status="requires_review",
        rows=[],
    )
    try:
        with local_ledger.run_lock(ledger):
            status = local_ledger.status(settings=settings, ledger_path=ledger)
            planned = sum(r["expected"] in {"answer", "no_supported_answer"} for r in rows)
            planned += sum(bool(r.get("followup")) for r in rows)
            # Calls are bounded upfront. Money is reserved from each actual
            # admitted prompt immediately before dispatch by the signed ledger.
            if args.run:
                check_envelope(status, planned, 0)
            # Prepare validates current sources and prompts without money reservation;
            # a signed unknown call remains visible and still blocks every paid run.
            report["budget_before"] = status
            for row in rows:
                steps = [row]
                if row.get("followup"):
                    steps.append(
                        dict(row["followup"], id=row["id"] + "-followup", split=row["split"])
                    )
                previous = None
                for step in steps:
                    with database.session_factory() as db:
                        db.info["settings"] = retrieval_settings
                        validate_dataset(corpus, dataset, iter_public_sources(db))
                    info, built = prepare_case(step, database, runtime, chat, contract, previous)
                    result = dict(id=step["id"], split=step["split"], **info)
                    if args.run and built:
                        paid, parsed = paid_call(
                            settings, contract, ledger, bind_answer_model(chat), built.messages,
                            built.estimated_tokens,
                        )
                        result.update(paid, chat_called=True)
                        if paid["transport_ok"]:
                            validated = (
                                validate_model_answer(
                                    parsed,
                                    built.evidence,
                                    question=step["question"],
                                    finish_reason=paid["finish_reason"],
                                )
                                if isinstance(parsed, ModelAnswer)
                                else "schema"
                            )
                            result["validator"] = (
                                validated if isinstance(validated, str) else "accepted"
                            )
                            if not isinstance(validated, str):
                                result.update(
                                    answer=validated.text,
                                    citations=validated.citations,
                                    sources=validated.sources,
                                )
                                previous = result
                        report["rows"].append(result)
                        report["budget_after"] = local_ledger.status(
                            settings=settings, ledger_path=ledger
                        )
                        output.write_text(
                            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8"
                        )
                        if not paid["transport_ok"]:
                            raise RuntimeError(
                                "provider result failed/unknown; recorded and stopped without retry"
                            )
                    else:
                        report["rows"].append(result)
                    print(
                        json.dumps(
                            {
                                k: result[k]
                                for k in ("id", "code", "validator", "degraded", "chat_called")
                                if k in result
                            }
                        )
                    )
            report["budget_after"] = local_ledger.status(settings=settings, ledger_path=ledger)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    finally:
        database.engine.dispose()
        runtime.store.client.close()
    print(str(output))


if __name__ == "__main__":
    main()
