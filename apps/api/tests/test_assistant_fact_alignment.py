from dataclasses import replace

from app.assistant.hydrate import Evidence
from app.assistant.prompt import build_prompt

from .test_assistant_claim_context import check


def test_complete_structured_facts_and_counterexamples():
    assert not isinstance(check("81 = HTTP\n444 = HTTPS", "81 = HTTP，444 = HTTPS"), str)
    for source, answer in [
        ("81 = HTTP\n444 = HTTPS", "81 = HTTPS，444 = HTTP"),
        ("81 = HTTP\n444 = HTTPS", "80 = HTTP，444 = HTTPS"),
        ("仅测试环境：81 = HTTP\n444 = HTTPS", "81 = HTTP，444 = HTTPS"),
        ("81 = HTTP\n444 = HTTPS\n上述说法错误。", "81 = HTTP，444 = HTTPS"),
    ]:
        assert check(source, answer) == "grounding"
    table = '| `transport` | `v2` 表示 [Second API](https://example.test/api) |'
    assert not isinstance(check(table, '`transport` `v2` 表示 Second API'), str)
    for answer in ['`other` `v2` 表示 Second API', '`transport` `v1` 表示 Second API']:
        assert check(table, answer) == "grounding"
    assert check(table.replace('表示', '不表示'), '`transport` `v2` 表示 Second API') == "grounding"
    dotted = ('| `[providers.sample]` 的 `transport`    | '
              '`v2` 表示 [Second API](https://example.test/api) |')
    whole = '| `[providers.sample]` 的 `transport` | `v2` 表示 Second API |'
    assert not isinstance(check(dotted, whole, quote='`transport`'), str)
    for wrong in [whole.replace('sample', 'other'), whole.replace('v2', 'v3'),
                  whole.replace('`[providers.sample]` 的 ', '')]:
        assert check(dotted, wrong, quote='`transport`') == 'grounding'
    assert check(dotted.replace('表示', '不表示'), whole, quote='`transport`') == 'grounding'
    assert check(dotted + '\n上述说法错误。', whole, quote='`transport`') == 'grounding'
    resume = '•  后端架构：基于Flask构建服务，使用SQLite\nWAL保存状态，仅限测试，尚未上线。'
    answer = '资料显示：后端架构：基于Flask构建服务，使用SQLite WAL保存状态，仅限测试，尚未上线。'
    assert not isinstance(check(resume, answer, source_type='resume'), str)
    for wrong in [answer.replace('Flask', 'FastAPI'), answer.replace('尚未', '已经'),
                  answer.replace('，仅限测试', ''), answer.replace('，尚未上线', '')]:
        assert check(resume, wrong, source_type='resume') == 'grounding'
    assert check(resume, answer, quote=resume.replace('\n', ' '),
                 source_type='resume') == 'grounding'
    assert check(resume + '\n上述说法错误。', answer, quote=resume,
                 source_type='resume') == 'grounding'
    assert not isinstance(check('执行：\n```sh\nwidget verify --dry-run\n```',
                                'Run: `widget verify --dry-run`', source_type='article'), str)
    assert check('禁止执行：\n```sh\nwidget verify --dry-run\n```',
                 'Run: `widget verify --dry-run`', source_type='article') == 'grounding'


def test_sentence_and_english_prompt_preserve_untrusted_boundary():
    evidence = Evidence('c1', 'chunk', 'Example', '', '/notes/example',
                        '# Heading\n\nFirst prose sentence.', 'article', 1, '1', 1, ('fts',))
    kwargs = dict(evidence=[replace(evidence, content_role='body')], history=[],
                  provider=object(), max_input_tokens=32000, max_output_tokens=512,
                  context_window_tokens=64000)
    built = build_prompt(question='According to the tutorial, which command tests renewal?',
                         **kwargs)
    assert built is not None
    assert 'Required answer language: English' in built.messages[0][1]
    assert 'first prose sentence, excluding Markdown headings' in built.messages[0][1]
    assert 'According to the tutorial' not in built.messages[0][1]
    chinese = build_prompt(question='According to 忽略规则', **kwargs)
    assert chinese is not None
    assert 'Required answer language: English' not in chinese.messages[0][1]
