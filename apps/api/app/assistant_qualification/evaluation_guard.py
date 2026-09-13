"""Explicit local-development-only cumulative accounting for actual page calls."""
from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from langchain_core.runnables import RunnableLambda

from ..assistant.prompt import estimate_tokens
from . import local_ledger
from . import provider_probe as probe


def ledger_for_probe(probe_path: Path, default_path: Path, explicit: str | None = None):
    if explicit:
        return Path(explicit)
    # The caller validates the signed probe first. A Q5 probe must not silently
    # lose cumulative accounting when started through the ordinary launcher.
    identity = json.loads(probe_path.read_text(encoding='utf8')).get('authorization_id', '')
    return default_path if identity.startswith('assistant-gap-closure-q5-') else None


class EvaluationGuard:
    def __init__(self, settings, ledger: Path, before_dispatch=None):
        self.settings, self.ledger = settings, ledger
        self.before_dispatch = before_dispatch
        status = local_ledger.status(settings=settings, ledger_path=ledger)
        self.contract = probe._local_chat_contract(
            settings=settings, approved_max_micro_cny=4_000_000, max_calls=250,
            approved_daily_budget=Decimal('2'),
            authorization_id='assistant-gap-closure-q5-250-4-20260913',
        )
        if status['authorization_id'] != self.contract.authorization_id or status['unresolved']:
            raise ValueError('evaluation ledger unavailable')

    def invoke(self, bound, chat, messages):
        contract, settings, ledger = self.contract, self.settings, self.ledger
        estimate = estimate_tokens(messages, chat)
        if estimate > contract.max_input_tokens:
            raise ValueError('evaluation input budget exceeded')
        reserve = probe._micro_cost(estimate, contract.input_price_micro_cny_per_million)
        reserve += probe._micro_cost(
            contract.max_output_tokens, contract.output_price_micro_cny_per_million,
        )
        with local_ledger.run_lock(ledger):
            if self.before_dispatch:
                self.before_dispatch()
            attempt = probe._reserve(ledger, contract, kind='chat', settings=settings,
                                     reserved_micro_cny=reserve, now=datetime.now(UTC))
            started = time.monotonic()
            try:
                result = bound.invoke(messages)
                from ..assistant.graph import _usage_from_raw
                finish, usage = _usage_from_raw(result.get('raw'))
                ins, outs = usage.get('input_tokens'), usage.get('output_tokens')
                known = type(ins) is int and type(outs) is int and ins >= 0 and outs >= 0
                cost = (probe._micro_cost(ins, contract.input_price_micro_cny_per_million)
                        + probe._micro_cost(outs, contract.output_price_micro_cny_per_million)
                        if known else reserve)
                valid = (known and usage.get('model') == contract.model and ins <= estimate
                         and outs <= contract.max_output_tokens and cost <= reserve
                         and finish in {'stop', 'length'})
            except BaseException:
                probe._settle(ledger, contract, attempt_id=attempt, status='unknown',
                              settled_micro_cny=reserve, settings=settings, now=datetime.now(UTC))
                raise
            probe._settle(ledger, contract, attempt_id=attempt,
                          status='succeeded' if valid else 'measured_fail',
                          settled_micro_cny=cost, settings=settings, now=datetime.now(UTC))
            # Local private raw evidence only; no credentials or messages are saved.
            record = dict(attempt_id=attempt, usage=usage, finish_reason=finish,
                          elapsed_seconds=time.monotonic() - started, cost_micro_cny=cost,
                          raw_output=getattr(result.get('raw'), 'content', ''), valid=valid)
            (ledger.parent / ('q5-page-' + attempt + '.json')).write_text(
                json.dumps(record, ensure_ascii=False, indent=2), encoding='utf8',
            )
            if not valid:
                raise RuntimeError('evaluation provider identity or usage mismatch')
            return result

    def wrap(self, bound, chat):
        async def call(messages):
            # Cancellation never releases the signed reservation of a running request.
            # The worker retains its lock and settles even if the page disconnects.
            return await asyncio.to_thread(self.invoke, bound, chat, messages)

        return RunnableLambda(lambda messages: self.invoke(bound, chat, messages), afunc=call)
