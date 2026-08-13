from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


def test_release_workflow_has_bounded_triggers_permissions_and_history() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "pull_request:" in text
    assert "push:" in text
    assert "workflow_dispatch:" in text
    assert text.count("branches: [main]") == 2
    assert "permissions:\n  contents: read" in text
    assert "cancel-in-progress: true" in text
    assert "fetch-depth: 0" in text
    assert "timeout-minutes: 30" in text
    assert "write" not in text


def test_release_workflow_pins_actions_and_reconstructs_dependencies() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1" in text
    assert "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0" in text
    assert "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0" in text
    assert 'python-version: "3.11"' in text
    assert 'node-version: "22"' in text
    assert "python -m venv apps/api/.venv" in text
    assert 'pip install -e "./apps/api[dev]"' in text
    assert "npm ci" in text
    assert "playwright install --with-deps chromium" in text


def test_release_workflow_enforces_trusted_change_coverage_refs() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "PR_BASE_SHA" in text
    assert "EVENT_BEFORE" in text
    assert 'git rev-parse "${head_ref}^1"' in text
    assert '"${base_ref}" =~ ^0+$' in text
    assert 'git cat-file -e "${base_ref}^{commit}"' in text
    assert 'HARNESS_BASE_REF=${base_ref}' in text
    assert 'HARNESS_HEAD_REF=${head_ref}' in text
    assert text.count("npm run quality:release") == 1


def test_ci_and_local_workspace_paths_are_governed() -> None:
    config = (ROOT / "harness" / "config.toml").read_text(encoding="utf-8")
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert '".github/workflows/"' in config
    assert {".run/", "my_image/", "my_blog_fork/"}.issubset(set(ignore))
