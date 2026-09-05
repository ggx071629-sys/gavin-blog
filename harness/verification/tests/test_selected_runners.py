from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from harness.tools import selected_tests as runner
from harness.tools import test_collection as tc


def test_vitest_collection_keeps_optional_json_output_after_all_selectors(
    tmp_path, monkeypatch
):
    path = tmp_path / "apps/web/tests/unit/example.test.ts"
    path.parent.mkdir(parents=True)
    original = "it('chosen', () => expect(true).toBe(true))"
    path.write_text(original)
    commands = []

    def invoke(command, cwd):
        commands.append(command)
        assert command[-1] == "--json"
        return json.dumps([{"file": str(path), "name": "group > chosen"}])

    monkeypatch.setattr(tc, "_run", invoke)
    rows = tc._collect_vitest(
        tmp_path,
        selectors=["tests/unit/example.test.ts", "-t", "chosen"],
        prepare=False,
    )
    assert path.read_text() == original
    assert len(commands) == 1 and rows[0]["name"] == "chosen"


def test_selected_javascript_collection_rejects_missing_duplicate_and_disabled(
    tmp_path, monkeypatch
):
    ref = {
        "kind": "vitest",
        "gate": "web-quality",
        "path": "apps/web/tests/unit/example.test.ts",
        "name": "chosen",
    }
    monkeypatch.setattr(
        runner, "command_for", lambda *_: (["npm", "test", "chosen"], tmp_path)
    )
    commands = []
    monkeypatch.setattr(runner, "ensure_prerequisites", lambda *a: 0)

    def invoke(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout="Tests 1 passed", stderr="")

    monkeypatch.setattr(runner, "_run_supervised_command", invoke)
    for rows in [
        [],
        [{**ref, "disabled": ["skip"]}],
        [{**ref, "disabled": []}, {**ref, "disabled": []}],
    ]:
        commands.clear()
        monkeypatch.setattr(tc, "_collect_vitest", lambda *_, rows=rows, **__: rows)
        with pytest.raises(ValueError, match="missing, duplicate or disabled"):
            runner.run_selected([ref], tmp_path)
        assert not commands  # prerequisites are stubbed; no test execution


def test_javascript_file_and_name_selectors_do_not_form_cross_products(tmp_path):
    refs = [
        {
            "kind": "vitest",
            "path": "apps/web/tests/unit/a.test.ts",
            "name": "literal [x]",
        },
        {
            "kind": "vitest",
            "path": "apps/web/tests/unit/b.test.ts",
            "name": "other (y)",
        },
    ]
    groups = runner.batches(refs)
    assert len(groups) == 2
    command, _ = runner.command_for(groups[0], tmp_path)
    assert "tests/unit/a.test.ts" in command and "tests/unit/b.test.ts" not in command
    assert r"literal\ \[x\]" in command[-1] and "other" not in command[-1]


def test_playwright_binds_selected_file_config_project_without_suite_wrapper(tmp_path):
    ref = {
        "kind": "playwright",
        "gate": "e2e",
        "path": "apps/web/tests/e2e/profile.spec.ts",
        "name": "chosen",
    }
    command, _ = runner.command_for([ref], tmp_path)
    assert command[command.index("--config") + 1] == "playwright.config.ts"
    assert command[command.index("--project") + 1] == "chromium"
    assert "--retries=0" in command and "run-playwright-e2e.mjs" not in command
