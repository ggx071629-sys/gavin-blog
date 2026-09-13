from __future__ import annotations

import threading
from dataclasses import replace

from sqlalchemy import select

from app.assistant.hydrate import Evidence
from app.assistant.output import ValidatedAnswer, validate_model_answer
from app.assistant.prompt import build_prompt
from app.assistant.providers import (
    AnswerBlock,
    DeterministicChatModel,
    ModelAnswer,
    ScriptedChatTurn,
)
from app.assistant_resume.schemas import status_view
from app.assistant_resume.storage import bind, fail, usable_version
from app.models import AssistantIndexWorkerState, AssistantResumeVersion
from app.time_utils import utc_now

from .test_assistant_index import _activate_ready_generation, _runtime, _session
from .test_assistant_online import _create_session, _online_client, _publish_and_index, _sse_body
from .test_assistant_resume_storage import import_fixture, lease_fixture


def test_resume_pdf_snapshot_is_exact_revocable_and_read_only(client):
    runtime = _runtime(client)
    with _session(client) as db:
        bind(db, "https://example.com/resume.pdf")
        version_id = import_fixture(db)
        original = db.get(AssistantResumeVersion, version_id).pdf_bytes
        from datetime import timedelta

        db.get(AssistantIndexWorkerState, 1).lease_expires_at = utc_now() - timedelta(seconds=1)
        db.commit()
    path = f"/api/v1/assistant/resume/{version_id}"
    assert client.get(path).status_code == 404
    _activate_ready_generation(client, runtime)
    response = client.get(path)
    assert response.status_code == 200 and response.content == original
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-disposition"] == 'attachment; filename="gavin-resume.pdf"'
    assert "set-cookie" not in response.headers
    with _session(client) as db:
        indexed = status_view(db).last_indexed_at
        assert indexed is not None
        fail(db, lease_fixture(db), "download_timeout")
        db.commit()
        assert status_view(db).last_indexed_at == indexed
        assert not status_view(db).usable
    assert client.get(path).status_code == 404
    for invalid in ("unknown", "A" * 32, "0" * 32):
        result = client.get("/api/v1/assistant/resume/" + invalid)
        assert result.status_code == 404 and result.headers["cache-control"] == "no-store"
    with _session(client) as db:
        bind(db, "https://example.com/new.pdf")
        db.commit()
        assert not list(db.scalars(select(AssistantResumeVersion)))
    assert client.get(path).status_code == 404
    assert client.app.state.assistant is None  # PDF route never boots an online/model session.


def test_resume_self_report_conflict_and_unaliased_operational_notice():
    resume = Evidence(
        alias="c1",
        chunk_id="resume-chunk",
        title="Gavin 简历",
        heading_path="第 1 页",
        public_path="/api/v1/assistant/resume/" + "a" * 32,
        body="简历自述：后端工程师。",
        source_type="resume",
        source_id=1,
        source_version="a" * 32,
        generation_id=1,
        sources=("fts",),
    )
    profile = replace(
        resume,
        alias="c2",
        chunk_id="profile-chunk",
        title="Gavin",
        public_path="/",
        body="个人资料自述：前端工程师。",
        source_type="profile",
    )
    prompt = build_prompt(
        question="Gavin 的岗位是什么？",
        evidence=[resume, profile],
        history=[],
        provider=object(),
        max_input_tokens=20000,
        max_output_tokens=1000,
        context_window_tokens=22000,
        resume_available=True,
    )
    assert "Resume entries are self-reported facts, not proof of mastery" in prompt.messages[0][1]
    assert "state the disagreement and cite both sources" in prompt.messages[0][1]
    parsed = ModelAnswer(
        blocks=[
            AnswerBlock(
                text="两份自述的岗位不同，简历为后端，个人资料为前端。", citation_ids=["c1", "c2"],
                supports=[{"citation_id": "c1", "quote": resume.body},
                          {"citation_id": "c2", "quote": profile.body}],
            )
        ]
    )
    result = validate_model_answer(
        parsed, [resume, profile], finish_reason="stop", resume_available=True
    )
    assert isinstance(result, ValidatedAnswer)
    assert [c["path"] for c in result.citations] == [resume.public_path, "/"]
    notice = AnswerBlock(text="简历当前不可用。", citation_ids=[])
    partial = ModelAnswer(
        blocks=[AnswerBlock(text="个人资料自述为前端工程师。", citation_ids=["c2"],
            supports=[{"citation_id": "c2", "quote": profile.body}]), notice]
    )
    result = validate_model_answer(partial, [profile], finish_reason="stop", resume_available=False)
    assert isinstance(result, ValidatedAnswer) and result.text.endswith("简历当前不可用。")
    assert len(result.citations) == 1 and result.resume_notice == notice.text
    assert (
        validate_model_answer(partial, [profile], finish_reason="stop", resume_available=True)
        == "citation"
    )
    assert (
        validate_model_answer(
            ModelAnswer(blocks=[notice]), [profile], finish_reason="stop", resume_available=False
        )
        == "citation"
    )
    forged = ModelAnswer(blocks=[AnswerBlock(text="任意无依据的断言", citation_ids=[])])
    assert (
        validate_model_answer(forged, [profile], finish_reason="stop", resume_available=False)
        == "citation"
    )
    unavailable = build_prompt(
        question="简历还有哪些经历？",
        evidence=[profile],
        history=[],
        provider=object(),
        max_input_tokens=20000,
        max_output_tokens=1000,
        context_window_tokens=22000,
        resume_available=False,
    )
    assert "operational notice is not evidence and has no alias" in unavailable.messages[0][1]


def test_resume_graph_rechecks_before_provider_and_after_generation(tmp_path, monkeypatch):
    from app.assistant import graph as graph_module

    original_next = DeterministicChatModel._next
    original_validate = graph_module.validate_model_answer
    for phase in ("before", "during", "publish"):
        monkeypatch.setattr(DeterministicChatModel, "_next", original_next)
        monkeypatch.setattr(graph_module, "validate_model_answer", original_validate)
        with _online_client(tmp_path / phase, assistant_chat_max_input_tokens=12000) as client:
            online = client.app.state.assistant
            with _session(client) as db:
                bind(db, "https://example.com/resume.pdf")
                version = import_fixture(
                    db, "Zebraresume is an explicitly stated personal backend role."
                )
                from datetime import timedelta

                db.get(AssistantIndexWorkerState, 1).lease_expires_at = utc_now() - timedelta(
                    seconds=1
                )
                db.commit()
            _publish_and_index(client)
            with _session(client) as db:
                assert usable_version(db).id == version
            model = online.chat

            class Gate:
                entered = threading.Event()
                released = threading.Event()

                def wait(self, timeout):
                    self.entered.set()
                    return self.released.wait(timeout)

            gate = Gate()
            if phase == "before":
                online.pause_before_send = gate

            def reply(self, messages, client=client):
                self.calls.append(messages)
                with _session(client) as db:
                    bind(db, None)
                    db.commit()
                return ScriptedChatTurn(
                    parsed={
                        "blocks": [{"text": "Zebraresume personal role.", "citation_ids": ["c1"]}]
                    },
                    finish_reason="stop",
                )

            if phase == "during":
                monkeypatch.setattr(DeterministicChatModel, "_next", reply)
            if phase == "publish":

                def revoke_after_validation(*args, client=client, **kwargs):
                    result = original_validate(*args, **kwargs)
                    assert isinstance(result, ValidatedAnswer)
                    with _session(client) as db:
                        bind(db, None)
                        db.commit()
                    return result

                monkeypatch.setattr(graph_module, "validate_model_answer", revoke_after_validation)
            csrf = _create_session(client)
            results = []

            def ask(client=client, csrf=csrf, results=results, phase=phase):
                results.append(
                    _sse_body(
                        client,
                        csrf,
                        "What personal role does Zebraresume state in the resume?",
                        idem="resume-revoke-" + phase + "-0001",
                    )
                )

            thread = threading.Thread(target=ask)
            thread.start()
            if phase == "before":
                assert gate.entered.wait(10)
                thread_id = online.control.read(
                    lambda conn: conn.execute(
                        "SELECT thread_id FROM assistant_turns ORDER BY created_at DESC LIMIT 1"
                    ).fetchone()["thread_id"]
                )
                snapshot = client.portal.call(
                    online.graph.aget_state,
                    {
                        "configurable": {"thread_id": thread_id},
                    },
                )
                assert any(e["source_type"] == "resume" for e in snapshot.values["evidence"])
                assert all(
                    "body" not in e and "page_content" not in e for e in snapshot.values["evidence"]
                )
                with _session(client) as db:
                    bind(db, None)
                    db.commit()
                gate.released.set()
            thread.join(20)
            assert not thread.is_alive() and results
            assert results[0][0] == 200 and "event: answer" not in results[0][1]
            assert len(model.calls) == (0 if phase == "before" else 1)
            assert client.get("/api/v1/assistant/resume/" + version).status_code == 404
