from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import timedelta

from sqlalchemy import select

from app.assistant.hydrate import hydrate_descriptors, hydrate_evidence
from app.assistant.providers import DeterministicChatModel, ScriptedChatTurn
from app.assistant_index.worker import process_once
from app.assistant_resume import queue
from app.assistant_resume.download import DownloadedPdf, DownloadError
from app.models import AssistantResumeSource, AssistantResumeVersion
from app.time_utils import utc_now

from .conftest import login
from .test_assistant_index import _session
from .test_assistant_online import _create_session, _online_client, _publish_and_index, _sse_body
from .test_assistant_resume_parse import pdf_fixture
from .test_profile import profile_payload

PROFILE = "/api/v1/admin/profile"
ABOUT = "/api/v1/admin/about-page"


def publish_about(client, headers, statement):
    current = client.get(ABOUT).json()
    saved = client.patch(
        ABOUT,
        headers=headers,
        json={
            "version": current["version"],
            "content": {**current["content"], "statement": statement},
        },
    )
    assert saved.status_code == 200
    published = client.post(
        ABOUT + "/publish", headers=headers, json={"version": saved.json()["version"]}
    )
    assert published.status_code == 200
    return published.json()


def prepare(client, monkeypatch):
    headers = {"X-CSRF-Token": login(client)}
    publish_about(client, headers, "Zebraportfolio self-report: frontend engineer.")
    saved = client.patch(PROFILE, headers=headers, json=profile_payload())
    assert saved.status_code == 200
    body = pdf_fixture(["Zebraportfolio self-report: backend engineer."])
    monkeypatch.setattr(
        queue,
        "download_pdf",
        lambda *a, **kw: DownloadedPdf(body, hashlib.sha256(body).hexdigest()),
    )
    runtime = client.app.state.assistant.index_runtime
    assert queue.process_resume_once(runtime)  # Real child parser and content transaction.
    assert client.get(PROFILE + "/resume").json()["state"] == "indexing"
    _publish_and_index(client)  # Real rebuild and API-owner finalize; also publishes an article.
    ready = client.get(PROFILE + "/resume").json()
    assert ready["state"] == "ready" and ready["usable"]
    return {"X-CSRF-Token": login(client)}, body, ready


def answering(monkeypatch, *, partial=False, article=False):
    def reply(self, messages):
        self.calls.append(list(messages))
        user = messages[-1][1] if isinstance(messages[-1], tuple) else messages[-1].content
        descriptors = [
            json.loads(html.unescape(attrs))
            for attrs in re.findall(r"<untrusted-evidence descriptor=(.*?)>\n", user)
        ]
        quotes = {
            json.loads(html.unescape(attrs))["id"]: html.unescape(body)
            for attrs, body in re.findall(
                r"<untrusted-evidence descriptor=(.*?)>\n(.*?)\n</untrusted-evidence>",
                user,
                re.DOTALL,
            )
        }
        # A source may contribute several chunks. Bind the model fixture to
        # the actual role statement, not the last (potentially unrelated) chunk
        # of that type. The validator must reject the latter as unsupported.
        by_type = {}
        for item in descriptors:
            kind = item["source_type"]
            if kind in {"about", "resume"} and "self-report:" not in quotes[item["id"]]:
                continue
            by_type.setdefault(kind, item)
        if article:
            assert "article" in by_type
            blocks = [
                {
                    "text": "The article discusses Python.",
                    "citation_ids": [by_type["article"]["id"]],
                }
            ]
        elif partial:
            assert "about" in by_type and "resume" not in by_type
            blocks = [
                {
                    "text": "About self-reports frontend work.",
                    "citation_ids": [by_type["about"]["id"]],
                },
                {"text": "Resume evidence is currently unavailable.", "citation_ids": []},
            ]
        else:
            assert "about" in by_type and "resume" in by_type
            blocks = [
                {
                    "text": "About and resume disagree on the stated role; both are self-reports.",
                    "citation_ids": [by_type["about"]["id"], by_type["resume"]["id"]],
                }
            ]
        for block in blocks:
            block["supports"] = [
                {"citation_id": alias, "quote": quotes[alias][:1200]}
                for alias in block["citation_ids"]
            ]
        return ScriptedChatTurn(parsed={"blocks": blocks}, finish_reason="stop")

    monkeypatch.setattr(DeterministicChatModel, "_next", reply)


def ask(client, question, key):
    csrf = _create_session(client)
    before = len(client.app.state.assistant.chat.calls)
    status, body = _sse_body(client, csrf, question, idem=key)
    assert status == 200 and body.count("event: answer") == 1, body
    assert len(client.app.state.assistant.chat.calls) == before + 1
    for block in body.split("\n\n"):
        if "event: answer\n" in block:
            return json.loads(
                next(line[6:] for line in block.splitlines() if line.startswith("data: "))
            )
    raise AssertionError(body)


def drain(runtime):
    for _ in range(30):
        if not process_once(runtime):
            return
    raise AssertionError("fixture worker did not become idle")


def test_two_sources_import_retrieve_answer_and_keep_article_flow(tmp_path, monkeypatch):
    with _online_client(
        tmp_path, assistant_chat_max_input_tokens=30000, assistant_chat_context_window_tokens=32000
    ) as client:
        _, original, ready = prepare(client, monkeypatch)
        runtime = client.app.state.assistant.index_runtime
        with _session(client) as db:
            found = hydrate_evidence(db, runtime, "Zebraportfolio", limit=8, max_chars=10000)
            assert {"about", "resume"} <= {e.source_type for e in found.evidence}
            assert sum(len(e.body) for e in found.evidence) <= 10000
            for source_type in ("about", "resume"):
                assert any(
                    e.source_type == source_type and {"fts", "dense"} <= set(e.sources)
                    for e in found.evidence
                )
            assert not hydrate_evidence(
                db, runtime, "Zebraportfolio", limit=8, max_chars=1
            ).evidence
        answering(monkeypatch)
        answer = ask(
            client,
            "What does Zebraportfolio state about the personal role?",
            "sources-integration-success-01",
        )
        paths = {c["path"] for c in answer["citations"]}
        pdf_path = "/api/v1/assistant/resume/" + ready["version_id"]
        assert paths == {"/about", pdf_path}
        assert client.get(pdf_path).content == original
        answering(monkeypatch, article=True)
        answer = ask(
            client, "What does the Python article discuss?", "sources-integration-article-01"
        )
        assert len(answer["citations"]) == 1 and "/notes/" in answer["citations"][0]["path"]


def test_two_sources_replace_pause_clear_and_about_publication_gap(tmp_path, monkeypatch):
    with _online_client(
        tmp_path, assistant_chat_max_input_tokens=30000, assistant_chat_context_window_tokens=32000
    ) as client:
        headers, _, ready = prepare(client, monkeypatch)
        runtime = client.app.state.assistant.index_runtime
        old_path = "/api/v1/assistant/resume/" + ready["version_id"]
        new_body = pdf_fixture(["Zebraportfolio new self-report: systems engineer."])
        monkeypatch.setattr(
            queue,
            "download_pdf",
            lambda *a, **kw: DownloadedPdf(new_body, hashlib.sha256(new_body).hexdigest()),
        )
        assert (
            client.post(
                PROFILE + "/resume/refresh",
                headers=headers,
                json={"binding_epoch": ready["binding_epoch"]},
            ).status_code
            == 202
        )
        assert queue.process_resume_once(runtime)
        assert client.get(old_path).status_code == 404
        assert not client.get(PROFILE + "/resume").json()["usable"]
        drain(runtime)
        current = client.get(PROFILE + "/resume").json()
        assert current["usable"] and current["version_id"] != ready["version_id"]
        answering(monkeypatch)
        answer = ask(
            client,
            "What personal role does Zebraportfolio state?",
            "sources-integration-replaced-01",
        )
        new_path = "/api/v1/assistant/resume/" + current["version_id"]
        assert {c["path"] for c in answer["citations"]} == {"/about", new_path}
        assert client.get(new_path).content == new_body
        # Advance only the manual cooldown fixture, without sleeps or periodic checks.
        with _session(client) as db:
            db.get(AssistantResumeSource, 1).last_refresh_at = utc_now() - timedelta(seconds=61)
            db.commit()

        def unavailable(*args, **kwargs):
            raise DownloadError("download_timeout")

        monkeypatch.setattr(queue, "download_pdf", unavailable)
        assert (
            client.post(
                PROFILE + "/resume/refresh",
                headers=headers,
                json={"binding_epoch": current["binding_epoch"]},
            ).status_code
            == 202
        )
        assert queue.process_resume_once(runtime)
        assert client.get(new_path).status_code == 404
        answering(monkeypatch, partial=True)
        answer = ask(
            client,
            "What does Zebraportfolio state in about and resume?",
            "sources-integration-paused-01",
        )
        assert {c["path"] for c in answer["citations"]} == {"/about"}
        assert "Resume evidence is currently unavailable." in json.dumps(answer)
        with _session(client) as db:
            found = hydrate_evidence(db, runtime, "Zebraportfolio", limit=8, max_chars=10000)
            old_about = [e.descriptor() for e in found.evidence if e.source_type == "about"]
            assert old_about
        publish_about(client, headers, "Replacementportfolio is my new engineering focus.")
        with _session(client) as db:
            assert hydrate_descriptors(db, old_about) == []
        saved = client.get(PROFILE).json()
        assert (
            client.patch(
                PROFILE,
                headers=headers,
                json=profile_payload(version=saved["version"], resume_url=None),
            ).status_code
            == 200
        )
        with _session(client) as db:
            assert not list(db.scalars(select(AssistantResumeVersion)))
        drain(runtime)
        assert client.get(new_path).status_code == 404
        with _session(client) as db:
            found = hydrate_evidence(db, runtime, "Replacementportfolio", limit=8, max_chars=10000)
            assert any(e.source_type == "about" for e in found.evidence)
            assert all(e.source_type != "resume" for e in found.evidence)
