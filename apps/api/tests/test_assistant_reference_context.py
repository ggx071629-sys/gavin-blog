from __future__ import annotations

import json
from datetime import timedelta

import pytest

from .test_assistant_online import _create_session, _online_client, _publish_and_index, _sse_body


def test_unique_reference_retrieves_current_source_without_old_answer(tmp_path, monkeypatch):
    from app.assistant import graph

    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        csrf = _create_session(client)
        online = client.app.state.assistant
        assert (
            "event: answer"
            in _sse_body(
                client, csrf, "Which published notes cover FastAPI?", idem="context-first-0001"
            )[1]
        )
        # Old answer text is deliberately poisoned; it must never become a new fact.
        online.control.immediate(
            lambda c: c.execute("UPDATE assistant_history SET answer = 'OLD_ANSWER_POISON'")
        )
        seen = []
        original = graph.build_prompt

        def capture(**kwargs):
            seen.append(kwargs)
            return original(**kwargs)

        monkeypatch.setattr(graph, "build_prompt", capture)
        result = _sse_body(client, csrf, "What does it cover?", idem="context-next-0001")[1]
        assert "event: answer" in result
        assert seen and all(p["history"] == [] for p in seen)
        assert all(p.get("reference_title") == "Python notes" for p in seen)
        assert all(p["question"] == "What does it cover?" for p in seen)
        assert "OLD_ANSWER_POISON" not in str(seen)


@pytest.mark.parametrize("condition", ["missing", "multiple", "ordinal", "expired", "withdrawn"])
def test_ambiguous_reference_clarifies_without_provider_calls(tmp_path, monkeypatch, condition):
    from app.models import Article

    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        csrf = _create_session(client)
        online = client.app.state.assistant
        if condition != "missing":
            assert (
                "event: answer"
                in _sse_body(
                    client, csrf, "Which published notes cover FastAPI?", idem="clarify-first-0001"
                )[1]
            )
        if condition == "multiple":
            online.control.immediate(
                lambda c: c.execute(
                    "UPDATE assistant_turns SET sources_json = ?",
                    (
                        json.dumps(
                            [
                                dict(n="1", path="/about", title="About"),
                                dict(n="2", path="/", title="Profile"),
                            ]
                        ),
                    ),
                )
            )
        elif condition == "expired":
            online.control.immediate(
                lambda c: c.execute(
                    "UPDATE assistant_turns SET terminal_at = ?",
                    (online.now() - timedelta(hours=1),),
                )
            )
        elif condition == "withdrawn":
            with online.content_session() as db:
                row = db.query(Article).first()
                row.status = "draft"
                db.commit()

        before = online.control.read(
            lambda c: c.execute(
                "SELECT COUNT(*) FROM assistant_attempts WHERE status = 'succeeded'"
            ).fetchone()[0]
        )

        def forbidden(*args, **kwargs):
            raise AssertionError("clarification must precede any provider dispatch")

        monkeypatch.setattr(online.embeddings, "embed_query_metered", forbidden)
        question = "第二个项目用了什么？" if condition == "ordinal" else "它用了什么？"
        status, body = _sse_body(client, csrf, question, idem="clarify-next-0001")
        assert status == 200 and "clarification_required" in body
        assert "event: answer" not in body and "insufficient_evidence" not in body
        after = online.control.read(
            lambda c: c.execute(
                "SELECT COUNT(*) FROM assistant_attempts WHERE status = 'succeeded'"
            ).fetchone()[0]
        )
        assert after == before
        assert (
            client.get("/api/v1/assistant/session").json()["turns"][-1]["code"]
            == "clarification_required"
        )


def test_topic_switch_has_no_historical_query_or_prompt(tmp_path, monkeypatch):
    from app.assistant import graph

    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        csrf = _create_session(client)
        assert (
            "event: answer"
            in _sse_body(
                client, csrf, "Which published notes cover FastAPI?", idem="switch-first-0001"
            )[1]
        )
        queries = []
        original = graph.hydrate_evidence

        def capture(db, runtime, query, **kwargs):
            queries.append(query)
            return original(db, runtime, query, **kwargs)

        monkeypatch.setattr(graph, "hydrate_evidence", capture)
        question = "换个话题，SQLite是什么？"
        _sse_body(client, csrf, question, idem="switch-next-0001")
        assert queries == [question]
