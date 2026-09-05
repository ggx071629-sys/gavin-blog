"""Conservative v1 input identity and cheap execution preconditions."""

from __future__ import annotations

import hashlib
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
        "NPM_CONFIG_USERCONFIG": str(Path(__file__).with_name("empty-user.npmrc")),
        "NPM_CONFIG_GLOBALCONFIG": str(Path(__file__).with_name("empty-global.npmrc")),
    }


def tree_digest(root: Path) -> str:
    """Hash installed code; discard only bytecode and documented generated caches."""
    if not root.is_dir():
        raise pv.ProductVerificationError(
            f"dependency directory is missing: {root.name}"
        )
    result = hashlib.sha256()
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in {"__pycache__", ".cache", ".vite"})
        for name in sorted(
            [*files, *(d for d in dirs if (Path(directory) / d).is_symlink())]
        ):
            path = Path(directory) / name
            if path.suffix == ".pyc":
                continue
            relative = path.relative_to(root).as_posix().encode()
            result.update(len(relative).to_bytes(8, "big"))
            result.update(relative)
            if path.is_symlink():
                target = path.resolve()
                if not target.is_relative_to(root.resolve()):
                    raise pv.ProductVerificationError(
                        "dependency symlink escapes its input root"
                    )
                result.update(
                    b"link" + hashlib.sha256(os.readlink(path).encode()).digest()
                )
            elif path.is_file():
                content = hashlib.sha256()
                with path.open("rb") as handle:
                    while chunk := handle.read(1024 * 1024):
                        content.update(chunk)
                result.update(b"file" + content.digest())
    return result.hexdigest()


def input_snapshot(
    mappings: dict[str, list[str]], fingerprints: dict[str, str]
) -> dict[str, Any]:
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


def preflight(mappings: dict[str, list[str]]) -> None:
    from .isolated_verification import isolation_config

    root = project_root().resolve()
    for value in isolation_config()["reuse_paths"]:
        path = (root / value).resolve()
        if not path.is_relative_to(root) or not path.is_dir():
            raise pv.ProductVerificationError(
                f"dependency source missing or outside project: {value}"
            )
    for gate in mappings:
        pv._command(gate, pv._configured_gates()[gate])
    if set(mappings) & {"e2e", "release"}:
        # v1 uses canonical E2E defaults; external port overrides are not forwarded.
        for port in (3100, 8100, 3101, 8101):
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
