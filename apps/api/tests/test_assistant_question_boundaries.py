from __future__ import annotations

from .test_assistant_online import (
    _create_session,
    _headers,
    _online_client,
    _publish_and_index,
    _sse_body,
)


def test_page_priority_requires_explicit_reference(tmp_path, monkeypatch):
    from app.assistant import graph

    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        csrf = _create_session(client)
        paths = []
        original = graph.hydrate_evidence

        def capture(db, runtime, query, **kwargs):
            paths.append(kwargs.get("current_path"))
            return original(db, runtime, query, **kwargs)

        monkeypatch.setattr(graph, "hydrate_evidence", capture)
        for n, question in enumerate(["What does SQLite do?", "这篇文章介绍FastAPI吗？"]):
            response = client.post(
                "/api/v1/assistant/questions",
                json=dict(question=question, current_path="/notes/2026/08/python-notes"),
                headers=_headers(csrf, idem=f"page-priority-{n}-0001"),
            )
            assert response.status_code == 200
        assert paths == [None, "/notes/2026/08/python-notes"]


def test_scope_rules_distinguish_inventory_freshness_and_local_facts():
    from app.assistant.question_scope import scope_code
    from app.assistant.reference_context import needs_reference

    for question in [
        "列出所有项目",
        "本站一共有多少篇文章？",
        "List all projects",
        "How many articles are on this site?",
    ]:
        assert scope_code(question) == "completeness_unverified"
    for question in [
        "最新文章是哪篇？",
        "他目前在哪家公司任职？",
        "What is the latest article?",
        "Where does he currently work?",
    ]:
        assert scope_code(question) == "freshness_unverified"
    for question in [
        "项目用了什么？",
        "举例列出几个项目",
        "如何统计SQLite所有行？",
        "How to count all rows in SQLite?",
        "简历里2020年的角色是什么？",
        "Python first-class functions是什么？",
    ]:
        assert scope_code(question) is None
    assert not needs_reference("Python first-class functions是什么？")
    assert not needs_reference("其他项目有哪些特点？")


def test_scope_notices_precede_all_provider_calls(tmp_path, monkeypatch):
    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        csrf = _create_session(client)
        online = client.app.state.assistant

        def forbidden(*args, **kwargs):
            raise AssertionError("scope notice must precede provider dispatch")

        monkeypatch.setattr(online.embeddings, "embed_query_metered", forbidden)
        for n, (question, code) in enumerate(
            [
                ("列出所有项目", "completeness_unverified"),
                ("最新文章是哪篇？", "freshness_unverified"),
            ]
        ):
            status, body = _sse_body(client, csrf, question, idem=f"scope-notice-{n}-0001")
            assert status == 200 and code in body
            assert "insufficient_evidence" not in body and "event: answer" not in body
        assert online.chat.calls == []
        assert (
            online.control.read(
                lambda c: c.execute(
                    "SELECT COUNT(*) FROM assistant_attempts "
                    "WHERE status IN ('sending','succeeded','unknown')",
                ).fetchone()[0]
            )
            == 0
        )
