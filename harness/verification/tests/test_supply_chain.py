from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import tomllib

CHECK_PATH = Path(__file__).parents[1] / "checks" / "supply_chain.py"
ROOT = Path(__file__).resolve().parents[3]
PIN = "a" * 40


def _load_check():
    spec = importlib.util.spec_from_file_location("harness_supply_chain_check", CHECK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _safe_repository(tmp_path: Path) -> None:
    _write(
        tmp_path / ".github" / "workflows" / "release.yml",
        f"""name: Release
on:
  pull_request:
permissions:
  contents: read
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{PIN} # v1.0.0
      - run: npm ci
      - run: uv sync --locked --extra dev --python 3.11
""",
    )
    _write(
        tmp_path / "package-lock.json",
        json.dumps(
            {
                "lockfileVersion": 3,
                "packages": {
                    "": {},
                    "node_modules/local-workspace": {
                        "resolved": "apps/example",
                        "link": True,
                    },
                    "node_modules/example": {
                        "resolved": "https://registry.npmjs.org/example/-/example-1.0.0.tgz",
                        "integrity": "sha512-example",
                    },
                },
            }
        ),
    )
    _write(
        tmp_path / "apps" / "api" / "uv.lock",
        """version = 1
revision = 3
requires-python = ">=3.11"

[[package]]
name = "example"
version = "1.0.0"
source = { registry = "https://pypi.org/simple" }
sdist = { url = "https://files.pythonhosted.org/example.tar.gz", hash = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" }
""",
    )


def _run(tmp_path: Path):
    return _load_check().run({"project_root": tmp_path})


def test_safe_supply_chain_baseline_passes(tmp_path: Path) -> None:
    _safe_repository(tmp_path)

    result = _run(tmp_path)

    assert result["passed"] is True
    assert "1 workflows" in result["details"][0]


def test_mutable_action_write_permission_and_dangerous_trigger_fail(tmp_path: Path) -> None:
    _safe_repository(tmp_path)
    workflow = tmp_path / ".github" / "workflows" / "release.yml"
    text = workflow.read_text(encoding="utf-8")
    text = text.replace("pull_request:", "pull_request_target:")
    text = text.replace("contents: read", "contents: write")
    text = text.replace(f"actions/checkout@{PIN}", "actions/checkout@v7")
    workflow.write_text(text, encoding="utf-8")

    result = _run(tmp_path)

    assert result["passed"] is False
    details = "\n".join(result["details"])
    assert "pull_request_target is forbidden" in details
    assert "permissions must be exactly" in details
    assert "full 40-character commit SHA" in details


def test_unlocked_installers_fail(tmp_path: Path) -> None:
    _safe_repository(tmp_path)
    workflow = tmp_path / ".github" / "workflows" / "release.yml"
    text = workflow.read_text(encoding="utf-8")
    text = text.replace("npm ci", "npm install")
    text = text.replace("uv sync --locked", "uv sync")
    text += "      - run: python -m pip install -e .\n"
    workflow.write_text(text, encoding="utf-8")

    result = _run(tmp_path)

    assert result["passed"] is False
    details = "\n".join(result["details"])
    assert "npm install is forbidden" in details
    assert "missing npm ci" in details
    assert "pip install is forbidden" in details
    assert "uv sync must use --locked" in details


def test_missing_or_untrusted_lockfiles_fail(tmp_path: Path) -> None:
    _safe_repository(tmp_path)
    (tmp_path / "package-lock.json").unlink()
    uv_lock = tmp_path / "apps" / "api" / "uv.lock"
    uv_lock.write_text(
        uv_lock.read_text(encoding="utf-8").replace(
            "https://pypi.org/simple", "https://mirror.invalid/simple"
        ),
        encoding="utf-8",
    )

    result = _run(tmp_path)

    assert result["passed"] is False
    details = "\n".join(result["details"])
    assert "package-lock.json: required lockfile is missing" in details
    assert "uses a non-PyPI registry" in details


def test_httpx_is_a_runtime_dependency_not_a_dev_only_dependency() -> None:
    with (ROOT / "apps" / "api" / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]

    assert any(item.startswith("httpx") for item in project["dependencies"])
    assert not any(
        item.startswith("httpx") for item in project["optional-dependencies"]["dev"]
    )
