from sqlalchemy import select

from app.assistant_index import retriever
from app.config import Settings
from app.models import AssistantChunk

from .conftest import login, publish_article
from .test_assistant_evidence_budget import _build
from .test_assistant_index import _activate_ready_generation, _runtime, _session
from .test_assistant_runtime_integrity_remediation import _evidence


def test_retrieval_spreads_limit_across_live_sources(client, monkeypatch):
    headers = {"X-CSRF-Token": login(client)}
    articles = []
    for index in range(12):
        created = client.post('/api/v1/admin/articles', headers=headers, json={
            'title': f'Article {index}', 'slug': f'coverage-{index}',
            'content': '\n\n'.join(f'## Section {j}\nUnique content {index} {j}' for j in range(5)),
        })
        articles.append(publish_article(client, created.json(), headers).json())
    runtime = _runtime(client)
    _activate_ready_generation(client, runtime)
    with _session(client) as db:
        chunks = list(db.scalars(select(AssistantChunk).where(
            AssistantChunk.source_type == 'article',
        ).order_by(AssistantChunk.source_id, AssistantChunk.ordinal)))
        ranked = [c.chunk_id for c in chunks]
        assert len([c for c in chunks if c.source_id == articles[0]['id']]) >= 3
        monkeypatch.setattr(retriever, '_fts_search', lambda *args: ranked)
        result = retriever.retrieve(db, runtime, 'articles', limit=3, skip_dense=True)
        by_id = {c.chunk_id: c for c in chunks}
        assert [by_id[c.chunk_id].source_id for c in result.candidates] == [
            a['id'] for a in articles[:3]
        ]
        expanded = retriever.retrieve(db, runtime, 'articles', limit=4, skip_dense=True)
        assert by_id[expanded.candidates[-1].chunk_id].source_id == articles[3]['id']
        wide = retriever.retrieve(db, runtime, 'articles', skip_dense=True)
        assert len(wide.candidates) == 32
        assert {by_id[c.chunk_id].source_id for c in wide.candidates} == {
            a['id'] for a in articles
        }
        assert wide.candidates[12].chunk_id == ranked[1]
    deleted = client.delete(f"/api/v1/admin/articles/{articles[1]['id']}", headers=headers)
    assert deleted.status_code == 204
    with _session(client) as db:
        result = retriever.retrieve(db, runtime, 'articles', limit=3, skip_dense=True)
        assert all(by_id[c.chunk_id].source_id != articles[1]['id'] for c in result.candidates)
        assert [c.rank for c in result.candidates] == [1, 2, 3]


def test_candidate_pool_defaults_are_configurable_without_raising_model_budget():
    settings = Settings()
    assert settings.assistant_retrieve_limit == 32
    assert settings.assistant_evidence_max_chars == 24000
    expanded = Settings(assistant_retrieve_limit=64, assistant_evidence_max_chars=48000)
    assert expanded.assistant_retrieve_limit == 64
    assert expanded.assistant_evidence_max_chars == 48000
    assert expanded.assistant_chat_max_input_tokens == settings.assistant_chat_max_input_tokens


def test_prompt_uses_titles_without_source_paths():
    evidence = _evidence()
    built = _build(evidence)
    assert built is not None
    human = built.messages[1][1]
    assert evidence[0].title in human
    assert evidence[0].public_path not in human
    assert 'never print source URL paths' in built.messages[0][1]
    assert built.evidence[0].public_path == evidence[0].public_path
