from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text

from app.assistant.admin_operations import task_view
from app.assistant.hydrate import hydrate_descriptors, hydrate_evidence
from app.assistant_index.outbox import enqueue_task
from app.assistant_index.projector import project_resume
from app.assistant_index.worker import process_once
from app.assistant_resume.download import DownloadedPdf
from app.assistant_resume.parse import ParsedPdf
from app.assistant_resume.storage import (
    ResumeLease,
    ResumeLeaseLost,
    accept_download,
    accept_parsed,
    bind,
    fail,
    source,
    usable_version,
)
from app.config import get_settings
from app.models import (
    AssistantChunk,
    AssistantIndexGeneration,
    AssistantIndexTask,
    AssistantIndexWorkerState,
    AssistantResumeRequest,
    AssistantResumeVersion,
)
from app.time_utils import utc_now

from .test_assistant_index import _activate_ready_generation, _runtime, _session


def lease_fixture(db):
    row = source(db)
    owner = db.get(AssistantIndexWorkerState, 1)
    if owner is None:
        owner = AssistantIndexWorkerState(id=1, fencing_token=1, owner_id="resume-test")
        db.add(owner)
    owner.lease_expires_at = utc_now() + timedelta(minutes=10)
    request = AssistantResumeRequest(
        id=uuid4().hex,
        binding_epoch=row.binding_epoch,
        status="leased",
        lease_owner=owner.owner_id,
        worker_fence=owner.fencing_token,
        lease_token=uuid4().hex,
        lease_expires_at=owner.lease_expires_at,
    )
    db.add(request)
    row.current_request_id = request.id
    row.state = "checking"
    db.flush()
    return ResumeLease(
        row.binding_epoch, request.id, owner.owner_id, request.lease_token, owner.fencing_token
    )


def pdf(value="Zebraresume engineering experience"):
    body = b"%PDF-fixture " + value.encode()
    return DownloadedPdf(body, hashlib.sha256(body).hexdigest()), ParsedPdf((value,), value)


def import_fixture(db, value="Zebraresume engineering experience"):
    lease = lease_fixture(db)
    downloaded, parsed = pdf(value)
    assert accept_download(db, lease, downloaded)
    db.commit()  # Suspension is visible before parsing starts.
    version = accept_parsed(db, lease, downloaded, parsed)
    db.commit()
    return version.id


def test_resume_cache_reuse_binding_revocation_and_migration(client, tmp_path, monkeypatch):
    snapshot = Path(__file__).resolve().parents[3] / "packages/contracts/openapi.json"
    assert json.loads(snapshot.read_text(encoding="utf-8")) == client.app.openapi()
    with _session(client) as db:
        bind(db, "https://example.com/a.pdf")
        first_epoch = source(db).binding_epoch
        first_id = import_fixture(db)
        task = db.scalar(
            select(AssistantIndexTask).where(AssistantIndexTask.source_type == "resume")
        )
        assert task_view(task).source_type == "resume"
        lease = lease_fixture(db)
        fail(db, lease, "download_timeout")
        db.commit()
        assert project_resume(db) is None
        assert db.get(AssistantResumeVersion, first_id) is not None
        lease = lease_fixture(db)
        assert accept_download(db, lease, pdf()[0]) is False
        db.commit()
        assert project_resume(db).source_version == first_id
        assert len(list(db.scalars(select(AssistantResumeVersion)))) == 1
        bind(db, "https://example.com/a.pdf")
        assert source(db).binding_epoch == first_epoch
        bind(db, "https://example.com/b.pdf")
        db.commit()
        assert db.get(AssistantResumeVersion, first_id) is None
        assert project_resume(db) is None
        bind(db, "https://example.com/a.pdf")
        assert source(db).binding_epoch == first_epoch + 2
        new_id = import_fixture(db)
        assert new_id != first_id
        bind(db, None)
        db.commit()
        assert list(db.scalars(select(AssistantResumeVersion))) == []
        assert usable_version(db) is None
    url = "sqlite:///" + (tmp_path / "resume-upgrade.db").as_posix()
    monkeypatch.setenv("GAVIN_DATABASE_URL", url)
    get_settings.cache_clear()
    engine = create_engine(url)
    try:
        config = Config("alembic.ini")
        command.upgrade(config, "20260911_0029")
        with engine.begin() as conn:
            conn.execute(text("UPDATE profiles SET title='preserved' WHERE id=1"))
        command.upgrade(config, "20260911_0030")
        assert "assistant_resume_versions" in inspect(engine).get_table_names()
        with engine.connect() as conn:
            assert conn.scalar(text("SELECT title FROM profiles WHERE id=1")) == "preserved"
        command.downgrade(config, "20260911_0029")
        assert "assistant_resume_versions" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()
        get_settings.cache_clear()


def test_resume_late_results_fail_closed_and_new_hash_suspends_before_parse(client):
    with _session(client) as db:
        bind(db, "https://example.com/a.pdf")
        old_id = import_fixture(db)
        lease = lease_fixture(db)
        db.commit()
        for invalid in (
            replace(lease, epoch=lease.epoch + 1),
            replace(lease, request_id="stale"),
            replace(lease, owner="other"),
            replace(lease, token="stale"),
            replace(lease, fence=lease.fence + 1),
        ):
            with pytest.raises(ResumeLeaseLost):
                accept_download(db, invalid, pdf("new")[0])
            db.rollback()
        with pytest.raises(ResumeLeaseLost):
            accept_download(db, lease, pdf()[0], now=utc_now() + timedelta(hours=1))
        db.rollback()
        assert accept_download(db, lease, pdf("new")[0])
        db.commit()
        assert project_resume(db) is None
        assert db.get(AssistantResumeVersion, old_id) is not None
        new_lease = lease_fixture(db)
        db.commit()
        with pytest.raises(ResumeLeaseLost):
            accept_parsed(db, lease, *pdf("new"))
        db.rollback()
        fail(db, new_lease, "secret third-party response")
        db.commit()
        assert source(db).error_code == "download_failed"
        assert project_resume(db) is None
        lease = lease_fixture(db)
        bind(db, None)
        db.commit()
        with pytest.raises(ResumeLeaseLost):
            accept_download(db, lease, pdf()[0])
        db.rollback()
        assert list(db.scalars(select(AssistantResumeVersion))) == []


def test_resume_retrieval_and_delayed_version_purge_preserve_new_version(client):
    runtime = _runtime(client)
    with _session(client) as db:
        bind(db, "https://example.com/a.pdf")
        old_id = import_fixture(db)
        assert usable_version(db) is None
        # Release the fixture owner so the actual worker can acquire its lease.
        db.get(AssistantIndexWorkerState, 1).lease_expires_at = utc_now() - timedelta(seconds=1)
        db.commit()
    _activate_ready_generation(client, runtime)
    _activate_ready_generation(client, runtime)  # Keep an older generation for purge coverage.
    with _session(client) as db:
        generations = list(db.scalars(select(AssistantIndexGeneration)))
        for generation in generations:
            # Simulate a vector write whose corresponding SQLite transaction was lost.
            runtime.store.upsert_points(
                generation.collection_name,
                generation_id=generation.id,
                items=[
                    (
                        "orphan-resume",
                        [0.1] * 32,
                        {
                            "chunk_id": "orphan-resume",
                            "source_type": "resume",
                            "source_id": 1,
                            "source_version": old_id,
                            "generation": generation.id,
                            "pipeline_version": generation.pipeline_version,
                        },
                    )
                ],
            )
        assert usable_version(db).id == old_id
        found = hydrate_evidence(db, runtime, "Zebraresume", limit=8, max_chars=10000)
        evidence = [e for e in found.evidence if e.source_type == "resume"]
        assert evidence and any(set(e.sources) == {"dense", "fts"} for e in evidence)
        descriptors = [e.descriptor() for e in evidence]
        lease = lease_fixture(db)
        fail(db, lease, "download_timeout")
        db.commit()
        assert usable_version(db) is None
        assert hydrate_descriptors(db, descriptors) == []
        new_id = import_fixture(db, "Newresume backend experience")
        assert new_id != old_id
        assert hydrate_descriptors(db, descriptors) == []
        # Defer old cleanup until after the new upsert, simulating delayed retry.
        for task in db.scalars(
            select(AssistantIndexTask).where(
                AssistantIndexTask.source_type == "resume",
                AssistantIndexTask.operation == "purge",
            )
        ):
            task.available_at = utc_now() + timedelta(days=1)
        db.commit()
    for _ in range(10):
        if not process_once(runtime):
            break
    with _session(client) as db:
        assert usable_version(db).id == new_id
        for task in db.scalars(
            select(AssistantIndexTask).where(
                AssistantIndexTask.source_type == "resume",
                AssistantIndexTask.operation == "purge",
            )
        ):
            task.available_at = utc_now() - timedelta(seconds=1)
        # Add another old tombstone; it must not merge with the new upsert.
        enqueue_task(
            db, source_type="resume", source_id=1, target_version=old_id, operation="purge"
        )
        db.commit()
    for _ in range(10):
        if not process_once(runtime):
            break
    with _session(client) as db:
        assert usable_version(db).id == new_id
        assert not list(
            db.scalars(
                select(AssistantChunk).where(
                    AssistantChunk.source_type == "resume",
                    AssistantChunk.source_version == old_id,
                )
            )
        )
        for generation in db.scalars(select(AssistantIndexGeneration)):
            points, _ = runtime.store.client.scroll(generation.collection_name, limit=100)
            assert all(p.payload.get("source_version") != old_id for p in points)
        found = hydrate_evidence(db, runtime, "Newresume", limit=8, max_chars=10000)
        assert any(e.source_type == "resume" and e.source_version == new_id for e in found.evidence)
