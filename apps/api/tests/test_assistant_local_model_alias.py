from dataclasses import replace

import pytest

from app.assistant_qualification.provider_probe import (
    ProviderQualificationError,
    _identity_source,
    _local_chat_contract,
    _probe_digest,
)

from .test_assistant_provider_qualification import _local_probe_inputs


def test_local_alias_preserves_identity_binding_and_unknown_model_rejection(tmp_path, monkeypatch):
    args, _ = _local_probe_inputs(tmp_path, monkeypatch)
    settings = args['settings']
    limits = dict(approved_max_micro_cny=1_000_000, max_calls=27,
                  authorization_id='same-budget-new-alias')
    old = _local_chat_contract(settings=settings, **limits)
    current = _local_chat_contract(settings=settings.model_copy(
        update={'assistant_chat_model': 'deepseek-flash'}), **limits)
    assert current.model == 'deepseek-flash'
    assert current.model_identity_source == 'operator-declaration'
    assert _probe_digest(current) != _probe_digest(old)
    assert _probe_digest(replace(current, model_identity_source=old.model_identity_source)) != (
        _probe_digest(old))
    assert _identity_source('deepseek-flash', 'provider-response', current.model,
                            current.model_identity_source) == (True, 'provider-response')
    assert _identity_source(None, None, current.model_version,
                            current.model_identity_source) == (False, 'operator-declaration')
    for update in ({'assistant_chat_model': 'unreviewed'}, {'environment': 'production'}):
        with pytest.raises(ProviderQualificationError):
            _local_chat_contract(settings=settings.model_copy(update=update), **limits)
