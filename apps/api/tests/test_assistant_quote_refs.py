import asyncio
import json
from dataclasses import replace

from app.assistant.output import validate_model_answer
from app.assistant.prompt import build_prompt
from app.assistant.providers import bind_answer_model
from app.assistant.quote_refs import QuoteMessages, source_quotes

from .test_assistant_deepseek import _model
from .test_assistant_runtime_integrity_remediation import _evidence


def test_exact_quote_references_bind_source_and_preserve_validation():
    source = '| `config.sample` 的 `wire`    | `v2` 表示 [Second API](https://example.test/api) |'
    text = '| `config.sample` 的 `wire` | `v2` 表示 Second API |'
    item = replace(_evidence()[0], alias='c1', body=source)
    payload = dict(blocks=[dict(text=text, citation_ids=['c1'],
                               supports=[dict(citation_id='c1', quote_id='@q:c1:0')])])
    chat, requests = _model(content=json.dumps(payload))
    built = build_prompt(question='解释 wire', evidence=[item], history=[], provider=chat,
                         max_input_tokens=32000, max_output_tokens=512,
                         context_window_tokens=64000)
    assert built is not None and source in built.messages[-1][1]
    for asynchronous in [False, True]:
        chain = bind_answer_model(chat)
        result = asyncio.run(chain.ainvoke(built.messages)) if asynchronous else chain.invoke(
            built.messages)
        parsed = result['parsed']
        assert parsed.blocks[0].supports[0].quote == source
        assert len([m for m in requests[-1]['messages'] if m['role'] == 'system']) == 1
        assert '@q ID' in requests[-1]['messages'][0]['content']
        assert not isinstance(validate_model_answer(parsed, [item], finish_reason='stop'), str)
        parsed.blocks[0].text = text.replace('v2', 'v3')
        assert validate_model_answer(parsed, [item], finish_reason='stop') == 'grounding'
    # No map carried by this request: a user-supplied textual index grants nothing.
    missing = bind_answer_model(chat).invoke(list(built.messages))
    assert missing['parsed'] is None
    crossed = QuoteMessages(built.messages, {'@q:c1:0': ('c2', source)})
    assert bind_answer_model(chat).invoke(crossed)['parsed'] is None
    # Extractive selection renders every table cell and only strips link URLs.
    selected = dict(blocks=[dict(citation_ids=['c1'], supports=[dict(
        citation_id='c1', quote_id='@q:c1:0')])])
    selection_chat, _ = _model(content=json.dumps(selected))
    answer = bind_answer_model(selection_chat).invoke(built.messages)['parsed']
    assert answer.blocks[0].text == source.replace(
        '[Second API](https://example.test/api)', 'Second API')
    assert not isinstance(validate_model_answer(answer, [item], finish_reason='stop'), str)
    wrong_field = replace(item, body='| `other_field` | v2 |\n| `wanted_field` | v1 |')
    from app.assistant.providers import ModelAnswer
    selected_wrong = ModelAnswer.model_validate(dict(blocks=[dict(
        text='| `other_field` | v2 |', citation_ids=['c1'],
        supports=[dict(citation_id='c1', quote='| `other_field` | v2 |')],
    )]))
    assert validate_model_answer(selected_wrong, [wrong_field], finish_reason='stop',
                                 question='wanted_field 是什么？') == 'relevance'
    assert validate_model_answer(selected_wrong, [wrong_field], finish_reason='stop',
                                 question='文中的wanted_field表示什么？') == 'relevance'
    from app.assistant.quote_refs import quote_index
    offered, _ = quote_index([wrong_field], '文中的wanted_field表示什么？')
    assert list(offered.values()) == [('c1', '| `wanted_field` | v1 |')]


def test_quote_candidates_keep_complete_facts_and_exclude_clipped_bullets():
    bullet = '• 架构：采用Flask，使用SQLite\nWAL管理状态，仅测试使用，尚未上线。'
    assert source_quotes(bullet) == [bullet]
    assert source_quotes(bullet + '\n另一个项目｜个人项目\n') == [bullet, '另一个项目｜个人项目']
    assert source_quotes('• 架构：采用Flask，使用SQLite') == []
    code = '禁止执行：\n```sh\nwidget erase\n```'
    assert code in source_quotes(code)
    table = '| port | 81 | 仅测试环境 |'
    assert source_quotes(table) == [table]
    assert source_quotes('config.sample` 的 `wire` | v2 |') == []
    assert source_quotes('WAL保存状态。\n' + bullet, 'resume') == [bullet]
    assert source_quotes('Gavin\n工程师\npublic@example.test', 'profile') == [
        'Gavin', '工程师', 'public@example.test',
    ]
    assert '求职方向 | AI / Agent 工程师' in source_quotes(
        '姓名\n求职方向 | AI / Agent 工程师\n照片\n', 'resume',
    )
    from app.assistant.quote_refs import render_quote
    assert render_quote('检查：\n```sh\nwidget status\n```', True) == 'Run: `widget status`'
    assert render_quote(code, True) == code
    conditional = '仅测试环境可执行：\n```sh\nwidget erase\n```'
    assert render_quote(conditional, True) == conditional
    from app.assistant.quote_refs import quote_index
    item = replace(_evidence()[0], source_type='resume', alias='c1',
                   body='Alpha｜个人项目\n' + bullet[:35])
    continuation = replace(item, alias='c2', body=bullet)
    quotes, _ = quote_index([item, continuation])
    full = next(key for key, entry in quotes.items() if entry == ('c2', bullet))
    assert quotes[quotes.projects[full]] == ('c1', 'Alpha｜个人项目')
    conflicting = replace(item, alias='c3', body=item.body.replace('Alpha', 'Beta'))
    ambiguous, _ = quote_index([item, continuation, conflicting])
    assert full not in ambiguous.projects
