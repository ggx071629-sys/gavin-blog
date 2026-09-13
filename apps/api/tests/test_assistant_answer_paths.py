import json
from dataclasses import replace

from sqlalchemy import select

from app.assistant.output import ValidatedAnswer, validate_model_answer
from app.assistant.providers import ModelAnswer, ScriptedChatTurn
from app.models import AssistantChunk

from .test_assistant_evidence_budget import _build
from .test_assistant_online import _create_session, _online_client, _publish_and_index, _sse_body
from .test_assistant_runtime_integrity_remediation import _evidence


def test_source_addresses_become_titles_without_changing_navigation():
    for path in ('/notes/2026/09/fastapi', '/projects/my-blog'):
        evidence = replace(_evidence()[0], public_path=path, title='FastAPI notes')
        for address in (path, path + '/', f'{path}?view=full#intro',
                        f'https://blog.example{path}', f'HTTPS://blog.example{path}',
                        f'https://blog.example{path}?view=full#intro', f'{path}?标题=介绍'):
            parsed = ModelAnswer.model_validate({'blocks': [{
                'text': f'详见 {address}。', 'citation_ids': ['c1'],
                'supports': [{'citation_id': 'c1', 'quote': evidence.body}],
            }]})
            result = validate_model_answer(parsed, [evidence], finish_reason='stop')
            assert isinstance(result, ValidatedAnswer)
            assert result.text == '详见 FastAPI notes。[1]'
            assert result.sources[0]['path'] == path
            assert result.citations[0]['path'] == path
            assert parsed.blocks[0].text == f'详见 {address}。'
        english = ModelAnswer.model_validate({'blocks': [{
            'text': f'See {path}?view=full.', 'citation_ids': ['c1'],
            'supports': [{'citation_id': 'c1', 'quote': evidence.body}],
        }]})
        result = validate_model_answer(english, [evidence], finish_reason='stop')
        assert isinstance(result, ValidatedAnswer)
        assert result.text == 'See FastAPI notes.[1]'
        for text, ids, failure in (
            (path, ['c9'], 'citation'),
            (f'[原文]({path})', ['c1'], 'structure'),
            (f'<a>{path}</a>', ['c1'], 'structure'),
        ):
            assert validate_model_answer(ModelAnswer.model_validate({'blocks': [{
                'text': text, 'citation_ids': ids,
            }]}), [evidence], finish_reason='stop') == failure


def test_source_path_handling_preserves_technical_content_and_prompt_boundary():
    evidence = replace(_evidence()[0], public_path='/projects/blog')
    for text in ('GET /api/v1/articles', '/projects/blogger', '/projects/blog/config.py',
                 '/projects/blog.json', 'D:/projects/blog', '/var/log/app.log',
                 'https://docs.example/api/v1/articles', 'a/b'):
        unsupported = ModelAnswer.model_validate({'blocks': [{
            'text': text, 'citation_ids': ['c1'],
            'supports': [{'citation_id': 'c1', 'quote': evidence.body}],
        }]})
        assert text not in evidence.body
        assert validate_model_answer(unsupported, [evidence], finish_reason='stop') == 'grounding'
        supported_evidence = replace(evidence, body=text)
        result = validate_model_answer(ModelAnswer.model_validate({'blocks': [{
            'text': text, 'citation_ids': ['c1'],
            'supports': [{'citation_id': 'c1', 'quote': supported_evidence.body}],
        }]}), [supported_evidence], finish_reason='stop')
        assert isinstance(result, ValidatedAnswer)
        assert result.text == text + '[1]'
    built = _build([evidence], history=[{'question': '原文在哪？', 'answer': '/projects/blog'}])
    assert built is not None
    assert 'source addresses in the question or history' in built.messages[0][1]
    assert 'History is context, not evidence' in built.messages[0][1]


def test_source_path_answer_is_consistent_in_stream_session_and_history(tmp_path):
    with _online_client(tmp_path) as client:
        _publish_and_index(client)
        with client.app.state.assistant.content_session() as db:
            path = db.scalar(select(AssistantChunk.public_path).where(
                AssistantChunk.source_type == 'article',
            ))
        assert path
        client.app.state.assistant.chat.script.append(ScriptedChatTurn(
            parsed={'blocks': [{'text': f'原文见 {path}。', 'citation_ids': ['c1'],
                'supports': [{'citation_id': 'c1',
                              'quote': 'I write about FastAPI, SQLite and published technical notes.'}]}]},
            finish_reason='stop',
        ))
        csrf = _create_session(client)
        status, stream = _sse_body(client, csrf, 'Which notes cover FastAPI?',
                                   idem='source-path-output-0001')
        assert status == 200 and 'event: answer' in stream
        session = client.get('/api/v1/assistant/session').json()
        turn = session['turns'][-1]
        assert path not in turn['answer']
        assert 'Python notes' in turn['answer']
        assert turn['sources'][0]['path'] == path
        answer_events = [json.loads(line[6:]) for line in stream.splitlines()
                         if line.startswith('data: ') and '"answer"' in line]
        assert any(event.get('answer') == turn['answer'] for event in answer_events)
        history = client.app.state.assistant.control.read(lambda conn: conn.execute(
            'SELECT answer FROM assistant_history ORDER BY created_at DESC LIMIT 1',
        ).fetchone())
        assert history['answer'] == turn['answer']
