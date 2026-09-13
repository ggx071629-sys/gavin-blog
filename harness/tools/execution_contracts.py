"""Read-only plans and explicit prerequisites, shared only inside one worktree."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys

from .run_store import digest

CONFIGS = {
    "playwright.config.ts": ("dev", (3100, 8100)),
    "playwright.quality.config.ts": ("production", (3300, 8300)),
    "playwright.assistant.config.ts": ("assistant-build-in-server", (3101, 8101)),
    "playwright.failure.config.ts": ("failure-upstream", (3200, 8200)),
}


def prerequisites(refs):
    from .selected_tests import playwright_config

    web = [r for r in refs if r["kind"] in {"vitest", "playwright"}]
    if not web:
        return []
    items = [
        {
            "id": "nuxt-prepare",
            "command": ["npm", "exec", "--", "nuxt", "prepare"],
            "cwd": "apps/web",
            "env": {},
            "outputs": ["apps/web/.nuxt"],
            "inputs": [
                "package-lock.json",
                "apps/web/nuxt.config.ts",
                "apps/web/tsconfig.json",
            ],
            "consumers": web,
            "failure_kind": "initialization",
            "timeout_seconds": 120,
        }
    ]
    quality = [
        r
        for r in web
        if r["kind"] == "playwright"
        and playwright_config(r["path"])[0] == "playwright.quality.config.ts"
    ]
    if quality:
        items.append(
            {
                "id": "quality-build",
                "command": ["npm", "run", "build"],
                "cwd": "apps/web",
                "env": {},
                "outputs": ["apps/web/.output"],
                "inputs": ["package-lock.json", "apps/web/nuxt.config.ts"],
                "consumers": quality,
                "failure_kind": "initialization",
                "timeout_seconds": 600,
            }
        )
    return items


def ensure_prerequisites(refs, root, invoke, record):
    directory = root / ".run" / "harness-prerequisites"
    for item in prerequisites(refs):
        inputs = {
            p: hashlib.sha256((root / p).read_bytes()).hexdigest()
            for p in item["inputs"]
        }
        # The enclosing worktree fixes every source input; the receipt never leaves it.
        signature = digest(
            {k: v for k, v in item.items() if k != "consumers"}
            | {"input_sha256": inputs}
        )
        receipt = directory / (signature + ".json")
        if receipt.exists() and all((root / p).is_dir() for p in item["outputs"]):
            record(
                "initialization",
                "reused-in-worktree",
                item["consumers"],
                prerequisite=item["id"],
                input_sha256=inputs,
            )
            continue
        command = list(item["command"])
        command[0] = (
            shutil.which("npm.cmd" if sys.platform == "win32" else "npm") or "npm"
        )
        result = invoke(
            command,
            cwd=root / item["cwd"],
            timeout_seconds=item["timeout_seconds"],
            env=item["env"],
        )
        if result.returncode:
            record(
                "initialization",
                "failed",
                item["consumers"],
                prerequisite=item["id"],
                input_sha256=inputs,
            )
            return result.returncode
        if not all((root / p).is_dir() for p in item["outputs"]):
            raise ValueError(
                "initialization produced no declared outputs: " + item["id"]
            )
        directory.mkdir(parents=True, exist_ok=True)
        receipt.write_text(
            json.dumps({"id": item["id"], "input_sha256": inputs}), encoding="utf-8"
        )
        record(
            "initialization",
            "passed",
            item["consumers"],
            prerequisite=item["id"],
            input_sha256=inputs,
        )
    return 0
