from decimal import Decimal

from sqlalchemy import select

from app.assistant_index.worker import _chunk_payload, process_once
from app.models import AssistantChunk, AssistantIndexEmbeddingAttempt, AssistantIndexTask

from .conftest import login, publish_article
from .test_assistant_index import _activate_ready_generation, _runtime, _session


def setup_source(client):
    headers = {'X-CSRF-Token': login(client)}
    article = publish_article(client, client.post('/api/v1/admin/articles', headers=headers,
        json={'title': 'Reusable', 'slug': 'reusable', 'content': 'Exact stable body.'},
    ).json(), headers).json()
    runtime = _runtime(client)
    runtime.settings = runtime.settings.model_copy(update={
        'assistant_index_embedding_daily_budget_cny': Decimal('1'),
        'assistant_embedding_input_price_cny_per_million': Decimal('0.1'),
    })
    _activate_ready_generation(client, runtime)
    return headers, article, runtime


def republish(client, headers, article, content='Exact stable body.'):
    updated = client.patch(f"/api/v1/admin/articles/{article['id']}", headers=headers,
        json={'version': article['version'], 'content': content})
    assert updated.status_code == 200
    response = publish_article(client, updated.json(), headers)
    assert response.status_code == 200
    return response.json()


def test_same_text_new_revision_reuses_vectors_without_provider_call(client, monkeypatch):
    headers, article, runtime = setup_source(client)
    newer = republish(client, headers, article)
    assert newer['current_revision_id'] != article['current_revision_id']
    def no_call(*args):
        raise AssertionError('unchanged text must not call provider')
    monkeypatch.setattr(runtime.embeddings, 'embed_documents_metered', no_call)
    assert process_once(runtime)
    with _session(client) as db:
        task = db.scalars(select(AssistantIndexTask).order_by(AssistantIndexTask.id.desc())).first()
        assert task.status == 'succeeded'
        rows = list(db.scalars(select(AssistantChunk).where(
            AssistantChunk.source_type == 'article')))
        assert rows and all(c.source_version == str(newer['current_revision_id']) for c in rows)
        vectors = runtime.store.reusable_vectors(rows[0].generation.collection_name,
            generation_id=rows[0].generation_id, payloads=[_chunk_payload(c, c.generation_id)
            for c in rows], dimension=32)
        assert vectors is not None


def test_changed_text_requires_new_embedding(client, monkeypatch):
    headers, article, runtime = setup_source(client)
    republish(client, headers, article, 'Changed technical content.')
    calls = []
    original = runtime.embeddings.embed_documents_metered
    def counted(texts):
        calls.append(texts)
        return original(texts)
    monkeypatch.setattr(runtime.embeddings, 'embed_documents_metered', counted)
    process_once(runtime)
    assert len(calls) == 1 and 'Changed technical content.' in '\n'.join(calls[0])


def test_unavailable_success_and_unknown_stop_without_retry(client):
    headers, article, runtime = setup_source(client)
    with _session(client) as db:
        rows = list(db.scalars(select(AssistantChunk).where(
            AssistantChunk.source_type == 'article')))
        runtime.store.delete_chunks(rows[0].generation.collection_name,
            generation_id=rows[0].generation_id, chunk_ids=[c.chunk_id for c in rows])
    newer = republish(client, headers, article)
    process_once(runtime)
    with _session(client) as db:
        task = db.scalars(select(AssistantIndexTask).order_by(AssistantIndexTask.id.desc())).first()
        assert (task.status, task.attempt_count, task.safe_error_code, task.provider_state) == (
            'failed', 1, 'index_vectors_unavailable', 'succeeded')
        from app.assistant.admin_operations import task_view
        assert '已停止自动重试' in task_view(task).message
        # Select the article attempt by its original input, not the profile attempt.
        import hashlib
        fingerprint = hashlib.sha256('\n'.join(c.page_content for c in rows).encode()).hexdigest()
        attempt = db.scalar(select(AssistantIndexEmbeddingAttempt).where(
            AssistantIndexEmbeddingAttempt.generation_id == rows[0].generation_id,
            AssistantIndexEmbeddingAttempt.request_fingerprint == fingerprint,
        ))
        assert attempt is not None
        attempt.status = 'unknown'
        db.commit()
    assert not process_once(runtime)
    republish(client, headers, newer)
    process_once(runtime)
    with _session(client) as db:
        task = db.scalars(select(AssistantIndexTask).order_by(AssistantIndexTask.id.desc())).first()
        assert (task.status, task.attempt_count, task.safe_error_code, task.provider_state) == (
            'failed', 1, 'provider_result_unknown', 'unknown')


def test_model_identity_mismatch_does_not_reuse(client, monkeypatch):
    headers, article, runtime = setup_source(client)
    republish(client, headers, article)
    runtime.settings = runtime.settings.model_copy(update={
        'assistant_embedding_model_version': 'other-version',
    })
    def no_reuse(*args, **kwargs):
        raise AssertionError('different model must not reuse vectors')
    monkeypatch.setattr(runtime.store, 'reusable_vectors', no_reuse)
    process_once(runtime)
    with _session(client) as db:
        task = db.scalars(select(AssistantIndexTask).order_by(AssistantIndexTask.id.desc())).first()
        assert task.safe_error_code == 'index_vectors_unavailable'


def test_transient_store_error_still_retries(client, monkeypatch):
    headers, article, runtime = setup_source(client)
    republish(client, headers, article)
    def temporary(*args, **kwargs):
        raise ConnectionError('temporary vector store failure')
    monkeypatch.setattr(runtime.store, 'reusable_vectors', temporary)
    process_once(runtime)
    with _session(client) as db:
        task = db.scalars(select(AssistantIndexTask).order_by(AssistantIndexTask.id.desc())).first()
        assert (task.status, task.attempt_count) == ('pending', 1)


def test_reuse_rejects_mismatched_payload_and_dimension(client, monkeypatch):
    _, _, runtime = setup_source(client)
    with _session(client) as db:
        row = db.scalars(select(AssistantChunk)).first()
        payload = _chunk_payload(row, row.generation_id)
        kwargs = dict(generation_id=row.generation_id, payloads=[payload], dimension=32)
        assert runtime.store.reusable_vectors(row.generation.collection_name, **kwargs)
        assert runtime.store.reusable_vectors(row.generation.collection_name,
            **dict(kwargs, dimension=16)) is None
        assert runtime.store.reusable_vectors(row.generation.collection_name,
            **dict(kwargs, payloads=[dict(payload, source_version='different')])) is None
        original = runtime.store.client.retrieve
        def nonfinite(**options):
            records = original(**options)
            records[0].vector[0] = float('nan')
            return records
        monkeypatch.setattr(runtime.store.client, 'retrieve', nonfinite)
        assert runtime.store.reusable_vectors(row.generation.collection_name, **kwargs) is None
