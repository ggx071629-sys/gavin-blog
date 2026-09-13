"""Local launcher diagnostics never call a provider or touch real processes."""

import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def launcher(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[3] / "scripts/local_launcher.py"
    spec = importlib.util.spec_from_file_location("launcher_under_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "STATE_DIR", tmp_path)
    monkeypatch.setattr(module, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    return module


def test_expired_probe_does_not_misdiagnose_validation_failure(launcher, tmp_path):
    path = tmp_path / "probe.json"
    path.write_text(
        json.dumps(
            {
                "completed_at": (datetime.now(UTC) - timedelta(days=2)).isoformat(),
                "secret": "DO_NOT_PRINT",
            }
        )
    )
    message = launcher.probe_refresh_hint(path)
    assert "单纯变旧不要求付费复验" in message
    assert "到期" not in message
    assert "保留原 ledger" in message
    assert "DO_NOT_PRINT" not in message


@pytest.mark.parametrize(
    "payload", [None, {}, {"completed_at": "invalid"}, {"completed_at": "2020-01-01"}]
)
def test_invalid_probe_remains_a_failure_hint(launcher, tmp_path, payload):
    path = tmp_path / "probe.json"
    path.write_text(json.dumps(payload))
    assert "无效" in launcher.probe_refresh_hint(path)


def test_stop_without_owner_explains_last_failure(launcher, monkeypatch, capsys):
    launcher.write_state({"status": "failed", "message": "Chat 验证记录过期"})
    monkeypatch.setattr(launcher, "active", lambda _: False)
    assert launcher.stop() == 0
    output = capsys.readouterr().out
    assert "无需停止" in output
    assert "上次启动失败：Chat 验证记录过期" in output
    assert not list(launcher.STATE_DIR.glob("stop-*"))


def test_manager_early_exit_does_not_wait_four_minutes(launcher, monkeypatch, capsys):
    monkeypatch.setattr(launcher, "active", lambda _: False)
    monkeypatch.setattr(
        launcher.subprocess, "Popen", lambda *a, **kw: SimpleNamespace(poll=lambda: 1)
    )
    waits = []
    monkeypatch.setattr(launcher.time, "sleep", waits.append)
    assert launcher.start(no_browser=True) == 1
    assert len(waits) == 10
    assert "启动管理进程已退出" in capsys.readouterr().out


def test_ready_instance_is_reused(launcher, monkeypatch):
    launcher.write_state({"status": "ready"})
    monkeypatch.setattr(launcher, "active", lambda _: True)

    def forbidden(*args, **kwargs):
        raise AssertionError("must not spawn a duplicate manager")

    monkeypatch.setattr(launcher.subprocess, "Popen", forbidden)
    assert launcher.start(no_browser=True) == 0


def test_start_prints_terminal_failure_once(launcher, monkeypatch, capsys):
    previous = {"token": "old"}
    failed = {"token": "new", "status": "failed", "message": "synthetic failure"}
    states = iter([previous, failed])
    monkeypatch.setattr(launcher, "read_state", lambda: next(states))
    monkeypatch.setattr(launcher, "active", lambda state: state is failed)
    monkeypatch.setattr(
        launcher.subprocess, "Popen", lambda *a, **kw: SimpleNamespace(poll=lambda: None)
    )
    assert launcher.start(no_browser=True) == 1
    assert capsys.readouterr().out.count("synthetic failure") == 1


def test_selected_probe_path_preserves_original(launcher, monkeypatch, tmp_path):
    path = tmp_path / "converted.json"
    monkeypatch.setenv("GAVIN_ASSISTANT_LOCAL_PROBE_PATH", str(path))
    assert launcher.selected_probe_path() == path
    from scripts import run_assistant_dev

    monkeypatch.setattr("sys.argv", ["run_assistant_dev"])
    assert run_assistant_dev.parse_args().probe == path


def test_managed_worker_uses_real_config_and_cleans_resources(launcher, monkeypatch):
    from app import config, db
    from app.assistant_index import embeddings, runtime, worker

    calls = []
    settings = SimpleNamespace(
        assistant_index_worker_enabled=True, database_url="sqlite:///real.db"
    )
    monkeypatch.setattr(launcher.os, "chdir", lambda path: calls.append(("cwd", path)))
    monkeypatch.setattr(config, "Settings", lambda **kw: (calls.append(kw), settings)[1])
    monkeypatch.setattr(
        embeddings, "validate_assistant_worker_settings", lambda s: calls.append(("validate", s))
    )
    database = SimpleNamespace(engine=SimpleNamespace(dispose=lambda: calls.append("disposed")))
    monkeypatch.setattr(db, "Database", lambda url: (calls.append(("database", url)), database)[1])
    instance = SimpleNamespace(
        database=database,
        store=SimpleNamespace(client=SimpleNamespace(close=lambda: calls.append("closed"))),
    )
    monkeypatch.setattr(runtime, "build_runtime", lambda s, d: instance)

    def stopped(actual):
        assert actual is instance
        raise KeyboardInterrupt

    monkeypatch.setattr(worker, "run_forever", stopped)
    with pytest.raises(KeyboardInterrupt):
        launcher.run_worker()
    assert {"_env_file": ".env.e5"} in calls
    assert ("database", "sqlite:///real.db") in calls
    assert calls[-2:] == ["closed", "disposed"]
    settings.assistant_index_worker_enabled = False
    calls.clear()
    with pytest.raises(RuntimeError, match="未启用"):
        launcher.run_worker()
    assert not any(isinstance(c, tuple) and c[0] == "database" for c in calls)
