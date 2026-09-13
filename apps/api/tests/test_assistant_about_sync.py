from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.assistant.admin_operations import task_view
from app.assistant_index.worker_control import WorkerFenceLost, require_source_revision
from app.models import AboutPage, AboutPageRevision, AssistantIndexTask

from .conftest import login


def test_about_publish_rollback_outbox_and_source_fence(client):
    snapshot = Path(__file__).resolve().parents[3] / "packages/contracts/openapi.json"
    assert json.loads(snapshot.read_text(encoding="utf-8")) == client.app.openapi()
    headers = {"X-CSRF-Token": login(client)}
    base = "/api/v1/admin/about-page"
    seeded = client.get(base).json()
    with client.app.state.database.session_factory() as db:
        assert list(db.scalars(select(AssistantIndexTask))) == []
    draft = {**seeded["content"], "statement": "发布的工程自述"}
    saved = client.patch(base, headers=headers, json={
        "content": draft, "version": seeded["version"],
    }).json()
    with client.app.state.database.session_factory() as db:
        assert list(db.scalars(select(AssistantIndexTask))) == []
    published = client.post(base + "/publish", headers=headers, json={
        "version": saved["version"],
    })
    assert published.status_code == 200
    first = published.json()
    with client.app.state.database.session_factory() as db:
        tasks = list(db.scalars(select(AssistantIndexTask)))
        assert len(tasks) == 1
        assert tasks[0].target_version == str(first["current_revision_id"])
        assert task_view(tasks[0]).source_type == "about"
    rolled = client.post(base + f"/revisions/{seeded['current_revision_id']}/rollback",
        headers=headers, json={
            "version": first["version"], "current_revision_id": first["current_revision_id"],
            "rollback_confirmed": True,
        })
    assert rolled.status_code == 200
    current = rolled.json()
    with client.app.state.database.session_factory() as db:
        tasks = list(db.scalars(select(AssistantIndexTask)))
        assert len(tasks) == 1
        assert tasks[0].target_version == str(current["current_revision_id"])
        assert tasks[0].status == "pending"
    runtime = SimpleNamespace(
        database=client.app.state.database, settings=client.app.state.settings,
    )
    with pytest.raises(WorkerFenceLost):
        require_source_revision(runtime, source_type="about", source_id=1,
                                expected_version=str(first["current_revision_id"]))
    require_source_revision(runtime, source_type="about", source_id=1,
                            expected_version=str(current["current_revision_id"]))


def test_about_failed_enqueue_rolls_back_publish_transaction(client, monkeypatch):
    from app.assistant_index import outbox

    headers = {"X-CSRF-Token": login(client)}
    base = "/api/v1/admin/about-page"
    seeded = client.get(base).json()

    def fail(*args, **kwargs):
        raise RuntimeError("simulated outbox failure")

    monkeypatch.setattr(outbox, "enqueue_about", fail)
    with pytest.raises(RuntimeError, match="simulated outbox failure"):
        client.post(base + "/publish", headers=headers, json={"version": seeded["version"]})
    with client.app.state.database.session_factory() as db:
        assert db.get(AboutPage, 1).current_revision_id == seeded["current_revision_id"]
        assert len(list(db.scalars(select(AboutPageRevision)))) == 1
        assert list(db.scalars(select(AssistantIndexTask))) == []
