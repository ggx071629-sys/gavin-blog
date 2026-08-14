from __future__ import annotations

import json
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
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1" in text
    assert "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02" not in text
    assert "astral-sh/setup-uv@ae62891fec2bb8e7d6c99fc78c9fec3a63790f8d # v10.0.0" in text
    assert 'python-version: "3.11"' in text
    assert 'node-version: "22"' in text
    assert 'version: "0.12.4"' in text
    assert "enable-cache: false" in text
    assert "working-directory: apps/api" in text
    assert "uv sync --locked --extra dev --python 3.11" in text
    assert "pip install" not in text
    assert "npm ci" in text
    assert "playwright install --with-deps chromium" in text


def test_release_workflow_persists_only_sanitized_telemetry() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert text.count("if: always()") == 2
    assert "telemetry-summary --json" in text
    assert "telemetry-health --json" in text
    assert "${GITHUB_STEP_SUMMARY}" in text
    assert "${{ runner.temp }}/harness-telemetry/summary.json" in text
    assert "${{ runner.temp }}/harness-telemetry/health.json" in text
    assert "if-no-files-found: error" in text
    assert "retention-days: 14" in text
    assert "harness/telemetry/local" not in text
    assert ".run/" not in text
    assert "my_image/" not in text
    assert "my_blog_fork/" not in text


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

    assert '".github/"' in config
    assert {".run/", "my_image/", "my_blog_fork/"}.issubset(set(ignore))


def test_openapi_export_forces_lf_for_cross_platform_byte_comparison() -> None:
    exporter = (ROOT / "apps" / "api" / "scripts" / "export_openapi.py").read_text(
        encoding="utf-8"
    )

    assert 'target.open("w", encoding="utf-8", newline="\\n")' in exporter


def test_native_optional_dependencies_are_locked_for_ci_and_windows() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
    expected = {
        "@rollup/rollup-linux-x64-gnu": ("4.62.3", "linux", "x64", "glibc"),
        "@rollup/rollup-win32-x64-msvc": ("4.62.3", "win32", "x64", None),
        "lightningcss-linux-x64-gnu": ("1.33.0", "linux", "x64", "glibc"),
        "lightningcss-win32-x64-msvc": ("1.33.0", "win32", "x64", None),
    }

    assert package["optionalDependencies"] == {
        name: version for name, (version, _os, _cpu, _libc) in expected.items()
    }
    assert lock["packages"][""]["optionalDependencies"] == package["optionalDependencies"]
    for name, (version, operating_system, cpu, libc) in expected.items():
        record = lock["packages"][f"node_modules/{name}"]
        assert record["version"] == version
        assert record["optional"] is True
        assert record["os"] == [operating_system]
        assert record["cpu"] == [cpu]
        if libc is None:
            assert "libc" not in record
        else:
            assert record["libc"] == [libc]


def test_playwright_hydration_readiness_is_shared_bounded_and_not_retried() -> None:
    helper = ROOT / "apps" / "web" / "tests" / "support" / "hydration.ts"
    helper_text = helper.read_text(encoding="utf-8")

    assert "export const HYDRATION_TIMEOUT_MS = 30_000" in helper_text
    assert "page.getByTestId('app-root')" in helper_text
    assert ".toHaveAttribute('data-hydrated', 'true', { timeout: HYDRATION_TIMEOUT_MS })" in helper_text

    scattered = {
        path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in (ROOT / "apps" / "web" / "tests").rglob("*.ts")
        if path != helper and "data-hydrated" in path.read_text(encoding="utf-8")
    }
    assert scattered == {}

    for name in (
        "playwright.config.ts",
        "playwright.quality.config.ts",
        "playwright.failure.config.ts",
    ):
        config = (ROOT / "apps" / "web" / name).read_text(encoding="utf-8")
        assert "retries: 0" in config
        assert "expect: {" not in config
