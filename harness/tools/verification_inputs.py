"""Conservative v1 input identity and cheap execution preconditions."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import product_verification as pv
from .config import project_root
from .run_store import digest

# Only these external values reach collectors and gate processes. Application secrets
# and arbitrary test flags are excluded, not copied or persisted in a manifest.
ENVIRONMENT_KEYS = (
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "SYSTEMDRIVE",
    "TEMP",
    "TMP",
    "TMPDIR",
    "HOME",
    "USERPROFILE",
    "LOCALAPPDATA",
    "APPDATA",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "PROGRAMDATA",
    "ALLUSERSPROFILE",
    "LANG",
    "LC_ALL",
    "TZ",
    "PLAYWRIGHT_BROWSERS_PATH",
)


def controlled_environment() -> dict[str, str]:
    allowed = set(ENVIRONMENT_KEYS)
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    return {
        **env,
        "CI": "1",
        "PYTHONUNBUFFERED": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "NPM_CONFIG_YES": "false",
        "NPM_CONFIG_USERCONFIG": str(Path(__file__).with_name("empty-user.npmrc")),
        "NPM_CONFIG_GLOBALCONFIG": str(Path(__file__).with_name("empty-global.npmrc")),
    }


def _is_link(path: Path) -> bool:
    # pathlib.is_symlink() alone misses Windows npm workspace junctions.
    return path.is_symlink() or bool(
        getattr(path.lstat(), "st_file_attributes", 0) & 0x400
    )


def tree_digest(root: Path) -> str:
    """Hash installed code, binding workspace links to their HEAD-controlled source."""
    if not root.is_dir():
        raise pv.ProductVerificationError(
            f"dependency directory is missing: {root.name}"
        )
    repository = project_root().resolve()
    package = repository / "package.json"
    workspace_paths = []
    if package.is_file():
        workspaces = json.loads(package.read_bytes()).get("workspaces", [])
        if isinstance(workspaces, list):
            workspace_paths = [
                (repository / value).resolve()
                for value in workspaces
                if isinstance(value, str) and "*" not in value
            ]
    result = hashlib.sha256()
    for directory, dirs, files in os.walk(root, followlinks=False):
        candidates = sorted(
            d for d in dirs if d not in {"__pycache__", ".cache", ".vite"}
        )
        linked_dirs = [d for d in candidates if _is_link(Path(directory) / d)]
        dirs[:] = [d for d in candidates if d not in linked_dirs]
        for name in sorted([*files, *linked_dirs]):
            path = Path(directory) / name
            if path.suffix == ".pyc":
                continue
            relative = path.relative_to(root).as_posix().encode()
            result.update(len(relative).to_bytes(8, "big"))
            result.update(relative)
            if _is_link(path):
                target = path.resolve()
                if target.is_relative_to(root.resolve()):
                    binding = (
                        "dependency:" + target.relative_to(root.resolve()).as_posix()
                    )
                elif target in workspace_paths and target.is_relative_to(repository):
                    binding = (
                        "workspace-head:" + target.relative_to(repository).as_posix()
                    )
                elif (
                    root.name == ".venv"
                    and path.parent.name == "bin"
                    and path.name.startswith("python")
                    and target.is_file()
                ):
                    binding = (
                        "interpreter:" + hashlib.sha256(target.read_bytes()).hexdigest()
                    )
                else:
                    raise pv.ProductVerificationError(
                        "dependency link escapes its controlled input roots"
                    )
                result.update(b"link" + hashlib.sha256(binding.encode()).digest())
            elif path.is_file():
                content = hashlib.sha256()
                with path.open("rb") as handle:
                    while chunk := handle.read(1024 * 1024):
                        content.update(chunk)
                result.update(b"file" + content.digest())
    return result.hexdigest()


def _python_identity(executable: str) -> str:
    completed = subprocess.run(
        [executable, "-c", "import sys; print(sys.version)"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
        env=controlled_environment(),
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    return completed.stdout.strip()


def input_snapshot(
    mappings: dict[str, list[str]], fingerprints: dict[str, str]
) -> dict[str, Any]:
    from .impact import current_plan
    if current_plan.get() is not None:
        return scoped_snapshot(mappings, fingerprints, current_plan.get())
    from .isolated_verification import isolation_config

    root = project_root()
    configured = pv._configured_gates()
    commands = {gate: pv._command(gate, configured[gate])[0] for gate in mappings}
    executables = {sys.executable, *(command[0] for command in commands.values())}
    # The global collector uses Node/npm even for a Harness-only task.
    node, npm = shutil.which("node"), shutil.which("npm")
    if node is None or npm is None:
        raise pv.ProductVerificationError("Node/npm collector toolchain is missing")
    executables.update((node, npm))
    toolchain = {
        str(Path(path).resolve()): hashlib.sha256(Path(path).read_bytes()).hexdigest()
        for path in sorted(executables)
    }
    toolchain["python_runtime_versions"] = {
        path: _python_identity(path)
        for path in sorted(executables)
        if Path(path).name.lower().startswith("python")
    }
    dependencies = {
        value: tree_digest(root / value) for value in isolation_config()["reuse_paths"]
    }
    npm_root = (
        Path(npm).parent / "node_modules/npm"
        if os.name == "nt"
        else Path(npm).resolve().parent.parent
    )
    dependencies["npm-toolchain"] = tree_digest(npm_root)
    if set(mappings) & {"e2e", "release"}:
        browser_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
        if browser_path == "0":
            browsers = root / "node_modules/playwright-core/.local-browsers"
        elif browser_path:
            browsers = Path(browser_path)
            if not browsers.is_absolute():
                raise pv.ProductVerificationError(
                    "PLAYWRIGHT_BROWSERS_PATH must be absolute for reusable verification"
                )
        else:
            browsers = (
                Path(os.environ["LOCALAPPDATA"]) / "ms-playwright"
                if os.name == "nt"
                else Path.home()
                / (
                    "Library/Caches/ms-playwright"
                    if sys.platform == "darwin"
                    else ".cache/ms-playwright"
                )
            )
        dependencies["playwright-browsers"] = tree_digest(browsers)
    # Every tracked script/config/data initializer is bound by HEAD. Runner files are
    # also bound by the required clean-source check before and after execution.
    return {
        "version": 1,
        "head": pv.head_commit(),
        "fingerprints": fingerprints,
        "mappings": list(mappings.items()),
        "platform": [
            platform.system(),
            platform.release(),
            platform.machine(),
            sys.version,
        ],
        "toolchain": digest(toolchain),
        "dependencies": dependencies,
        "environment": digest(controlled_environment()),
        "commands": {gate: configured[gate] for gate in mappings},
        "build_artifacts": "never-reused; missing gates build in a new worktree",
    }


def preflight(mappings: dict[str, list[str]], *, selected_refs=None) -> None:
    from .isolated_verification import isolation_config

    root = project_root().resolve()
    from .impact import current_plan, dependency_paths
    reuse_paths = dependency_paths(mappings) if current_plan.get() is not None else isolation_config()["reuse_paths"]
    for value in reuse_paths:
        path = (root / value).resolve()
        if not path.is_relative_to(root) or not path.is_dir():
            raise pv.ProductVerificationError(
                f"dependency source missing or outside project: {value}"
            )
    for gate in mappings:
        pv._command(gate, pv._configured_gates()[gate])
    ports = set()
    plan = current_plan.get()
    if plan is not None and not plan.get("release"):
        from .selected_tests import playwright_config
        for ref in selected_refs if selected_refs is not None else plan["test_refs"]:
            if ref["gate"] in mappings and ref["kind"] == "playwright":
                config_name, _ = playwright_config(ref["path"])
                ports.update({"playwright.config.ts": (3100, 8100),
                              "playwright.assistant.config.ts": (3101, 8101),
                              "playwright.quality.config.ts": (3300, 8300),
                              "playwright.failure.config.ts": (3200, 8200)}[config_name])
    elif set(mappings) & {"e2e", "release"}:
        ports.update((3100, 8100, 3101, 8101))
    if ports:
        for port in sorted(ports):
            for host in ("127.0.0.1", "::1"):
                family = socket.AF_INET6 if ":" in host else socket.AF_INET
                with socket.socket(family, socket.SOCK_STREAM) as probe:
                    try:
                        probe.bind((host, port))
                    except OSError as error:
                        if host == "::1" and error.errno in {97, 10047, 99, 10049}:
                            continue
                        owner = port_owner(port)
                        raise pv.ProductVerificationError(
                            f"port-conflict: {host}:{port}; {owner}"
                        ) from error


def port_owner(port: int) -> str:
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["netstat", "-ano", "-p", "tcp"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            rows = [line.split() for line in result.stdout.splitlines()]
            pids = sorted(
                {
                    row[-1]
                    for row in rows
                    if len(row) >= 5 and row[1].endswith(f":{port}")
                }
            )
            return "owner PID " + ",".join(pids) if pids else "owner unavailable"
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "owner unavailable; no process was terminated"


def scoped_snapshot(mappings, fingerprints, plan):
    """No installed-tree walk. Reuse requires explicit, bounded input ownership.

    Harness tests run with plugin auto-discovery disabled. Only the selected
    distributions and their declared files are hashed, including RECORD itself.
    Product executions use same-process close until their dependency contract is
    registered; an incomplete contract never grants cross-process reuse.
    """
    root = project_root()
    refs = plan["test_refs"]
    harness_only = all(r["kind"] == "pytest" and r["path"].startswith("harness/") for r in refs)
    configured = pv._configured_gates()
    commands = {g: pv._command(g, configured[g])[0] for g in mappings}
    executables = {sys.executable, *(c[0] for c in commands.values())}
    for name in (["git"] if harness_only else ["git", "node", "npm"]):
        executable = shutil.which(name)
        if executable:
            executables.add(executable)
    toolchain = {str(Path(p).resolve()): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sorted(executables)}
    dependencies = {}
    reuse_enabled = harness_only and bool(load_reuse_policy())
    if refs and reuse_enabled:
        python = str(root / "apps/api/.venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
        script = r'''
import hashlib, importlib.metadata as m, json
names = ['pytest', 'pluggy', 'packaging', 'iniconfig', 'pygments', 'colorama']
result = {}
for name in names:
    try: dist = m.distribution(name)
    except m.PackageNotFoundError:
        if name == 'colorama': continue
        raise
    h = hashlib.sha256()
    for file in sorted(dist.files or [], key=str):
        if str(file).endswith('.pyc') or '__pycache__' in str(file): continue
        path = dist.locate_file(file)
        if not path.is_file(): raise RuntimeError('missing dependency input: ' + str(file))
        h.update(str(file).encode()); h.update(hashlib.sha256(path.read_bytes()).digest())
    result[name] = h.hexdigest()
print(json.dumps(result, sort_keys=True))
'''
        try:
            completed = subprocess.run([python, "-c", script], capture_output=True, text=True, check=True,
                                       timeout=30, env=controlled_environment(),
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except (OSError, subprocess.SubprocessError) as error:
            diagnostic = str(getattr(error, 'stderr', '') or 'dependency probe could not complete').strip().splitlines()[-1]
            raise pv.ProductVerificationError('dependency input check failed: ' + diagnostic[:240]) from error
        dependencies = json.loads(completed.stdout)
    return {"version": 3, "selection_protocol": 3, "head": pv.head_commit(), "fingerprints": fingerprints,
            "plan": digest(plan), "mappings": list(mappings.items()), "commands": commands,
            "platform": [platform.system(), platform.machine(), sys.version],
            "toolchain": digest(toolchain), "dependencies": dependencies,
            "environment": digest(controlled_environment()),
            "reusable": reuse_enabled,
            "persistent_close": not refs or reuse_enabled,
            "build_artifacts": "never reused; selected prerequisites rebuilt in isolated worktree"}


def load_reuse_policy():
    from .config import load_config
    return load_config()["verification"].get("impact", {}).get("reuse", False)
