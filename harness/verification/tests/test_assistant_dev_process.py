from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


def test_assistant_shutdown_stops_parent_and_descendant(tmp_path: Path) -> None:
    helper = Path(__file__).resolve().parents[3] / "scripts/assistant-dev-process.mjs"
    node = shutil.which("node")
    assert node is not None
    script = tmp_path / "shutdown.mjs"
    script.write_text(
        "import { spawn } from 'node:child_process';\n"
        "import { once } from 'node:events';\n"
        f"import {{ stopTree }} from {json.dumps(helper.as_uri())};\n"
        "const parentCode = `\n"
        "  const { spawn } = require('node:child_process');\n"
        "  const child = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], { windowsHide: true, stdio: 'ignore' });\n"
        "  child.once('spawn', () => console.log(child.pid));\n"
        "  setInterval(() => {}, 1000);\n"
        "`;\n"
        "const parent = spawn(process.execPath, ['-e', parentCode], {\n"
        "  detached: true, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],\n"
        "});\n"
        "const [data] = await once(parent.stdout, 'data');\n"
        "const descendant = Number(data.toString().trim());\n"
        "try {\n"
        "  await stopTree(parent);\n"
        "  for (const pid of [parent.pid, descendant]) {\n"
        "    let running = true;\n"
        "    for (let i = 0; i < 50 && running; i++) {\n"
        "      try { process.kill(pid, 0); } catch { running = false; }\n"
        "      if (running) await new Promise(r => setTimeout(r, 100));\n"
        "    }\n"
        "    if (running) throw new Error('surviving assistant process: ' + pid);\n"
        "  }\n"
        "} finally {\n"
        "  for (const pid of [descendant, parent.pid]) {\n"
        "    try { process.kill(pid, 'SIGKILL'); } catch {}\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [node, str(script)], capture_output=True, text=True, timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
