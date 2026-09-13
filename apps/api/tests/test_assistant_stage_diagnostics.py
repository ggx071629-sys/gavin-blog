from __future__ import annotations

import logging
import time

from app.assistant.admin_operations import build_snapshot
from app.assistant.store import settle_attempt

from .test_assistant_deepseek import _model
from .test_assistant_online import _create_session, _online_client, _publish_and_index, _sse_body


def test_stage_diagnostics_link_retry_without_bodies(tmp_path, caplog):
    with _online_client(tmp_path, assistant_chat_max_input_tokens=10000) as client:
        _publish_and_index(client)
        online = client.app.state.assistant
        online.chat, requests = _model(content="PRIVATE_INVALID_OUTPUT")
        csrf = _create_session(client)
        logger = logging.getLogger("gavin.assistant")
        logger.addHandler(caplog.handler)
        try:
            with caplog.at_level(logging.INFO, logger="gavin.assistant"):
                _, body = _sse_body(
                    client, csrf, "What Python notes are published?", idem="stage-diagnostics-01"
                )
        finally:
            logger.removeHandler(caplog.handler)
        assert len(requests) == 2 and "output_invalid" in body
        turns = online.control.read(
            lambda c: [dict(r) for r in c.execute("SELECT * FROM assistant_turns")]
        )
        turn = turns[-1]["id"]
        rows = online.control.read(
            lambda c: [
                dict(r)
                for r in c.execute(
                    "SELECT * FROM assistant_activity_events WHERE kind LIKE 'stage_%'"
                )
            ]
        )
        assert {r["kind"] for r in rows} == {
            "stage_checking",
            "stage_retrieving",
            "stage_evidence_gate",
            "stage_composing",
            "stage_validating",
        }
        assert len([r for r in rows if r["kind"] == "stage_composing"]) == 2
        assert all(turn in r["event_id"] and r["latency_ms"] >= 0 for r in rows)
        messages = [
            r.getMessage()
            for r in caplog.records
            if r.getMessage().startswith(("assistant_stage ", "assistant_terminal "))
        ]
        assert messages and all(turn in m for m in messages)
        assert any(
            "candidates=" in m and "selected=" in m and "evidence_version_digest=" in m
            for m in messages
        )
        assert any("code=output_invalid" in m for m in messages)
        assert not any(
            secret in str(messages) + str(rows)
            for secret in ("PRIVATE_INVALID_OUTPUT", "What Python notes", "I write about FastAPI")
        )


def test_metered_latency_and_query_event_are_exact_once(tmp_path):
    with _online_client(tmp_path, assistant_chat_max_input_tokens=10000) as client:
        _publish_and_index(client)
        online = client.app.state.assistant
        original = online.embeddings.embed_query_metered

        def slow(query):
            time.sleep(0.02)
            return original(query)

        online.embeddings.embed_query_metered = slow
        online.chat, requests = _model(status=500)
        csrf = _create_session(client)
        _, body = _sse_body(
            client, csrf, "What Python notes are published?", idem="metered-latency-01"
        )
        assert "provider_result_unknown" in body and len(requests) == 1
        events = online.control.read(
            lambda c: [dict(r) for r in c.execute("SELECT * FROM assistant_metered_events")]
        )
        assert len(events) == 2 and {r["kind"] for r in events} == {"chat", "query_embedding"}
        assert all(r["latency_ms"] is not None and r["latency_ms"] >= 0 for r in events)
        assert next(r for r in events if r["kind"] == "query_embedding")["latency_ms"] >= 15
        attempts = online.control.read(
            lambda c: [
                dict(r)
                for r in c.execute(
                    "SELECT * FROM assistant_attempts WHERE status IN ('succeeded','unknown')"
                )
            ]
        )
        for attempt in attempts:
            event = next(e for e in events if e["event_id"] == attempt["id"])
            assert event["cost_micro"] == attempt["settled_micro"]
            assert (
                online.control.immediate(
                    lambda c, attempt=attempt: settle_attempt(
                        c,
                        attempt=attempt,
                        status=attempt["status"],
                        settled_micro=attempt["settled_micro"],
                        now=online.now(),
                    )
                )
                is False
            )
        assert (
            online.control.read(
                lambda c: c.execute("SELECT COUNT(*) FROM assistant_metered_events").fetchone()[0]
            )
            == 2
        )
        with online.content_session() as db:
            snapshot = build_snapshot(
                settings=online.settings, online=online, db=db, launcher_source="test"
            )
        total = online.control.read(
            lambda c: c.execute(
                "SELECT latency_ms FROM assistant_activity_events WHERE kind='error'"
            ).fetchone()[0]
        )
        assert snapshot.daily_activity.latency_ms_min == total
        assert snapshot.daily_activity.latency_ms_max == total
