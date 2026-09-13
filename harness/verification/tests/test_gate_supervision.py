from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

from harness.tools import product_verification


def test_supervised_command_streams_output_and_forces_unbuffered_python(
    capsys: pytest.CaptureFixture[str],
) -> None:
    completed = product_verification._run_supervised_command(
        [
            sys.executable,
            "-c",
            "import os,sys; print('gate-line', flush=True); print(os.environ.get('PYTHONUNBUFFERED', ''), flush=True)",
        ],
        cwd=Path.cwd(),
        timeout_seconds=10,
    )

    assert completed.returncode == 0
    assert "gate-line" in completed.stdout
    assert "1" in completed.stdout.splitlines()
    captured = capsys.readouterr()
    assert "gate-line" in captured.out


def test_supervised_command_kills_descendant_on_timeout(tmp_path: Path) -> None:
    marker = tmp_path / "child-pid.txt"
    script = (
        "import os, subprocess, sys, time\n"
        f"marker = {str(marker)!r}\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(90)'], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)\n"
        "with open(marker, 'w', encoding='utf-8') as handle:\n"
        "    handle.write(str(child.pid))\n"
        "time.sleep(90)\n"
    )

    with pytest.raises(subprocess.TimeoutExpired) as raised:
        product_verification._run_supervised_command(
            [sys.executable, "-c", script],
            cwd=tmp_path,
            timeout_seconds=2,
        )

    assert raised.value.timeout == 2
    child_pid = int(marker.read_text(encoding="utf-8"))
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and product_verification._pid_is_running(child_pid):
        time.sleep(0.1)
    assert not product_verification._pid_is_running(child_pid)
