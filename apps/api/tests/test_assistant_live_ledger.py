import asyncio
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from app.assistant_qualification import evaluation_guard as module


def test_live_ledger_reserves_every_call_and_blocks_unknown(monkeypatch, tmp_path):
    from contextlib import nullcontext
    guard = object.__new__(module.EvaluationGuard)
    guard.settings = None
    guard.ledger = tmp_path / 'ledger.json'
    guard.before_dispatch = None
    guard.contract = SimpleNamespace(max_input_tokens=32000, max_output_tokens=512,
        input_price_micro_cny_per_million=3_000_000,
        output_price_micro_cny_per_million=9_000_000, model='deepseek-flash')
    events = []
    monkeypatch.setattr(module, 'estimate_tokens', lambda *a: 1000)
    monkeypatch.setattr(module.local_ledger, 'run_lock', lambda *a: nullcontext())
    def reserve(*a, **k):
        if 'unknown' in events:
            raise ValueError('unresolved')
        events.append('reserve')
        return str(len(events))
    monkeypatch.setattr(module.probe, '_reserve', reserve)
    monkeypatch.setattr(module.probe, '_settle', lambda *a, **k: events.append(k['status']))
    def invoke(messages):
        assert events[-1] == 'reserve'
        events.append('send')
        return dict(raw=AIMessage(content='{"blocks":[]}',
            usage_metadata=dict(input_tokens=100, output_tokens=10, total_tokens=110),
            response_metadata=dict(model_name='deepseek-flash', finish_reason='stop')))
    bound = SimpleNamespace(invoke=invoke)
    for _ in range(2):
        asyncio.run(guard.wrap(bound, object()).ainvoke([]))
    assert events == ['reserve', 'send', 'succeeded'] * 2
    def fail(messages):
        events.append('send')
        raise TimeoutError()
    bound.invoke = fail
    with pytest.raises(TimeoutError):
        guard.invoke(bound, object(), [])
    assert events[-1] == 'unknown'
    with pytest.raises(ValueError, match='unresolved'):
        guard.invoke(bound, object(), [])
    assert events.count('send') == 3
    guard.before_dispatch = lambda: (_ for _ in ()).throw(ValueError('corpus changed'))
    with pytest.raises(ValueError, match='corpus changed'):
        guard.invoke(bound, object(), [])
    assert events.count('send') == 3


def test_local_alias_probe_retains_unknown_version(monkeypatch, tmp_path):
    from app.assistant_qualification.provider_probe import run_local_chat_probe

    from .test_assistant_provider_qualification import _local_probe_inputs
    args, requests = _local_probe_inputs(
        tmp_path, monkeypatch, assistant_chat_model='deepseek-flash',
    )
    args['settings'] = args['settings'].model_copy(update={'assistant_chat_model':'deepseek-flash'})
    from app.assistant_qualification import provider_probe
    original_usage = provider_probe._usage_from_raw

    def alias_usage(raw):
        finish, usage = original_usage(raw)
        return finish, {**usage, 'model': 'deepseek-flash'}

    monkeypatch.setattr(provider_probe, '_usage_from_raw', alias_usage)
    result = run_local_chat_probe(**args)
    assert result['chat']['status'] == 'pass'
    assert result['chat']['response_version_match'] is False
    assert result['production_qualified'] is False
    assert len(requests) == 1
    import json
    probe_path = tmp_path / 'probe.json'
    ledger = tmp_path / 'ledger.json'
    probe_path.write_text(json.dumps(dict(
        authorization_id='assistant-gap-closure-q5-250-4-20260913',
    )), encoding='utf8')
    assert module.ledger_for_probe(probe_path, ledger) == ledger
    probe_path.write_text('{}', encoding='utf8')
    assert module.ledger_for_probe(probe_path, ledger) is None


def test_page_cancellation_does_not_release_inflight_accounting(monkeypatch):
    from threading import Event

    guard = object.__new__(module.EvaluationGuard)
    started, release, settled = Event(), Event(), Event()

    def inflight(*args):
        started.set()
        assert release.wait(5)
        settled.set()

    monkeypatch.setattr(guard, 'invoke', inflight)

    async def scenario():
        task = asyncio.create_task(guard.wrap(None, None).ainvoke([]))
        assert await asyncio.to_thread(started.wait, 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not settled.is_set()
        release.set()
        assert await asyncio.to_thread(settled.wait, 5)

    asyncio.run(scenario())
