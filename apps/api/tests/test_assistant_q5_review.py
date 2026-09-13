from .test_assistant_current_quality import (
    runner,
)
from .test_assistant_current_quality import (
    test_current_quality_budget_precedes_dispatch_and_unknown_stops as unknown_stops,
)
from .test_assistant_current_quality import (
    test_current_quality_default_prepare_never_dispatches_or_reserves as prepare_without_pay,
)


def test_holdout_is_frozen_and_unknown_does_not_prevent_readonly_prepare(monkeypatch, tmp_path):
    r = runner()
    cases = r.read_json(r.BASE / 'Q5-holdout.json')
    r.validate_dataset(r.read_json(r.BASE / 'Q5-corpus.json'), cases)
    old = r.read_json(r.BASE / 'Q5-cases.json')
    questions = {row['question'] for row in old['rows']}
    held = [row for row in cases['rows'] if row['split'] == 'evaluation']
    assert len(held) == 8 and all(row['question'] not in questions for row in held)
    assert 'no model output at freeze' in cases['freeze_policy']
    original_runner = __import__(prepare_without_pay.__module__, fromlist=['runner'])

    def with_unknown():
        module = runner()

        def refuse_envelope(*args, **kwargs):
            raise AssertionError('read-only prepare must not check paid admission')

        monkeypatch.setattr(module, 'check_envelope', refuse_envelope)
        return module

    monkeypatch.setattr(original_runner, 'runner', with_unknown)
    prepare_without_pay(monkeypatch, tmp_path)


def test_unknown_records_elapsed_and_preserves_stop(monkeypatch, tmp_path):
    # Existing counterexamples cover reservation-before-send, exhausted budgets
    # and unknown-result settlement without retry. Capture the measured duration.
    original_runner = __import__(unknown_stops.__module__, fromlist=['runner'])
    module = runner()
    paid = module.paid_call
    captured = []

    def measured(*args, **kwargs):
        result = paid(*args, **kwargs)
        captured.append(result[0])
        return result

    monkeypatch.setattr(module, 'paid_call', measured)
    monkeypatch.setattr(original_runner, 'runner', lambda: module)
    unknown_stops(monkeypatch, tmp_path)
    assert captured[-1]['status'] == 'unknown'
    assert captured[-1]['elapsed_seconds'] >= 0
