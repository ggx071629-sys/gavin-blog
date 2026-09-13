from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

import pytest

from app.assistant.constants import ESTIMATOR_VERSION
from app.assistant.crypto import digest
from app.assistant.errors import AssistantNotReadyError
from app.assistant.graph import _retrieval_query, _reusable_query_vector
from app.assistant.hydrate import Evidence
from app.assistant.prompt import build_prompt, estimate_tokens
from app.assistant.providers import ModelAnswer
from app.assistant.readiness import verify_receipt, write_receipt
from app.assistant.store import insert_attempt
from app.assistant.validation import validate_online_settings

from .test_assistant_online import (
    _create_session,
    _online_client,
    _publish_and_index,
    _settings,
    _sse_body,
)


class _Tokenizer:
    def __init__(self, value: object = 0, *, fail: bool = False) -> None:
        self.value = value
        self.fail = fail

    def assistant_token_count(self, _text: str) -> object:
        if self.fail:
            raise RuntimeError("tokenizer unavailable")
        return self.value


def _byte_bound(messages: list[tuple[str, str]]) -> int:
    schema = json.dumps(ModelAnswer.model_json_schema(), sort_keys=True, separators=(",", ":"))
    serialized = schema + "\n" + "\n".join(f"{role}:{body}" for role, body in messages)
    return len(serialized.encode("utf-8")) + 16 + 4 * len(messages)


def _evidence() -> list[Evidence]:
    return [
        Evidence(
            alias="c1",
            chunk_id="chunk-1",
            title="Python notes",
            heading_path="Python",
            public_path="/articles/python-notes",
            body="Published notes cover FastAPI and SQLite.",
            source_type="article",
            source_id=1,
            source_version="v1",
            generation_id=1,
            sources=("fts",),
        )
    ]


@pytest.mark.parametrize(
    "provider",
    [_Tokenizer(0), _Tokenizer(-7), _Tokenizer("invalid"), _Tokenizer(fail=True)],
)
def test_estimator_invalid_or_unavailable_tokenizer_cannot_lower_byte_bound(
    provider: _Tokenizer,
) -> None:
    messages = [("system", "系统"), ("human", "What is published?")]
    assert estimate_tokens(messages, provider) == _byte_bound(messages)


def test_estimator_uses_provider_count_only_when_it_is_more_conservative() -> None:
    messages = [("system", "scope"), ("human", "question")]
    byte_bound = _byte_bound(messages)
    assert estimate_tokens(messages, _Tokenizer(byte_bound + 73)) == byte_bound + 73


def test_prompt_drops_oldest_complete_pairs_before_dispatch() -> None:
    history = [{"question": f"question-{index}", "answer": f"answer-{index}"} for index in range(4)]
    provider = _Tokenizer(0)
    output_reserve = 128
    two_pairs = build_prompt(
        question="What did those notes mean?",
        evidence=_evidence(),
        history=history[-2:],
        provider=provider,
        max_input_tokens=100_000,
        max_output_tokens=output_reserve,
        context_window_tokens=100_128,
    )
    three_pairs = build_prompt(
        question="What did those notes mean?",
        evidence=_evidence(),
        history=history[-3:],
        provider=provider,
        max_input_tokens=100_000,
        max_output_tokens=output_reserve,
        context_window_tokens=100_128,
    )
    assert two_pairs is not None
    assert three_pairs is not None
    assert two_pairs.estimated_tokens < three_pairs.estimated_tokens
    input_cap = three_pairs.estimated_tokens - 1

    trimmed = build_prompt(
        question="What did those notes mean?",
        evidence=_evidence(),
        history=history,
        provider=provider,
        max_input_tokens=input_cap,
        max_output_tokens=output_reserve,
        context_window_tokens=input_cap + output_reserve,
    )

    assert trimmed is not None
    assert trimmed.history == history[-2:]
    assert trimmed.estimated_tokens == two_pairs.estimated_tokens


def test_retrieval_query_preserves_current_question_under_long_history() -> None:
    history = [f"HISTORY_{index}_" + "x" * 490 for index in range(4)]
    current = "CURRENT_QUESTION_SENTINEL_62D1_" + "y" * 450

    query = _retrieval_query(current, history)

    assert len(query) <= 1000
    assert query.startswith(current)
    assert "CURRENT_QUESTION_SENTINEL_62D1" in query
    assert "HISTORY_3_" in query

    from app.assistant_index.retriever import _match_expressions
    from app.assistant_index.fts import ASSISTANT_FTS_SQL
    import sqlite3

    long_history = "Tell me how the first project implements logging monitoring deployment backups security and caching"
    for current, history, required in [
        ("Redis", [long_history], "Redis"),
        ("向量检索", [long_history], "向"),
        ("How does it retry?", [long_history, "Redis retry policy"], "retry"),
    ]:
        expressions = _match_expressions(_retrieval_query(current, history))
        assert expressions and all(required in expression for expression in expressions)
        if "it" in current:
            assert all("Redis" in expression for expression in expressions)

    # Real FTS regression: history-first conversion lost the new topic entirely.
    with sqlite3.connect(":memory:") as db:
        db.execute(ASSISTANT_FTS_SQL)
        db.execute(
            "INSERT INTO assistant_chunk_fts VALUES ('redis', 1, 'Redis', '', 'Redis cache')"
        )
        hits = []
        for match in _match_expressions(_retrieval_query("Redis", [long_history])):
            hits = db.execute(
                "SELECT chunk_id FROM assistant_chunk_fts WHERE assistant_chunk_fts MATCH ?",
                (match,),
            ).fetchall()
            if hits:
                break
        assert hits == [("redis",)]


def test_context_window_validation_and_readiness_bind_all_token_limits(tmp_path: Path) -> None:
    missing = _settings(tmp_path, assistant_chat_context_window_tokens=None)
    with pytest.raises(RuntimeError, match="assistant_chat_context_window_tokens is required"):
        validate_online_settings(missing)

    invalid = _settings(
        tmp_path,
        assistant_chat_max_input_tokens=8000,
        assistant_chat_max_output_tokens=400,
        assistant_chat_context_window_tokens=8399,
    )
    with pytest.raises(RuntimeError, match="exceed the declared context window"):
        validate_online_settings(invalid)

    reused_secret = _settings(
        tmp_path,
        assistant_csrf_hmac_secret=_settings(tmp_path).assistant_session_hmac_secret,
    )
    with pytest.raises(RuntimeError, match="must be independent"):
        validate_online_settings(reused_secret)

    equality = _settings(
        tmp_path,
        assistant_chat_max_input_tokens=8000,
        assistant_chat_max_output_tokens=400,
        assistant_chat_context_window_tokens=8400,
    )
    validate_online_settings(equality)

    with _online_client(tmp_path) as client:
        online = client.app.state.assistant
        receipt_json = online.control.read(
            lambda conn: conn.execute(
                "SELECT receipt_json FROM assistant_readiness_receipts WHERE revoked_at IS NULL"
            ).fetchone()[0]
        )
        payload = json.loads(receipt_json)
        assert payload["estimator_version"] == ESTIMATOR_VERSION
        assert payload["chat_token_limits"] == {
            "max_input": 8000,
            "max_output": 400,
            "context_window": 16384,
        }
        for field, drifted_value in (
            ("assistant_chat_max_input_tokens", 7999),
            ("assistant_chat_max_output_tokens", 399),
            ("assistant_chat_context_window_tokens", 16385),
        ):
            drifted = client.app.state.settings.model_copy(update={field: drifted_value})
            with pytest.raises(AssistantNotReadyError, match="binding mismatch"):
                online.control.read(lambda conn, settings=drifted: verify_receipt(settings, conn))


def test_resume_discards_cached_vector_when_history_query_changes(tmp_path: Path) -> None:
    with _online_client(tmp_path) as client:
        _create_session(client)
        online = client.app.state.assistant
        session_id = client.get("/api/v1/assistant/session").json()["session_id"]
        now = online.now()
        old_query = "old history question current question"
        new_query = "current question after history purge"

        def _seed(conn) -> dict[str, object]:
            conn.execute(
                "INSERT INTO assistant_turns "
                "(id, session_id, idempotency_hmac, payload_hmac, status, created_at) "
                "VALUES ('resume-vector-turn', ?, 'resume-vector-idem', 'payload', "
                "'running', ?)",
                (session_id, now),
            )
            insert_attempt(
                conn,
                attempt_id="resume-vector-attempt",
                turn_id="resume-vector-turn",
                kind="query_embedding",
                fencing_token="resume-vector-token",
                request_fingerprint=digest(old_query),
                price_snapshot_json="{}",
                day="2026-08-29",
                max_cost_micro=1,
                now=now,
            )
            conn.execute(
                "UPDATE assistant_attempts SET status = 'succeeded', vector_json = '[0.1,0.2]' "
                "WHERE id = 'resume-vector-attempt'"
            )
            return dict(
                conn.execute(
                    "SELECT * FROM assistant_attempts WHERE id = 'resume-vector-attempt'"
                ).fetchone()
            )

        attempt = online.control.immediate(_seed)
        embedding_calls = len(online.embeddings.calls)

        assert _reusable_query_vector(online, attempt, new_query) is None
        assert len(online.embeddings.calls) == embedding_calls
        assert (
            online.control.read(
                lambda conn: conn.execute(
                    "SELECT vector_json FROM assistant_attempts WHERE id = 'resume-vector-attempt'"
                ).fetchone()[0]
            )
            is None
        )


def test_unprovable_prompt_fit_never_dispatches_chat_provider(tmp_path: Path) -> None:
    with _online_client(
        tmp_path,
        assistant_chat_max_input_tokens=1,
        assistant_chat_max_output_tokens=400,
        assistant_chat_context_window_tokens=401,
    ) as client:
        _publish_and_index(client)
        csrf = _create_session(client)
        status, body = _sse_body(
            client,
            csrf,
            "Which published notes cover FastAPI?",
            idem="prompt-no-fit-000001",
        )
        online = client.app.state.assistant

        assert status == 200
        assert "event: error" in body
        assert online.chat.calls == []
        attempts, budget, history, turn = online.control.read(
            lambda conn: (
                conn.execute(
                    "SELECT status, settled_micro, parsed_json FROM assistant_attempts "
                    "WHERE kind = 'chat' ORDER BY created_at"
                ).fetchall(),
                conn.execute(
                    "SELECT reserved_micro, settled_micro FROM assistant_chat_budgets"
                ).fetchone(),
                conn.execute("SELECT COUNT(*) FROM assistant_history").fetchone()[0],
                conn.execute(
                    "SELECT status, answer FROM assistant_turns ORDER BY created_at DESC LIMIT 1"
                ).fetchone(),
            )
        )
        assert attempts
        assert all(row["status"] == "failed" for row in attempts)
        assert all(row["settled_micro"] == 0 for row in attempts)
        assert all(row["parsed_json"] is None for row in attempts)
        assert budget["reserved_micro"] == 0
        assert budget["settled_micro"] == 0
        assert history == 0
        assert turn["status"] == "terminal"
        assert turn["answer"] is None


def test_history_query_is_transient_and_never_enters_langgraph_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    history_question = "HISTORY_Q_SENTINEL_FASTAPI_7F3A"
    history_answer = "HISTORY_A_SENTINEL_PRIVATE_91C2"
    current_question = "Which published FastAPI note follows CURRENT_Q_SENTINEL_4D8B?"
    with _online_client(
        tmp_path,
        assistant_chat_max_input_tokens=16000,
        assistant_chat_context_window_tokens=20000,
    ) as client:
        _publish_and_index(client)
        csrf = _create_session(client)
        online = client.app.state.assistant
        session_id = client.get("/api/v1/assistant/session").json()["session_id"]
        now = online.now()

        def _seed(conn) -> None:
            conn.execute(
                "INSERT INTO assistant_turns "
                "(id, session_id, idempotency_hmac, payload_hmac, status, created_at, "
                "terminal_at, terminal_event, terminal_code) "
                "VALUES ('history-sentinel-turn', ?, 'history-sentinel-idem', 'payload', "
                "'terminal', ?, ?, 'answer', 'answered')",
                (session_id, now, now),
            )
            conn.execute(
                "INSERT INTO assistant_history "
                "(session_id, turn_id, question, answer, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    "history-sentinel-turn",
                    history_question,
                    history_answer,
                    now,
                ),
            )

        online.control.immediate(_seed)
        captured_checkpoints: list[object] = []
        captured_writes: list[object] = []
        original_aput = online.saver.delegate.aput
        original_aput_writes = online.saver.delegate.aput_writes

        async def _capture_aput(config, checkpoint, metadata, new_versions):
            captured_checkpoints.append((checkpoint, metadata))
            return await original_aput(config, checkpoint, metadata, new_versions)

        async def _capture_aput_writes(config, writes, task_id, task_path=""):
            captured_writes.append(list(writes))
            return await original_aput_writes(config, writes, task_id, task_path)

        monkeypatch.setattr(online.saver.delegate, "aput", _capture_aput)
        monkeypatch.setattr(online.saver.delegate, "aput_writes", _capture_aput_writes)
        # A verbatim supported response isolates this runtime/query contract
        # from the separate heading-plus-first-person paraphrase limitation.
        from app.assistant.providers import ScriptedChatTurn

        quote = "I write about FastAPI, SQLite and published technical notes."
        online.chat.script.append(
            ScriptedChatTurn(
                parsed={
                    "blocks": [
                        {
                            "text": quote,
                            "citation_ids": ["c1"],
                            "supports": [{"citation_id": "c1", "quote": quote}],
                        }
                    ]
                }
            )
        )
        online.chat.hold()
        result: dict[str, tuple[int, str]] = {}

        def _ask() -> None:
            result["response"] = _sse_body(
                client,
                csrf,
                current_question,
                idem="history-checkpoint-0001",
            )

        worker = threading.Thread(target=_ask, daemon=True)
        worker.start()
        try:
            assert online.chat.wait_until_started()
            expected_query = current_question
            assert online.embeddings.calls[-1] == expected_query
            query_attempt = online.control.read(
                lambda conn: conn.execute(
                    "SELECT request_fingerprint FROM assistant_attempts "
                    "WHERE kind = 'query_embedding' ORDER BY created_at DESC LIMIT 1"
                ).fetchone()
            )
            assert query_attempt["request_fingerprint"] == digest(expected_query)

            runtime = sqlite3.connect(str(online.settings.assistant_runtime_path))
            try:
                checkpoint_rows = runtime.execute("SELECT * FROM checkpoints").fetchall()
                write_rows = runtime.execute("SELECT * FROM writes").fetchall()
            finally:
                runtime.close()
            assert checkpoint_rows
            assert write_rows
            assert captured_checkpoints
            assert captured_writes
            values = [value for row in checkpoint_rows for value in row]
            values.extend(value for row in write_rows for value in row)
            persisted = b"".join(
                value if isinstance(value, bytes) else str(value).encode("utf-8", errors="ignore")
                for value in values
                if value is not None
            )
            assert history_question.encode() not in persisted
            assert history_answer.encode() not in persisted
            assert b"retrieval_query" not in persisted
            assert current_question.encode() in persisted
            captured_checkpoint_bytes = repr(captured_checkpoints).encode()
            captured_write_bytes = repr(captured_writes).encode()
            for captured in (captured_checkpoint_bytes, captured_write_bytes):
                assert history_question.encode() not in captured
                assert history_answer.encode() not in captured
                assert b"retrieval_query" not in captured
            assert current_question.encode() in captured_checkpoint_bytes
            assert b"chunk_id" in captured_checkpoint_bytes
            with pytest.raises(
                AssistantNotReadyError,
                match="checkpoint residue must be cleaned",
            ):
                write_receipt(
                    client.app.state.settings,
                    probe_live=False,
                    lock=online.lock,
                )
        finally:
            online.chat.release()
            worker.join(timeout=10)
        assert not worker.is_alive()
        status, body = result["response"]
        assert status == 200
        assert "event: answer" in body
