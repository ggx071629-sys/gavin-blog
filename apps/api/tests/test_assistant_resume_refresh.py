from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import select, text

from app.assistant_index.worker import process_once
from app.assistant_resume import queue
from app.assistant_resume.download import DownloadedPdf, DownloadError
from app.assistant_resume.schemas import status_view
from app.content_write_fence import content_write_fence
from app.models import (
    AssistantResumeRequest,
    AssistantResumeVersion,
)

from .conftest import login
from .test_assistant_index import FakeClock, _activate_ready_generation, _runtime, _session
from .test_assistant_resume_parse import pdf_fixture
from .test_profile import profile_payload

BASE = "/api/v1/admin/profile"


def configured(client):
    headers = {"X-CSRF-Token": login(client)}
    response = client.patch(BASE, headers=headers, json=profile_payload())
    assert response.status_code == 200
    return headers, response.json()


def test_resume_refresh_api_auth_epoch_coalescing_cooldown_and_atomicity(client, monkeypatch):
    assert client.get(BASE + "/resume").status_code == 401
    assert client.post(BASE + "/resume/refresh", json={"binding_epoch": 0}).status_code == 401
    headers = {"X-CSRF-Token": login(client)}
    assert client.post(BASE + "/resume/refresh", json={"binding_epoch": 0}).status_code == 403
    assert (
        client.post(
            BASE + "/resume/refresh", headers=headers, json={"binding_epoch": 0}
        ).status_code
        == 409
    )
    initial = client.get(BASE + "/resume")
    assert initial.headers["cache-control"] == "no-store"
    assert initial.json()["state"] == "unconfigured"
    saved = client.patch(BASE, headers=headers, json=profile_payload()).json()
    view = client.get(BASE + "/resume").json()
    epoch, request_id = view["binding_epoch"], view["request_id"]
    assert view["state"] == "pending" and not view["usable"]
    wrong = client.post(
        BASE + "/resume/refresh", headers=headers, json={"binding_epoch": epoch + 1}
    )
    assert wrong.status_code == 409
    same = client.post(BASE + "/resume/refresh", headers=headers, json={"binding_epoch": epoch})
    assert same.status_code == 202 and same.json()["request_id"] == request_id
    assert same.headers["cache-control"] == "no-store"
    changed = client.patch(
        BASE, headers=headers, json=profile_payload(version=saved["version"], title="New title")
    )
    assert changed.status_code == 200
    assert client.get(BASE + "/resume").json()["request_id"] == request_id
    with _session(client) as db:
        db.get(AssistantResumeRequest, request_id).status = "failed"
        db.commit()
    manual = client.post(BASE + "/resume/refresh", headers=headers, json={"binding_epoch": epoch})
    assert manual.status_code == 202 and manual.json()["request_id"] != request_id
    with _session(client) as db:
        db.get(AssistantResumeRequest, manual.json()["request_id"]).status = "succeeded"
        db.commit()
    cooldown = client.post(BASE + "/resume/refresh", headers=headers, json={"binding_epoch": epoch})
    assert cooldown.status_code == 429 and 1 <= int(cooldown.headers["retry-after"]) <= 60
    from app.routes import admin_profile

    def broken(*args):
        raise RuntimeError("enqueue fixture failed")

    monkeypatch.setattr(admin_profile, "sync_binding", broken)
    with pytest.raises(RuntimeError):
        client.patch(
            BASE,
            headers=headers,
            json=profile_payload(version=changed.json()["version"], resume_url=None),
        )
    assert client.get(BASE).json()["resume_url"] == saved["resume_url"]
    assert client.get(BASE + "/resume").json()["binding_epoch"] == epoch
    snapshot = Path(__file__).resolve().parents[3] / "packages/contracts/openapi.json"
    assert json.loads(snapshot.read_text(encoding="utf-8")) == client.app.openapi()


def test_resume_worker_import_manual_reuse_no_timer_and_replacement_during_download(
    client, monkeypatch
):
    headers, saved = configured(client)
    runtime = _runtime(client)
    runtime.settings.assistant_resume_trusted_hosts = "example.com"
    data = pdf_fixture(["Zebraresume public engineering experience"])
    calls, parses = [], []
    real_parse = queue.parse_pdf

    def parse(body):
        parses.append(body)
        return real_parse(body)

    def download(url, hosts, **kwargs):
        calls.append(url)
        assert hosts == ("example.com",) and kwargs["force_refresh"]
        # Download holds neither SQLite write transaction nor backup write lock.
        with content_write_fence(runtime.settings):
            with _session(client) as db:
                db.execute(text("BEGIN IMMEDIATE"))
                db.rollback()
        if len(calls) == 1:
            response = client.patch(
                BASE,
                headers=headers,
                json=profile_payload(
                    version=saved["version"], resume_url="https://example.com/new.pdf"
                ),
            )
            assert response.status_code == 200
        return DownloadedPdf(data, hashlib.sha256(data).hexdigest())

    monkeypatch.setattr(queue, "download_pdf", download)
    monkeypatch.setattr(queue, "parse_pdf", parse)
    assert process_once(runtime)
    assert parses == []  # Replaced download is fenced before parsing.
    with _session(client) as db:
        assert list(db.scalars(select(AssistantResumeVersion))) == []
    assert process_once(runtime)
    assert len(calls) == 2 and len(parses) == 1
    checking = client.get(BASE + "/resume").json()
    assert checking["state"] == "indexing" and checking["last_checked_at"]
    assert checking["last_indexed_at"] is None and not checking["usable"]
    _activate_ready_generation(client, runtime)
    ready = client.get(BASE + "/resume").json()
    assert ready["state"] == "ready" and ready["usable"] and ready["last_indexed_at"]
    refresh = client.post(
        BASE + "/resume/refresh", headers=headers, json={"binding_epoch": ready["binding_epoch"]}
    )
    assert refresh.status_code == 202
    assert process_once(runtime)
    again = client.get(BASE + "/resume").json()
    assert again["version_id"] == ready["version_id"] and again["usable"]
    assert len(calls) == 3 and len(parses) == 1
    for _ in range(3):
        assert not queue.process_resume_once(runtime)
        client.get(BASE + "/resume")
    assert len(calls) == 3
    latest = client.get(BASE).json()
    cleared = client.patch(
        BASE, headers=headers, json=profile_payload(version=latest["version"], resume_url=None)
    )
    assert cleared.status_code == 200
    assert client.get(BASE + "/resume").json()["state"] == "unconfigured"


def test_resume_retry_backoff_pause_and_restart_are_bounded(client, monkeypatch):
    configured(client)
    clock = FakeClock()
    runtime = _runtime(client, clock)
    data = pdf_fixture(["Public resume text"])
    monkeypatch.setattr(
        queue, "download_pdf", lambda *a, **k: DownloadedPdf(data, hashlib.sha256(data).hexdigest())
    )
    assert queue.process_resume_once(runtime)
    _activate_ready_generation(client, runtime)
    with _session(client) as db:
        view = status_view(db)
        assert view.usable
        queue.refresh(db, view.binding_epoch, now=clock())
        db.commit()
    attempts = []

    def fail_download(*args, **kwargs):
        attempts.append(clock())
        raise DownloadError("download_timeout", transient=True, retry_after=120)

    monkeypatch.setattr(queue, "download_pdf", fail_download)
    for delay in (120, 300, 900):
        assert queue.process_resume_once(runtime)
        with _session(client) as db:
            view = status_view(db)
            assert view.state == "failed" and not view.usable
            assert (view.retry_at - clock()).total_seconds() == delay
        assert not queue.process_resume_once(runtime)
        clock.advance(delay)
    assert queue.process_resume_once(runtime)
    assert len(attempts) == 4
    clock.advance(86400)
    assert not queue.process_resume_once(runtime)
    with _session(client) as db:
        view = status_view(db)
        assert view.retry_at is None and not view.usable
        queue.refresh(db, view.binding_epoch, now=clock())
        db.commit()
    # Simulate four crashes after the persisted claim. No infinite attempts on restart.
    for _ in range(4):
        with queue._write(runtime) as db:
            assert queue._claim(db, runtime) is not None
        clock.advance(queue.LEASE_SECONDS + 1)
    assert not queue.process_resume_once(runtime)
    with _session(client) as db:
        request = db.get(AssistantResumeRequest, status_view(db).request_id)
        assert request.status == "failed" and request.attempt_count == 4
        queue.refresh(db, status_view(db).binding_epoch, now=clock())
        db.commit()
    monkeypatch.setattr(
        queue, "download_pdf", lambda *a, **k: (_ for _ in ()).throw(DownloadError("blocked_host"))
    )
    assert queue.process_resume_once(runtime)
    with _session(client) as db:
        assert status_view(db).retry_at is None
        assert status_view(db).error_code == "blocked_host"


def test_resume_worker_bootstraps_existing_url_and_parse_failure_keeps_evidence_paused(
    client, monkeypatch
):
    from app.assistant_resume.parse import ParseError
    from app.profile_service import get_or_create_profile

    clock = FakeClock()
    runtime = _runtime(client, clock)
    data = pdf_fixture(["Public resume before update"])
    with _session(client) as db:
        profile = get_or_create_profile(db)
        profile.resume_url = "https://example.com/legacy.pdf"
        db.commit()
    calls = []

    def downloaded(*args, **kwargs):
        calls.append(args[0])
        return DownloadedPdf(data, hashlib.sha256(data).hexdigest())

    monkeypatch.setattr(queue, "download_pdf", downloaded)
    assert queue.process_resume_once(runtime)
    _activate_ready_generation(client, runtime)
    clock.advance(365 * 86400)
    assert not queue.process_resume_once(runtime)
    with _session(client) as db:
        before = status_view(db)
        assert before.usable
        queue.refresh(db, before.binding_epoch, now=clock())
        db.commit()
    data = pdf_fixture(["New PDF that cannot be parsed"])

    def failed_parse(body):
        with _session(client) as db:
            assert not status_view(db).usable
            assert status_view(db).state == "parsing"
        raise ParseError("text_unavailable")

    monkeypatch.setattr(queue, "parse_pdf", failed_parse)
    assert queue.process_resume_once(runtime)
    with _session(client) as db:
        after = status_view(db)
        assert not after.usable and after.error_code == "text_unavailable"
        assert after.version_id == before.version_id and after.retry_at is None
    assert len(calls) == 2
