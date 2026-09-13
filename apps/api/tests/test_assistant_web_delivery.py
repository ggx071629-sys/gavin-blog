from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from app.assistant.constants import (
    ATTEMPT_FAILED,
    ATTEMPT_SUCCEEDED,
    BODY_RETENTION_SECONDS,
    CODE_ORIGIN_REJECTED,
)
from app.assistant.crypto import compare, session_csrf_token
from app.assistant.hydrate import Evidence
from app.assistant.output import validate_model_answer
from app.assistant.providers import DeterministicChatModel, ModelAnswer
from app.assistant.sse import project_public_event
from app.assistant.store import (
    enforce_session_byte_cap,
    purge_billing_tombstones,
    session_snapshot,
    session_utf8_bytes,
)

from .test_assistant_online import (
    CSRF_SECRET,
    ORIGIN,
    _create_session,
    _headers,
    _online_client,
    _publish_and_index,
    _sse_body,
)


def test_session_view_policy_and_no_store(tmp_path: Path) -> None:
    with _online_client(tmp_path) as client:
        csrf = _create_session(client)
        created = client.post("/api/v1/assistant/sessions", headers={"Origin": ORIGIN})
        body = created.json()
        assert created.headers.get("cache-control") == "no-store"
        assert body["policy"] == {
            "question_max_chars": 500,
            "session_idle_seconds": 1800,
            "session_absolute_seconds": 86400,
            "body_retention_seconds": BODY_RETENTION_SECONDS,
        }
        listed = client.get("/api/v1/assistant/session")
        assert listed.status_code == 200
        assert listed.headers.get("cache-control") == "no-store"
        payload = listed.json()
        assert payload["policy"] == body["policy"]
        assert payload["turns"] == []
        assert payload["active_turn"] is None
        assert csrf
        token = session_csrf_token(CSRF_SECRET, payload["session_id"])
        assert created.json()["csrf_token"] == token


def test_get_session_trusts_forwarded_public_host_not_api_listen_host(
    tmp_path: Path,
) -> None:
    with _online_client(tmp_path) as client:
        csrf = _create_session(client)
        listen = client.get(
            "/api/v1/assistant/session",
            headers={"Host": "127.0.0.1:8101"},
        )
        assert listen.status_code == 403
        assert listen.json()["error"]["code"] == CODE_ORIGIN_REJECTED
        proxied = client.get(
            "/api/v1/assistant/session",
            headers={"Host": "127.0.0.1:8101", "X-Forwarded-Host": "testserver"},
        )
        assert proxied.status_code == 200, proxied.text
        assert proxied.json()["turns"] == []
        spoofed = client.get(
            "/api/v1/assistant/session",
            headers={"Host": "127.0.0.1:8101", "X-Forwarded-Host": "evil.example"},
        )
        assert spoofed.status_code == 403
        assert spoofed.json()["error"]["code"] == CODE_ORIGIN_REJECTED
        assert csrf


def test_read_metadata_production_accepts_matching_forwarded_host() -> None:
    import pytest
    from starlette.requests import Request

    from app.assistant.origin import require_read_metadata
    from app.config import Settings
    from app.http_errors import ApiException

    settings = Settings(
        environment="production",
        admin_password="long-enough-password",
        cookie_secure=True,
        assistant_public_origin="https://gavin.example",
        _env_file=None,
    )

    def _request(headers: list[tuple[bytes, bytes]]) -> Request:
        return Request(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": "/api/v1/assistant/session",
                "raw_path": b"/api/v1/assistant/session",
                "query_string": b"",
                "headers": headers,
                "client": ("127.0.0.1", 9),
                "server": ("127.0.0.1", 8000),
            }
        )

    require_read_metadata(
        _request(
            [
                (b"host", b"127.0.0.1:8000"),
                (b"x-forwarded-host", b"gavin.example"),
                (b"sec-fetch-site", b"same-origin"),
                (b"sec-fetch-mode", b"cors"),
            ]
        ),
        settings,
    )
    with pytest.raises(ApiException) as rejected:
        require_read_metadata(
            _request(
                [
                    (b"host", b"127.0.0.1:8000"),
                    (b"sec-fetch-site", b"same-origin"),
                ]
            ),
            settings,
        )
    assert rejected.value.code == CODE_ORIGIN_REJECTED


def test_bootstrap_reissues_same_csrf_without_create_limit(tmp_path: Path) -> None:
    with _online_client(tmp_path) as client:
        first = client.post("/api/v1/assistant/sessions", headers={"Origin": ORIGIN})
        token = first.json()["csrf_token"]
        session_id = first.json()["session_id"]
        idle = first.json()["idle_expires_at"]
        for _ in range(6):
            again = client.post("/api/v1/assistant/sessions", headers={"Origin": ORIGIN})
            assert again.status_code == 200, again.text
            assert again.json()["csrf_token"] == token
            assert again.json()["session_id"] == session_id
            assert again.json()["idle_expires_at"] == idle


def test_constant_time_csrf_compare() -> None:
    assert compare("abc", "abc") is True
    assert compare("abc", "abd") is False
    assert compare("", "abc") is False


def test_public_sse_strips_idempotent_and_unknown_fields() -> None:
    projected = project_public_event(
        "checking",
        {"event_id": 1, "turn_id": "t", "stage": "checking", "idempotent": 1, "secret": "nope"},
    )
    assert projected == {"event_id": 1, "turn_id": "t", "stage": "checking"}
    answer = project_public_event(
        "answer",
        {
            "event_id": 2,
            "turn_id": "t",
            "type": "answer",
            "code": "answered",
            "message": "ok",
            "answer": "text",
            "citations": [],
            "sources": [],
            "idempotent": 1,
        },
    )
    assert "idempotent" not in answer
    assert "answer" in answer and "citations" in answer and "sources" in answer


def test_model_block_reserved_marker_rejected() -> None:
    evidence = [
        Evidence(
            alias="c1",
            chunk_id="chunk-1",
            title="Python notes",
            heading_path="Python",
            public_path="/notes/2026/08/python-notes",
            body="FastAPI notes",
            source_type="article",
            source_id=1,
            source_version="1",
            generation_id=1,
            sources=("article:1",),
        )
    ]
    parsed = ModelAnswer.model_validate(
        {"blocks": [{"text": "See [1] in the corpus", "citation_ids": ["c1"]}]}
    )
    assert validate_model_answer(parsed, evidence, finish_reason="stop") == "structure"


def test_completed_turn_view_includes_question_and_tombstone(tmp_path: Path) -> None:
    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        csrf = _create_session(client)
        status, body = _sse_body(
            client, csrf, "Which published notes cover FastAPI?", idem="idem-view-body-000001"
        )
        assert status == 200
        assert "idempotent" not in body
        listed = client.get("/api/v1/assistant/session")
        assert listed.status_code == 200
        turns = listed.json()["turns"]
        assert len(turns) == 1
        turn = turns[0]
        assert turn["question"] == "Which published notes cover FastAPI?"
        assert turn["body_available"] is True
        assert turn["answer"]
        assert isinstance(turn["citations"], list)
        online = client.app.state.assistant

        def _purge(conn):
            conn.execute(
                "UPDATE assistant_turns SET question = NULL, answer = NULL, "
                "citations_json = NULL, sources_json = NULL, body_purged_at = ?",
                (online.now(),),
            )

        online.control.immediate(_purge)
        tombstoned = client.get("/api/v1/assistant/session").json()["turns"][0]
        assert tombstoned["body_available"] is False
        assert tombstoned["question"] is None
        assert tombstoned["answer"] is None


def test_multi_active_session_view_fails_closed(tmp_path: Path) -> None:
    with _online_client(tmp_path) as client:
        csrf = _create_session(client)
        listed = client.get("/api/v1/assistant/session")
        session_id = listed.json()["session_id"]
        online = client.app.state.assistant
        now = online.now()

        def _seed(conn):
            for index in range(2):
                conn.execute(
                    """
                    INSERT INTO assistant_turns (
                        id, session_id, idempotency_hmac, payload_hmac, status, created_at
                    ) VALUES (?, ?, ?, 'pay', 'running', ?)
                    """,
                    (f"turn-{index}", session_id, f"idem-{index}", now),
                )

        online.control.immediate(_seed)
        response = client.get("/api/v1/assistant/session")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "assistant_not_ready"
        assert csrf


def test_delete_missing_origin_fails_before_tombstone(tmp_path: Path) -> None:
    with _online_client(tmp_path) as client:
        csrf = _create_session(client)
        listed = client.get("/api/v1/assistant/session")
        session_id = listed.json()["session_id"]
        response = client.delete(
            "/api/v1/assistant/session",
            headers={"X-Assistant-CSRF": csrf},
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "origin_rejected"
        online = client.app.state.assistant
        row = online.control.read(
            lambda conn: conn.execute(
                "SELECT tombstoned_at FROM assistant_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        )
        assert row["tombstoned_at"] is None


def test_delete_204_and_202_clear_both_cookies(tmp_path: Path) -> None:
    with _online_client(tmp_path) as client:
        csrf = _create_session(client)
        deleted = client.delete(
            "/api/v1/assistant/session",
            headers={"Origin": ORIGIN, "X-Assistant-CSRF": csrf},
        )
        assert deleted.status_code == 204
        joined = "\n".join(deleted.headers.get_list("set-cookie")).lower()
        assert "gavin_assistant_session=" in joined
        assert "gavin_assistant_csrf=" in joined
        assert "cache-control" in {key.lower() for key in deleted.headers.keys()}


def test_delete_before_sending_makes_zero_provider_calls(tmp_path: Path) -> None:
    import threading
    import time

    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        csrf = _create_session(client)
        online = client.app.state.assistant
        model = online.chat
        assert isinstance(model, DeterministicChatModel)
        online.pause_before_send = threading.Event()

        def _ask() -> None:
            client.post(
                "/api/v1/assistant/questions",
                json={"question": "Which published notes cover FastAPI?"},
                headers=_headers(csrf, idem="idem-delete-before-send01"),
            )

        worker = threading.Thread(target=_ask)
        worker.start()
        for _ in range(80):
            prepared = online.control.read(
                lambda conn: conn.execute(
                    "SELECT COUNT(*) AS n FROM assistant_attempts "
                    "WHERE kind = 'chat' AND status = 'prepared'"
                ).fetchone()["n"]
            )
            if int(prepared) >= 2:
                break
            time.sleep(0.05)
        deleted = client.delete(
            "/api/v1/assistant/session",
            headers={"Origin": ORIGIN, "X-Assistant-CSRF": csrf},
        )
        assert deleted.status_code in {202, 204}
        online.pause_before_send.set()
        worker.join(timeout=15)
        assert len(model.calls) == 0


def test_chat_attempts_are_prepared_at_admission(tmp_path: Path) -> None:
    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        csrf = _create_session(client)
        status, _body = _sse_body(
            client, csrf, "Which published notes cover FastAPI?", idem="idem-two-slots-0000001"
        )
        assert status == 200
        online = client.app.state.assistant
        rows = online.control.read(
            lambda conn: conn.execute(
                "SELECT status FROM assistant_attempts WHERE kind = 'chat' ORDER BY created_at"
            ).fetchall()
        )
        statuses = [row["status"] for row in rows]
        assert len(statuses) == 2
        assert ATTEMPT_SUCCEEDED in statuses
        assert ATTEMPT_FAILED in statuses
        budget = online.control.read(
            lambda conn: conn.execute(
                "SELECT reserved_micro, settled_micro FROM assistant_chat_budgets"
            ).fetchone()
        )
        assert int(budget["reserved_micro"]) == 0
        assert int(budget["settled_micro"]) >= 0


def test_openapi_declares_additive_headers_and_policy(tmp_path: Path) -> None:
    with _online_client(tmp_path) as client:
        spec = client.app.openapi()
        questions = spec["paths"]["/api/v1/assistant/questions"]["post"]
        names = {item["name"] for item in questions.get("parameters", [])}
        assert "Idempotency-Key" in names
        assert "X-Assistant-CSRF" in names
        assert "Last-Event-ID" in names
        create_schema = spec["components"]["schemas"]["SessionCreateResponse"]
        assert "policy" in create_schema["properties"]
        turn_schema = spec["components"]["schemas"]["SessionTurn"]
        for field in ("question", "citations", "sources", "body_available"):
            assert field in turn_schema["properties"]
        delete = spec["paths"]["/api/v1/assistant/session"]["delete"]
        delete_names = {item["name"] for item in delete.get("parameters", [])}
        assert "X-Assistant-CSRF" in delete_names


def test_utf8_byte_cap_recalculates_after_purge(tmp_path: Path) -> None:
    with _online_client(tmp_path) as client:
        csrf = _create_session(client)
        listed = client.get("/api/v1/assistant/session")
        session_id = listed.json()["session_id"]
        online = client.app.state.assistant
        now = online.now()
        blob = "测" * 40000

        def _seed(conn):
            conn.execute(
                """
                INSERT INTO assistant_turns (
                    id, session_id, idempotency_hmac, payload_hmac, status, created_at,
                    terminal_event, terminal_code, terminal_message, question, answer
                ) VALUES ('old', ?, 'idem-old', 'pay', 'terminal', ?, 'answer', 'answered', ?, ?, ?)
                """,
                (session_id, now, blob, blob, blob),
            )

        online.control.immediate(_seed)
        over = online.control.immediate(
            lambda conn: enforce_session_byte_cap(conn, session_id, now)
        )
        total = online.control.read(lambda conn: session_utf8_bytes(conn, session_id))
        assert total <= 256 * 1024
        row = online.control.read(
            lambda conn: conn.execute(
                "SELECT body_purged_at, question FROM assistant_turns WHERE id = 'old'"
            ).fetchone()
        )
        assert row["body_purged_at"] is not None
        assert row["question"] is None
        assert csrf
        assert over is False


def test_48h_purge_removes_minimal_rows(tmp_path: Path) -> None:
    with _online_client(tmp_path) as client:
        csrf = _create_session(client)
        listed = client.get("/api/v1/assistant/session")
        session_id = listed.json()["session_id"]
        online = client.app.state.assistant
        now = online.now()
        purged_at = now - timedelta(hours=49)

        def _seed(conn):
            conn.execute(
                """
                INSERT INTO assistant_turns (
                    id, session_id, idempotency_hmac, payload_hmac, status, created_at,
                    body_purged_at
                ) VALUES ('gone', ?, 'idem-gone', 'pay', 'terminal', ?, ?)
                """,
                (session_id, now, purged_at),
            )
            conn.execute(
                "UPDATE assistant_sessions SET tombstoned_at = ? WHERE id = ?",
                (now, session_id),
            )
            purge_billing_tombstones(conn, now)

        online.control.immediate(_seed)
        leftover = online.control.read(
            lambda conn: conn.execute("SELECT COUNT(*) AS n FROM assistant_turns").fetchone()["n"]
        )
        sessions = online.control.read(
            lambda conn: conn.execute(
                "SELECT COUNT(*) AS n FROM assistant_sessions"
            ).fetchone()["n"]
        )
        assert leftover == 0
        assert sessions == 0
        assert csrf


def test_test_bootstrap_rejected_outside_test_environment() -> None:
    from app.config import Settings

    settings = Settings(
        environment="production",
        admin_password="long-enough-password",
        cookie_secure=True,
        assistant_test_startup_bootstrap=True,
        _env_file=None,
    )
    try:
        settings.validate_runtime()
        raise AssertionError("expected bootstrap to fail closed")
    except RuntimeError as exc:
        assert "test" in str(exc)


def test_snapshot_orders_newest_twenty_ascending(tmp_path: Path) -> None:
    with _online_client(tmp_path) as client:
        csrf = _create_session(client)
        session_id = client.get("/api/v1/assistant/session").json()["session_id"]
        online = client.app.state.assistant
        now = online.now()

        def _seed(conn):
            for index in range(25):
                created = now - timedelta(minutes=25 - index)
                conn.execute(
                    """
                    INSERT INTO assistant_turns (
                        id, session_id, idempotency_hmac, payload_hmac, status, created_at,
                        terminal_event, preflight_blocked
                    ) VALUES (?, ?, ?, 'pay', 'terminal', ?, 'answer', 0)
                    """,
                    (f"t{index:02d}", session_id, f"idem{index:02d}", created),
                )

        online.control.immediate(_seed)
        snapshot = online.control.read(lambda conn: session_snapshot(conn, session_id))
        ids = [item["turn_id"] for item in snapshot["turns"]]
        assert ids == [f"t{index:02d}" for index in range(5, 25)]
        assert csrf
