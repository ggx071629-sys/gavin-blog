from __future__ import annotations

import sqlite3
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, select, text

from app.assistant_index.fts import delete_fts_ids, delete_generation_fts, upsert_chunk_fts
from app.assistant_index.integrity import (
    IndexIntegrityError,
    audit_generation,
    require_active_integrity,
)
from app.assistant_index.maintenance import repair_active_fts
from app.assistant_index.qdrant_store import point_uuid
from app.assistant_index.worker import rebuild_generation
from app.models import AssistantChunk, AssistantIndexCommand, AssistantIndexGeneration

from .conftest import login, publish_article
from .test_assistant_index import _activate_ready_generation, _runtime, _session


def indexed(client):
    headers = {"X-CSRF-Token": login(client)}
    article = client.post('/api/v1/admin/articles', headers=headers, json={
        'title': 'nginx sentinel', 'slug': 'nginx-integrity',
        'content': '# nginx\n\nnginx configuration sentinel',
    }).json()
    assert publish_article(client, article, headers).status_code == 200
    runtime = _runtime(client)
    active = _activate_ready_generation(client, runtime)
    return runtime, active


def fts_rows(db, generation):
    return db.execute(text(
        'SELECT chunk_id, title, heading_path, body FROM assistant_chunk_fts '
        'WHERE generation_id=:g ORDER BY chunk_id'
    ), {'g': generation}).all()


def test_staging_same_ids_preserve_active_fts_and_generation_cleanup(client):
    runtime, active = indexed(client)
    with _session(client) as db:
        before = fts_rows(db, active)
    staging = rebuild_generation(runtime)
    with _session(client) as db:
        assert fts_rows(db, active) == before
        assert db.execute(text(
            "SELECT count(*) FROM assistant_chunk_fts WHERE generation_id=:g "
            "AND assistant_chunk_fts MATCH 'nginx'"
        ), {'g': active}).scalar_one() > 0
        second = fts_rows(db, staging)
        for chunk in db.scalars(select(AssistantChunk).where(
            AssistantChunk.generation_id == active
        )):
            upsert_chunk_fts(db, chunk)
        assert fts_rows(db, staging) == second
        delete_fts_ids(db, [row[0] for row in second], generation_id=staging)
        assert fts_rows(db, active) == before
        delete_generation_fts(db, staging)
        assert fts_rows(db, active) == before
    runtime.store.client.close()


def test_audit_derives_missing_whole_source_even_when_three_indexes_agree(client):
    runtime, active = indexed(client)
    with _session(client) as db:
        generation = db.get(AssistantIndexGeneration, active)
        assert audit_generation(db, runtime, generation).passed
        ids = list(db.scalars(select(AssistantChunk.chunk_id).where(
            AssistantChunk.generation_id == active, AssistantChunk.source_type == 'article'
        )))
        db.execute(delete(AssistantChunk).where(
            AssistantChunk.generation_id == active, AssistantChunk.source_type == 'article'
        ))
        db.execute(text('DELETE FROM assistant_chunk_fts WHERE generation_id=:g AND title=:t'),
                   {'g': active, 't': 'nginx sentinel'})
        runtime.store.delete_chunks(generation.collection_name, generation_id=active, chunk_ids=ids)
        report = audit_generation(db, runtime, generation)
        assert report.canonical_chunks == report.fts_rows == report.vector_points
        assert report.expected_chunks > report.canonical_chunks
        assert {i['layer'] for i in report.issues} == {'canonical'}
    runtime.store.client.close()


def test_audit_accepts_the_original_text_projection_of_an_existing_generation(client):
    headers = {'X-CSRF-Token': login(client)}
    article = client.post('/api/v1/admin/articles', headers=headers, json={
        'title': '中文标题', 'slug': 'lexical-audit',
        'content': '# 中文\n\n系统支持全文检索和向量检索。',
    }).json()
    assert publish_article(client, article, headers).status_code == 200
    runtime = _runtime(client)
    active = _activate_ready_generation(client, runtime)
    with _session(client) as db:
        generation = db.get(AssistantIndexGeneration, active)
        assert audit_generation(db, runtime, generation).fts_lexical_rows > 0
        for chunk in db.scalars(select(AssistantChunk).where(
            AssistantChunk.generation_id == active
        )):
            db.execute(
                text(
                    'UPDATE assistant_chunk_fts SET title=:t, heading_path=:h, body=:b '
                    'WHERE generation_id=:g AND chunk_id=:c'
                ),
                {
                    't': chunk.title, 'h': chunk.heading_path, 'b': chunk.page_content,
                    'g': active, 'c': chunk.chunk_id,
                },
            )
        legacy = audit_generation(db, runtime, generation)
        assert legacy.passed
        assert legacy.fts_lexical_rows == 0
    runtime.store.client.close()


@pytest.mark.parametrize('defect', [
    'canonical_body', 'canonical_version', 'fts_body', 'fts_duplicate', 'fts_extra',
    'fts_unavailable', 'vector_payload', 'vector_id', 'vector_dimension',
    'vector_nan', 'vector_unavailable',
])
def test_audit_detects_corruption_beyond_counts(client, monkeypatch, defect):
    runtime, active = indexed(client)
    with _session(client) as db:
        generation = db.get(AssistantIndexGeneration, active)
        chunk = db.scalar(select(AssistantChunk).where(AssistantChunk.generation_id == active))
        if defect == 'canonical_body':
            chunk.page_content = 'wrong body'
        elif defect == 'canonical_version':
            chunk.source_version = 'wrong-version'
        elif defect == 'fts_body':
            db.execute(text('UPDATE assistant_chunk_fts SET body=:b WHERE generation_id=:g'),
                       {'b': 'wrong body', 'g': active})
        elif defect == 'fts_duplicate':
            db.execute(text('INSERT INTO assistant_chunk_fts SELECT * FROM assistant_chunk_fts '
                            'WHERE generation_id=:g'), {'g': active})
        elif defect == 'fts_extra':
            db.execute(text('UPDATE assistant_chunk_fts SET chunk_id=:id WHERE generation_id=:g'),
                       {'id': 'wrong-id', 'g': active})
        elif defect == 'fts_unavailable':
            db.execute(text('DROP TABLE assistant_chunk_fts'))
        else:
            original = runtime.store.client.scroll

            def corrupted(*args, **kwargs):
                if defect == 'vector_unavailable':
                    raise OSError('provider unavailable')
                records, offset = original(*args, **kwargs)
                record = records[0]
                if defect == 'vector_payload':
                    record.payload = {**record.payload, 'generation': active + 100}
                if defect == 'vector_id':
                    record.id = point_uuid(active + 100, record.payload['chunk_id'])
                if defect == 'vector_dimension':
                    record.vector = [1.0]
                if defect == 'vector_nan':
                    record.vector[0] = float('nan')
                return records, offset
            monkeypatch.setattr(runtime.store.client, 'scroll', corrupted)
        db.flush()
        report = audit_generation(db, runtime, generation)
        assert not report.passed
        assert any(i['layer'] == defect.split('_')[0] for i in report.issues)
        with pytest.raises(IndexIntegrityError):
            report.require_passed()
    runtime.store.client.close()


def test_fts_repair_is_backed_up_generation_scoped_and_idempotent(client, tmp_path, monkeypatch):
    runtime, active = indexed(client)
    staging = rebuild_generation(runtime)
    with _session(client) as db:
        untouched = fts_rows(db, staging)
        db.execute(text('DELETE FROM assistant_chunk_fts WHERE generation_id=:g'), {'g': active})
        db.commit()
    def forbidden(*args, **kwargs):
        raise AssertionError('repair must not embed or write vectors')
    monkeypatch.setattr(runtime.embeddings, 'embed_documents', forbidden)
    monkeypatch.setattr(runtime.embeddings, 'embed_query', forbidden)
    monkeypatch.setattr(runtime.store.client, 'upsert', forbidden)
    result = repair_active_fts(runtime, generation_id=active, backup=tmp_path/'before.db')
    assert result['before']['fts_rows'] == 0
    assert result['after']['status'] == 'passed'
    assert result['changed_chunk_ids']
    with sqlite3.connect(tmp_path/'before.db') as backup:
        assert backup.execute('SELECT count(*) FROM assistant_chunk_fts WHERE generation_id=?',
                              (active,)).fetchone() == (0,)
    with _session(client) as db:
        assert fts_rows(db, staging) == untouched
        assert db.execute(text("SELECT count(*) FROM assistant_chunk_fts "
                               "WHERE generation_id=:g AND assistant_chunk_fts MATCH 'nginx'"),
                          {'g': active}).scalar_one() > 0
    second = repair_active_fts(runtime, generation_id=active, backup=tmp_path/'second.db')
    assert second['changed_chunk_ids'] == []
    assert require_active_integrity(runtime).passed
    runtime.store.client.close()


@pytest.mark.parametrize('defect', ['canonical', 'backup', 'postcheck', 'generation', 'fence'])
def test_unsafe_repair_refuses_or_rolls_back(client, tmp_path, monkeypatch, defect):
    from app.assistant_index import maintenance
    from app.content_write_fence import content_write_fence

    runtime, active = indexed(client)
    with _session(client) as db:
        db.execute(text('DELETE FROM assistant_chunk_fts WHERE generation_id=:g'), {'g': active})
        if defect == 'canonical':
            db.execute(delete(AssistantChunk).where(AssistantChunk.generation_id == active))
        db.commit()
    backup = tmp_path/'repair.db'
    if defect == 'backup':
        backup.write_text('existing backup must survive')
    if defect == 'postcheck':
        original = maintenance.audit_generation
        calls = 0
        def fail_after_write(*args):
            nonlocal calls
            report = original(*args)
            calls += 1
            if calls == 2:
                report.defect('fts', 'injected_failure')
            return report
        monkeypatch.setattr(maintenance, 'audit_generation', fail_after_write)
    lock = content_write_fence(runtime.settings) if defect == 'fence' else None
    if lock:
        lock.acquire()
    try:
        with pytest.raises((RuntimeError, FileExistsError)):
            repair_active_fts(runtime, generation_id=active + (defect == 'generation'),
                              backup=backup)
    finally:
        if lock:
            lock.release()
    with _session(client) as db:
        assert fts_rows(db, active) == []
    if defect == 'backup':
        assert backup.read_text() == 'existing backup must survive'
    if defect == 'fence':
        assert not backup.exists()
    runtime.store.client.close()


def test_startup_and_finalize_checks_reject_missing_fts_without_switching(client):
    from app.assistant.admin_operations import _switch_content
    from app.http_errors import ApiException

    runtime, active = indexed(client)
    staging = rebuild_generation(runtime)
    with _session(client) as db:
        db.execute(text('DELETE FROM assistant_chunk_fts WHERE generation_id IN (:a,:s)'),
                   {'a': active, 's': staging})
        db.commit()
        operation = db.scalar(select(AssistantIndexCommand).where(
            AssistantIndexCommand.generation_id == staging
        ))
        operation_id, version = operation.id, operation.version
    with pytest.raises(IndexIntegrityError):
        require_active_integrity(runtime)
    with pytest.raises(ApiException) as error:
        _switch_content(runtime.database, settings=runtime.settings, index_runtime=runtime,
                        operation_id=operation_id, expected_version=version,
                        idempotency_hash='test', token='test')
    assert error.value.code == 'index_integrity_failed'
    with _session(client) as db:
        assert db.get(AssistantIndexGeneration, active).status == 'active'
        assert db.get(AssistantIndexGeneration, staging).status == 'staging'
    runtime.store.client.close()


def test_rebuild_cannot_become_ready_with_missing_fts(client, monkeypatch):
    from app.assistant_index import worker

    runtime, active = indexed(client)
    monkeypatch.setattr(worker, 'upsert_chunk_fts', lambda *_: None)
    with pytest.raises(IndexIntegrityError):
        rebuild_generation(runtime)
    with _session(client) as db:
        commands = list(db.scalars(select(AssistantIndexCommand).where(
            AssistantIndexCommand.generation_id != active
        )))
        assert commands and all(c.status != 'ready_to_switch' for c in commands)
    runtime.store.client.close()


def test_real_lifespan_does_not_enable_gate_when_integrity_fails(client, monkeypatch):
    import asyncio
    from contextlib import asynccontextmanager
    from pathlib import Path

    from app.assistant import development
    from app.assistant_qualification import provider_probe
    from app.local_embedding import client as e5

    runtime, active = indexed(client)
    with _session(client) as db:
        db.execute(text('DELETE FROM assistant_chunk_fts WHERE generation_id=:g'), {'g': active})
        db.commit()
    states = []
    monkeypatch.setattr(development, 'validate_real_development_settings', lambda *_: None)
    monkeypatch.setattr(provider_probe, 'validate_local_chat_probe_artifact', lambda *_: None)
    monkeypatch.setattr(e5, 'E5Embeddings', type(runtime.embeddings))
    monkeypatch.setattr(development, 'update_availability',
                        lambda *args, enabled, **kwargs: states.append(enabled))
    @asynccontextmanager
    async def original(app):
        yield
    online = SimpleNamespace(index_runtime=runtime, embeddings=runtime.embeddings,
                             active_generation=lambda: SimpleNamespace(id=active))
    app = SimpleNamespace(router=SimpleNamespace(lifespan_context=original),
                          state=SimpleNamespace(assistant=online))
    development.attach_real_development_lifespan(app, runtime.settings, Path('unused-probe'))
    async def start():
        async with app.router.lifespan_context(app):
            pytest.fail('startup must reject corrupt indexes')
    with pytest.raises(IndexIntegrityError):
        asyncio.run(start())
    assert states and True not in states
    runtime.store.client.close()


@pytest.mark.parametrize('entry', ['local', 'capacity'])
def test_local_finalize_consumers_preserve_runtime_and_fence(client, tmp_path, monkeypatch, entry):
    from fastapi.testclient import TestClient

    from app.assistant_index import runtime as runtime_module
    from app.local_embedding import client as e5
    from app.local_embedding.capacity_roles import create_capacity_api
    from app.local_embedding.local import finalize_local

    runtime, active = indexed(client)
    staging = rebuild_generation(runtime)
    settings = runtime.settings.model_copy(update={
        'environment': 'development',
        'assistant_runtime_path': str(tmp_path/'local-runtime.db'),
    })
    runtime.settings = settings
    if entry == 'local':
        finalize_local(settings, runtime.database, staging, runtime)
    else:
        monkeypatch.setattr(runtime_module, 'build_runtime', lambda *_: runtime)
        monkeypatch.setattr(e5, 'E5Embeddings', type(runtime.embeddings))
        token = 'synthetic-capacity-auth-token-000000'
        app = create_capacity_api(settings, token)
        with TestClient(app) as web:
            response = web.post(f'/__capacity/finalize/{staging}',
                                headers={'Authorization': 'Bearer '+token})
            assert response.status_code == 200, response.text
    with _session(client) as db:
        assert db.get(AssistantIndexGeneration, active).status == 'previous'
        assert db.get(AssistantIndexGeneration, staging).status == 'active'
    assert require_active_integrity(runtime).passed
    runtime.store.client.close()
