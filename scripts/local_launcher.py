"""Windows desktop shortcuts for the existing local real-assistant commands."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps/api"
STATE_DIR = ROOT / ".run/quick-start"
STATE_FILE = STATE_DIR / "state.json"
WEB_URL = "http://127.0.0.1:3101"
PYTHON = API / ".venv/Scripts/python.exe"


def read_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_state(state):
    temporary = STATE_DIR / f"state-{uuid.uuid4().hex}.tmp"
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(STATE_FILE)


def process_stamp(pid):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetExitCodeProcess.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, int(pid or 0))
    if not handle:
        return None
    try:
        times = [wintypes.FILETIME() for _ in range(4)]
        code = wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != 259:
            return None
        if not kernel.GetProcessTimes(handle, *(ctypes.byref(value) for value in times)):
            return None
        return (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
    finally:
        kernel.CloseHandle(handle)


def active(state):
    return bool(state.get("stamp") and process_stamp(state.get("pid")) == state["stamp"])


def port_open(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.4):
            return True
    except OSError:
        return False


def http_json(url, headers=None):
    # Local service checks must not follow a redirect to another destination.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(url, headers=headers or {})
    with opener.open(request, timeout=3) as response:
        return json.load(response)


def child_environment(extra):
    # E5 and Qdrant receive only OS essentials and their own credentials.
    allowed = {
        "SYSTEMROOT",
        "WINDIR",
        "PATH",
        "PATHEXT",
        "TEMP",
        "TMP",
        "COMSPEC",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "PROGRAMDATA",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
        "SYSTEMDRIVE",
        "NUMBER_OF_PROCESSORS",
    }
    result = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    result.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", NUXT_TELEMETRY_DISABLED="1")
    result.update(extra)
    return result


class Job:
    """Own child process trees, including detached Node/Python descendants."""

    def __init__(self):
        size = ctypes.c_size_t

        class Limits(ctypes.Structure):
            _fields_ = [
                ("process_time", ctypes.c_int64),
                ("job_time", ctypes.c_int64),
                ("flags", wintypes.DWORD),
                ("minimum", size),
                ("maximum", size),
                ("active", wintypes.DWORD),
                ("affinity", size),
                ("priority", wintypes.DWORD),
                ("scheduling", wintypes.DWORD),
            ]

        class Counters(ctypes.Structure):
            _fields_ = [
                (name, ctypes.c_uint64)
                for name in (
                    "read",
                    "write",
                    "other",
                    "read_bytes",
                    "write_bytes",
                    "other_bytes",
                )
            ]

        class Extended(ctypes.Structure):
            _fields_ = [
                ("basic", Limits),
                ("io", Counters),
                ("process_memory", size),
                ("job_memory", size),
                ("peak_process", size),
                ("peak_job", size),
            ]

        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.kernel.CreateJobObjectW.restype = wintypes.HANDLE
        self.kernel.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        self.kernel.AssignProcessToJobObject.argtypes = [
            wintypes.HANDLE,
            wintypes.HANDLE,
        ]
        self.kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.kernel.CreateJobObjectW(None, None)
        limits = Extended()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.handle or not self.kernel.SetInformationJobObject(
            self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        ):
            self.close()
            raise OSError("无法建立启动进程的清理边界。")

    def assign(self, process):
        if not self.kernel.AssignProcessToJobObject(self.handle, int(process._handle)):
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=10,
                check=False,
            )
            raise OSError("无法登记子进程，已中止启动。")

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def send_console_stop(pid):
    """Runs in a helper process so console attachment cannot affect the manager."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.FreeConsole()
    if not kernel.AttachConsole(int(pid)):
        return 1
    try:
        kernel.SetConsoleCtrlHandler(None, True)
        sent = kernel.GenerateConsoleCtrlEvent(1, 0)  # CTRL_BREAK is not inherited as ignored.
        time.sleep(0.2)
        return 0 if sent else 1
    finally:
        kernel.FreeConsole()


def probe_refresh_hint(path):
    """Do not infer the cause of failed validation from an untrusted timestamp."""
    return (
        "真实问答配置或 Chat 验证记录无效。请检查 apps/api/.env、.env.e5 "
        "和 local-chat-probe.json 的签名、成功状态、时间及配置绑定；"
        "记录单纯变旧不要求付费复验。保留原 ledger，不要删除账本或修改记录时间。"
        "详细步骤见 apps/api/README.md。"
    )


def selected_probe_path():
    return Path(
        os.environ.get(
            "GAVIN_ASSISTANT_LOCAL_PROBE_PATH",
            str(API / "data/assistant-qualification/local-chat-probe.json"),
        )
    )


def configuration():
    sys.path.insert(0, str(API))
    from app.assistant.development import build_real_development_settings
    from app.config import Settings
    from app.local_embedding.service import identity

    chat, base = Settings(), Settings(_env_file=".env.e5")
    try:
        settings = build_real_development_settings(
            base,
            chat,
            run_root=API / "data/assistant-local-real",
            web_origin=WEB_URL,
            proxy_secret=chat.assistant_proxy_hmac_secret or "",
            probe_path=selected_probe_path(),
        )
    except Exception:  # noqa: BLE001 - never expose credential-bearing validation input.
        raise RuntimeError(probe_refresh_hint(selected_probe_path())) from None
    node = shutil.which("node.exe")
    npm = Path(node).parent / "node_modules/npm/bin/npm-cli.js" if node else Path("missing-npm")
    embedding_python = API / "embedding_service/.venv/Scripts/python.exe"
    qdrant = API / "data/qdrant-bin/v1.18.3/qdrant.exe"
    storage = API / "data/e5/qdrant"
    for path in (embedding_python, qdrant, npm, storage, ROOT / "node_modules"):
        if not path.exists():
            raise RuntimeError(f"缺少已有运行依赖或存储：{path}")
    return settings, identity(), node, npm, embedding_python, qdrant, storage


def run_worker():
    """Use the same real content/index configuration as the managed API."""
    os.chdir(API)
    sys.path.insert(0, str(API))
    from app.assistant_index.embeddings import validate_assistant_worker_settings
    from app.assistant_index.runtime import build_runtime
    from app.assistant_index.worker import run_forever
    from app.config import Settings
    from app.db import Database

    settings = Settings(_env_file=".env.e5")
    if not settings.assistant_index_worker_enabled:
        raise RuntimeError("真实问答索引 worker 未启用，请检查 .env.e5。")
    validate_assistant_worker_settings(settings)
    runtime = build_runtime(settings, Database(settings.database_url))
    try:
        run_forever(runtime)
    finally:
        runtime.store.client.close()
        runtime.database.engine.dispose()


def run_manager():
    import msvcrt

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock = (STATE_DIR / "manager.lock").open("a+b")
    lock.seek(0, 2)
    if not lock.tell():
        lock.write(b"0")
        lock.flush()
    lock.seek(0)
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        lock.close()
        return 0
    token = uuid.uuid4().hex
    run_dir = STATE_DIR / token
    run_dir.mkdir()
    state = {
        "pid": os.getpid(),
        "stamp": process_stamp(os.getpid()),
        "token": token,
        "status": "starting",
        "message": "检查配置…",
        "url": WEB_URL,
        "logs": str(run_dir),
        "owned": [],
        "reused": [],
    }
    owned, job = [], None
    failure = None
    stop_file = STATE_DIR / f"stop-{token}"

    def progress(message):
        state["message"] = message
        write_state(state)

    def check_cancel():
        if stop_file.exists():
            raise InterruptedError("启动已取消。")
        for name, process, _log in owned:
            if process.poll() is not None:
                raise RuntimeError(f"{name} 已退出，请查看日志目录：{run_dir}")

    def spawn(name, args, cwd, env):
        check_cancel()
        log = (run_dir / f"{name}.log").open("wb")
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        process = subprocess.Popen(
            [str(arg) for arg in args],
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            startupinfo=startup,
        )
        try:
            job.assign(process)
        except Exception:
            log.close()
            raise
        owned.append((name, process, log))
        state["owned"].append({"service": name, "pid": process.pid})

    def wait_ready(label, probe, timeout=150):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            check_cancel()
            try:
                if probe():
                    return
            except (OSError, ValueError):
                pass
            time.sleep(0.5)
        raise RuntimeError(f"{label} 启动超时，请查看日志目录：{run_dir}")

    try:
        progress("检查配置与现有服务…")
        os.chdir(API)
        settings, expected, node, npm, embedding_python, qdrant, storage = configuration()
        from app.assistant_qualification.provider_probe import local_chat_probe_notice

        probe_notice = local_chat_probe_notice(selected_probe_path(), settings)
        check_cancel()
        if port_open(3101) or port_open(8101):
            raise RuntimeError("3101/8101 端口被其他启动方式占用，请先停止之前的 Web/API。")
        job = Job()
        e5_headers = {"Authorization": f"Bearer {settings.assistant_embedding_api_key}"}
        qdrant_headers = {"api-key": settings.assistant_qdrant_api_key or ""}

        def e5_ready():
            data = http_json("http://127.0.0.1:8091/readyz", e5_headers)
            return all(data.get(key) == value for key, value in expected.items())

        def qdrant_ready():
            return (
                http_json("http://127.0.0.1:8092/collections", qdrant_headers).get("status") == "ok"
            )

        progress("启动或复用 Qdrant…")
        if port_open(8092) or port_open(8093):
            if not qdrant_ready():
                raise RuntimeError("现有 Qdrant 无法通过鉴权检查。")
            state["reused"].append("Qdrant")
        else:
            spawn(
                "qdrant",
                [qdrant],
                API / "data/e5",
                child_environment(
                    {
                        "QDRANT__SERVICE__HOST": "127.0.0.1",
                        "QDRANT__SERVICE__HTTP_PORT": "8092",
                        "QDRANT__SERVICE__GRPC_PORT": "8093",
                        "QDRANT__SERVICE__API_KEY": settings.assistant_qdrant_api_key,
                        "QDRANT__STORAGE__STORAGE_PATH": str(storage),
                        "QDRANT__STORAGE__SNAPSHOTS_PATH": str(API / "data/e5/snapshots"),
                        "QDRANT__TELEMETRY_DISABLED": "true",
                    }
                ),
            )
            wait_ready("Qdrant", qdrant_ready)
        progress("启动或复用 E5 模型，首次加载需要一些时间…")
        if port_open(8091):
            if not e5_ready():
                raise RuntimeError("现有 E5 的模型身份或鉴权不匹配。")
            state["reused"].append("E5")
        else:
            spawn(
                "e5",
                [embedding_python, "scripts/run_e5_service.py"],
                API,
                child_environment(
                    {
                        "GAVIN_ENVIRONMENT": "development",
                        "GAVIN_E5_MODEL_DIR": str(Path(settings.assistant_e5_model_dir).resolve()),
                        "GAVIN_E5_API_KEY": settings.assistant_embedding_api_key,
                        "HF_HUB_OFFLINE": "1",
                        "TRANSFORMERS_OFFLINE": "1",
                        "TOKENIZERS_PARALLELISM": "false",
                    }
                ),
            )
            wait_ready("E5", e5_ready)
        progress("启动真实内容索引 worker…")
        spawn(
            "worker",
            [PYTHON, "-B", Path(__file__).resolve(), "_worker"],
            API,
            child_environment({}),
        )
        progress("启动真实问答 API 与 Web…")
        app_env = {"GAVIN_ASSISTANT_LOCAL_PROBE_PATH": str(selected_probe_path())}
        if ledger := os.environ.get("GAVIN_ASSISTANT_EVALUATION_LEDGER"):
            app_env["GAVIN_ASSISTANT_EVALUATION_LEDGER"] = ledger
        spawn("app", [node, npm, "run", "dev:assistant:real"], ROOT, child_environment(app_env))

        def web_ready():
            request = urllib.request.Request(WEB_URL)
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(request, timeout=4) as response:
                return response.status == 200

        wait_ready("Web/API", web_ready)
        state["status"] = "ready"
        progress("项目已启动：" + WEB_URL + "\n" + probe_notice)
        while not stop_file.exists():
            check_cancel()
            time.sleep(0.5)
    except InterruptedError:
        pass
    except Exception as exc:  # noqa: BLE001 - clean owned services and redact credential-bearing errors.
        # Do not expose settings validation input values, HTTP headers or credentials.
        failure = (
            str(exc)
            if type(exc) is RuntimeError
            else f"启动失败（{type(exc).__name__}），请检查配置和本机日志。"
        )
    finally:
        state["status"] = "stopping"
        progress("正在停止本次启动的服务…")
        for _name, process, _log in reversed(owned):
            if process.poll() is None:
                try:
                    subprocess.run(
                        [
                            str(PYTHON),
                            "-B",
                            str(Path(__file__).resolve()),
                            "_signal",
                            str(process.pid),
                        ],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        timeout=5,
                        check=False,
                    )
                except (subprocess.TimeoutExpired, OSError):
                    pass
        deadline = time.monotonic() + 10
        while (
            any(process.poll() is None for _name, process, _log in owned)
            and time.monotonic() < deadline
        ):
            time.sleep(0.2)
        if job:
            job.close()  # Also cleans up detached descendants if graceful exit failed.
        for _name, process, log in owned:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                failure = "服务清理超时，请检查日志与端口。"
            log.close()
        state["status"] = "failed" if failure else "stopped"
        progress(failure or "本次启动的项目服务已停止。")
        stop_file.unlink(missing_ok=True)
        lock.close()
    return 1 if failure else 0


def start(no_browser=False):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    previous = read_state()
    manager = None
    if active(previous) and previous.get("status") == "ready":
        print("项目已在运行：" + WEB_URL)
        if not no_browser:
            os.startfile(WEB_URL)
        return 0
    if not active(previous):
        with (STATE_DIR / "manager.log").open("ab") as log:
            manager = subprocess.Popen(
                [str(PYTHON), "-B", str(Path(__file__).resolve()), "_run"],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
    last_message = None
    for attempt in range(480):
        state = read_state()
        current = active(state)
        if current and state.get("message") != last_message:
            last_message = state.get("message")
            print(last_message, flush=True)
        if current and state.get("status") == "ready":
            if not no_browser:
                os.startfile(WEB_URL)
            return 0
        if state.get("token") != previous.get("token") and state.get("status") in {
            "failed",
            "stopped",
        }:
            if state.get("message") != last_message:
                print(state.get("message"), flush=True)
            print("日志：" + state.get("logs", str(STATE_DIR)))
            return 1
        if manager is not None and manager.poll() is not None and not current and attempt >= 10:
            print(
                "启动管理进程已退出，未能启动项目。请检查 .run/quick-start/manager.log。",
                flush=True,
            )
            return 1
        time.sleep(0.5)
    print("启动仍未完成；请双击“停止项目.cmd”取消，并检查 .run/quick-start/manager.log。")
    return 1


def stop():
    state = read_state()
    if not active(state):
        print("当前没有由快捷入口管理的运行实例，无需停止。")
        if state.get("status") == "failed":
            print("上次启动失败：" + state.get("message", "请检查启动日志。"))
        print("其他终端或测试入口启动的服务不会被此脚本关闭。")
        return 0
    (STATE_DIR / ("stop-" + state["token"])).touch()
    print("正在停止 Web/API、索引 worker、E5 和 Qdrant（仅本次启动的服务）…", flush=True)
    for _ in range(300):
        current = read_state()
        if current.get("token") != state["token"]:
            print("已停止原启动实例；发现另一次启动，请按需再次停止。")
            return 0
        if not active(current):
            print(current.get("message", "已停止。"))
            return 1 if current.get("status") == "failed" else 0
        time.sleep(0.5)
    print("停止超时，请检查 .run/quick-start/ 下的日志。")
    return 1


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop", "_run", "_signal", "_worker"])
    parser.add_argument("pid", nargs="?")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("This shortcut launcher supports Windows only.")
    if args.action == "_signal":
        return send_console_stop(args.pid)
    if args.action == "_run":
        return run_manager()
    if args.action == "_worker":
        return run_worker()
    return start(args.no_browser) if args.action == "start" else stop()


if __name__ == "__main__":
    raise SystemExit(main())
