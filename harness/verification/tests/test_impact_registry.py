from pathlib import Path

from harness.tools.impact_registry import audit


def test_current_governed_sources_have_unique_existing_ownership_and_cases():
    result = audit(Path(__file__).resolve().parents[3])
    assert result["paths"] > 300
    assert result["errors"] == []


def test_new_unknown_source_fails_without_expanding_test_scope():
    result = audit(
        Path(__file__).resolve().parents[3],
        paths=["apps/web/utils/new-unregistered.ts"],
    )
    assert any("new-unregistered.ts: missing ownership" in e for e in result["errors"])


def test_structure_resolves_repeated_paths_once_but_rechecks_next_invocation(tmp_path, monkeypatch):
    from harness.tools import module_verification as mv
    from harness.verification.tests.test_module_coverage import _write_project
    _write_project(tmp_path)
    original=Path.resolve
    resolutions=[]
    def resolve(path, *args, **kwargs):
        if path.name=='contract_fixture.py': resolutions.append(path)
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'resolve',resolve)
    config={'verification':{'gates':{'harness-tests':{}}}}
    _,errors=mv.validate_module_contract(tmp_path,tmp_path/'harness',config,structure_only=True)
    assert not errors
    assert len(resolutions)==1
    (tmp_path/'harness/verification/tests/contract_fixture.py').unlink()
    _,errors=mv.validate_module_contract(tmp_path,tmp_path/'harness',config,structure_only=True)
    assert any('referenced file does not exist' in error for error in errors)
