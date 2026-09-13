from __future__ import annotations

from sqlalchemy import select

from app.about_page_service import (
    create_publish_revision,
    get_or_create_about_page,
    parse_content,
    serialize_content,
)
from app.assistant.hydrate import hydrate_descriptors, hydrate_evidence
from app.assistant_index.projector import iter_public_sources
from app.assistant_index.worker import process_once
from app.models import AssistantChunk

from .test_assistant_index import _activate_ready_generation, _runtime, _session


def test_about_rebuild_hybrid_budget_and_stale_evidence(client):
    runtime = _runtime(client)
    with _session(client) as db:
        page = get_or_create_about_page(db)
        assert "about" not in {d.source_type for d in iter_public_sources(db)}
        content = parse_content(page.content_json)
        content.statement = "Zebracapability is my explicitly published engineering focus."
        page.content_json = serialize_content(content)
        revision = create_publish_revision(db, page)
        old_version = str(revision.id)
        db.commit()
    _activate_ready_generation(client, runtime)
    with _session(client) as db:
        chunks = list(db.scalars(select(AssistantChunk).where(
            AssistantChunk.source_type == "about",
        )))
        assert chunks and {c.source_version for c in chunks} == {old_version}
        found = hydrate_evidence(db, runtime, "Zebracapability", limit=8, max_chars=10000)
        about = [item for item in found.evidence if item.source_type == "about"]
        assert about
        assert any(set(item.sources) == {"fts", "dense"} for item in about)
        assert sum(len(item.body) for item in found.evidence) <= 10000
        assert not hydrate_evidence(db, runtime, "Zebracapability", limit=8, max_chars=1).evidence
        descriptors = [item.descriptor() for item in about]
        page = get_or_create_about_page(db)
        content = parse_content(page.content_json)
        content.statement = "Newcapability replaces the previous statement."
        page.content_json = serialize_content(content)
        create_publish_revision(db, page)
        db.commit()
        assert hydrate_descriptors(db, descriptors) == []
        pending = hydrate_evidence(db, runtime, "Zebracapability", limit=8, max_chars=10000)
        assert all(item.source_type != "about" for item in pending.evidence)
        other = hydrate_evidence(db, runtime, "Gavin", limit=8, max_chars=10000)
        assert any(item.source_type == "profile" for item in other.evidence)
    for _ in range(10):
        if not process_once(runtime):
            break
    with _session(client) as db:
        updated = hydrate_evidence(db, runtime, "Newcapability", limit=8, max_chars=10000)
        assert any(item.source_type == "about" and item.source_version != old_version
                   for item in updated.evidence)
