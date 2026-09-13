"""Windows local capacity experiment with dedicated processes, ports and databases."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
from sqlalchemy import select

from ..assistant.admin_operations import request_rebuild
from ..db import Database
from ..models import AssistantChunk, AssistantIndexCommand, AssistantIndexGeneration
from ..time_utils import utc_now
from .artifact import LOCK_PATH, MODEL, PIPELINE, VERSION, sha256, verify_artifact
from .capacity_metrics import GIB, percentile, summarize_samples, validate_run
from .evaluation import (
    API_ROOT,
    DEFAULT_DATASET,
    isolated_settings,
    load_dataset,
    publish_corpus,
    reserve_output,
)
from .local import load_settings
from .tokenization import E5Tokenizer

REPO = API_ROOT.parents[1]


def write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def check_ports(ports: dict[str, int]) -> None:
    if len(set(ports.values())) != len(ports):
        raise ValueError("capacity ports must be distinct")
    sockets = []
    try:
        for port in ports.values():
            sock = socket.socket()
            sockets.append(sock)
            sock.bind(("127.0.0.1", port))
    finally:
        for sock in sockets:
            sock.close()


def directory_bytes(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) if path.exists() else 0


def prepare(base, output: Path, ports: dict[str, int], repeats: int) -> tuple[dict, dict]:
    if not 1 <= repeats <= 100:
        raise ValueError("corpus repeats must be 1..100")
    settings = isolated_settings(base, output, "e5_capacity_" + secrets.token_hex(10))
    directory = output / "model"
    directory.mkdir()
    source = Path(base.assistant_e5_model_dir)
    verify_artifact(source)
    files = json.loads(LOCK_PATH.read_text(encoding="utf-8"))["files"]
    for name in files:
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(source / name, target)
    verify_artifact(directory)
    model_key, qdrant_key, token = (secrets.token_urlsafe(32) for _ in range(3))
    settings = settings.model_copy(
        update={
            "assistant_e5_model_dir": str(directory),
            "assistant_embedding_endpoint": f"http://127.0.0.1:{ports['model']}/v1",
            "assistant_embedding_api_key": model_key,
            "assistant_qdrant_url": f"http://127.0.0.1:{ports['qdrant']}",
            "assistant_qdrant_api_key": qdrant_key,
            "assistant_qdrant_path": None,
            "assistant_qdrant_volume": str(output / "qdrant"),
            "assistant_index_worker_enabled": True,
            "content_write_fence_path": str(output / "content-write.lock"),
        }
    )
    config = {
        "settings": settings.model_dump(mode="json"),
        "ports": ports,
        "model_directory": str(directory),
        "model_key": model_key,
        "qdrant_key": qdrant_key,
        "token": token,
    }
    write_json(output / "config.json", config)
    dataset = load_dataset(DEFAULT_DATASET)
    documents = [d for d in dataset.documents if d.source_type == "article"]
    documents = [
        d.model_copy(
            update={
                "content": "\n\n".join(f"## Section {i + 1}\n\n{d.content}" for i in range(repeats))
            }
        )
        for d in documents
    ]
    documents += [next(d for d in dataset.documents if d.source_type == "profile")]
    publish_corpus(settings, documents)
    corpus = [d.model_dump() for d in documents]
    write_json(output / "corpus.json", corpus)
    return config, {
        "documents": len(documents),
        "article_repetitions": repeats,
        "corpus_sha256": sha256(output / "corpus.json"),
        "source_dataset_sha256": sha256(DEFAULT_DATASET),
    }


def run(output: Path, config: dict, corpus: dict) -> dict:
    from ..config import Settings

    settings = Settings.model_validate(config["settings"])
    code_paths = [
        Path(__file__),
        Path(__file__).with_name("capacity_roles.py"),
        Path(__file__).with_name("capacity_metrics.py"),
        API_ROOT / "scripts/sample-capacity.ps1",
    ]
    code_hashes = {p.name: sha256(p) for p in code_paths}
    database = Database(settings.database_url)
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    node = shutil.which("node")
    if not powershell or not node:
        raise RuntimeError("PowerShell and Node are required")
    qdrant = API_ROOT / "data/qdrant-bin/v1.18.3/qdrant.exe"
    model_python = API_ROOT / "embedding_service/.venv/Scripts/python.exe"
    web_entry = REPO / "apps/web/.output/server/index.mjs"
    for path in (qdrant, model_python, web_entry):
        if not path.is_file():
            raise ValueError("build web output and prepare pinned local model/Qdrant first")
    ports = config["ports"]
    roots: list[dict] = []
    owned: list[subprocess.Popen] = []
    logs = []
    control = {"phase": "cold", "roots": roots, "stop": False}
    control_path = output / "control.json"
    write_json(control_path, control)
    flags = 0x08000000  # Windows CREATE_NO_WINDOW; module is rejected on other platforms.
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GAVIN_", "NUXT_", "QDRANT__"))}
    env.update(
        PYTHONUTF8="1",
        TOKENIZERS_PARALLELISM="false",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_TELEMETRY="1",
    )

    def start(role: str, command: list[str], extra: dict | None = None, cwd: Path = API_ROOT):
        log = (output / f"{role}.log").open("wb")
        logs.append(log)
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env={**env, **(extra or {})},
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=flags,
        )
        owned.append(process)
        if role != "collector":
            roots.append({"role": role, "pid": process.pid})
            write_json(control_path, control)
        return process

    def phase(name: str):
        control["phase"] = name
        write_json(control_path, control)

    api = f"http://127.0.0.1:{ports['api']}"
    model = f"http://127.0.0.1:{ports['model']}"
    web = f"http://127.0.0.1:{ports['web']}"
    headers = {"Authorization": "Bearer " + config["token"]}
    client = httpx.Client(timeout=60, trust_env=False)
    queue_stop = threading.Event()
    queue_samples: list[dict] = []
    queue_thread = None
    collector = None
    loads: dict = {}
    timings = {}
    cleanup = False
    failure = None
    extra: dict = {}

    def ensure_live():
        if any(p.poll() is not None for p in owned):
            raise RuntimeError("owned process exited unexpectedly; inspect local role logs")

    def wait_url(url: str, auth: dict | None = None):
        until = time.monotonic() + 120
        while time.monotonic() < until:
            ensure_live()
            try:
                r = client.get(url, headers=auth)
                if r.is_success:
                    return r
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
        raise RuntimeError("service startup deadline exceeded")

    def rebuild() -> str:
        with database.session_factory() as db:
            operation, _ = request_rebuild(db, idempotency_key=secrets.token_hex(16))
            return operation.operation_id

    def wait_ready(operation_id: str) -> int:
        until = time.monotonic() + 240
        while time.monotonic() < until:
            ensure_live()
            with database.session_factory() as db:
                op = db.get(AssistantIndexCommand, operation_id)
                if op is None:
                    raise RuntimeError("rebuild operation disappeared")
                if op.status == "ready_to_switch":
                    if op.generation_id is None:
                        raise RuntimeError("ready rebuild has no generation")
                    return op.generation_id
                if op.status in ("failed", "waiting", "abandoned"):
                    raise RuntimeError("rebuild failed or waiting")
            time.sleep(0.25)
        raise RuntimeError("rebuild deadline exceeded")

    def finalize(generation: int):
        result = client.post(api + f"/__capacity/finalize/{generation}", headers=headers)
        result.raise_for_status()
        if result.json() != {"gate": "disabled"}:
            raise RuntimeError("runtime gate drift")

    tokenizer = E5Tokenizer(Path(config["model_directory"]))
    dataset = load_dataset(DEFAULT_DATASET)
    short = []
    for q in [q for q in dataset.questions if q.kind == "positive"]:
        text = q.question
        while tokenizer.count("query: " + text) < 32:
            text += " " + q.question
        if tokenizer.count("query: " + text) <= 128:
            short.append(text)
    near = short[0]
    while tokenizer.count("query: " + near + " public") <= 505:
        near += " public"
    write_json(output / "queries.json", {"short": short, "near_limit": near})

    def load(name: str, count: int, period: float, text: str | None = None):
        phase(name)
        rows = []
        for i in range(count):
            ensure_live()
            started = time.monotonic()
            response = client.get(
                api + "/__capacity/query",
                headers=headers,
                params={"question": text or short[i % len(short)]},
            )
            response.raise_for_status()
            row = response.json()
            web_start = time.monotonic()
            page = client.get(web + "/")
            public = client.get(web + "/api/v1/articles")
            row.update(
                web_seconds=time.monotonic() - web_start,
                ok=(
                    row["status"] == "ok"
                    and not row["degraded"]
                    and row["hits"] > 0
                    and page.status_code == 200
                    and public.status_code == 200
                    and not row["chat_called"]
                ),
            )
            rows.append(row)
            time.sleep(max(0, period - (time.monotonic() - started)))
        loads[name] = rows
        write_json(output / "loads.json", loads)

    try:
        # Hardware metadata contains no process command lines or environment values.
        hardware_script = (
            "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); "
            "$cpu=Get-CimInstance Win32_Processor; $os=Get-CimInstance Win32_OperatingSystem; "
            "@{cpu=@($cpu | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors);"
            "os=$os.Caption; total_memory_bytes=[long]$os.TotalVisibleMemorySize*1024} "
            "| ConvertTo-Json"
        )
        hardware = json.loads(
            subprocess.check_output(
                [powershell, "-NoProfile", "-Command", hardware_script], creationflags=flags
            ).decode("utf-8-sig")
        )
        collector = start(
            "collector",
            [
                powershell,
                "-NoProfile",
                "-File",
                str(API_ROOT / "scripts/sample-capacity.ps1"),
                "-Control",
                str(control_path),
                "-Output",
                str(output / "samples.jsonl"),
            ],
        )
        beginning = time.monotonic()
        start(
            "qdrant",
            [str(qdrant)],
            {
                "QDRANT__SERVICE__HOST": "127.0.0.1",
                "QDRANT__SERVICE__HTTP_PORT": str(ports["qdrant"]),
                "QDRANT__SERVICE__GRPC_PORT": str(ports["grpc"]),
                "QDRANT__SERVICE__API_KEY": config["qdrant_key"],
                "QDRANT__SERVICE__MAX_WORKERS": "1",
                "QDRANT__STORAGE__STORAGE_PATH": str(output / "qdrant"),
                "QDRANT__STORAGE__SNAPSHOTS_PATH": str(output / "snapshots"),
                "QDRANT__TELEMETRY_DISABLED": "true",
            },
            cwd=output,
        )
        role_args = [
            "-m",
            "app.local_embedding.capacity_roles",
            "--config",
            str(output / "config.json"),
        ]
        start("model", [str(model_python), *role_args, "--role", "model"])
        start("api", [sys.executable, *role_args, "--role", "api"])
        start(
            "web",
            [node, str(web_entry)],
            {
                "NITRO_HOST": "127.0.0.1",
                "NITRO_PORT": str(ports["web"]),
                "NUXT_API_UPSTREAM": api,
                "NODE_ENV": "production",
            },
        )
        wait_url(f"http://127.0.0.1:{ports['qdrant']}/healthz")
        wait_url(model + "/readyz", {"Authorization": "Bearer " + config["model_key"]})
        wait_url(api + "/api/health")
        wait_url(web + "/")
        start("worker", [sys.executable, *role_args, "--role", "worker"])
        timings["services_ready_seconds"] = time.monotonic() - beginning
        # Ensure cold phase has at least five observed samples even on fast hardware.
        time.sleep(max(0, 8 - timings["services_ready_seconds"]))
        phase("bootstrap")
        first_op = rebuild()
        generation = wait_ready(first_op)
        finalize(generation)
        timings["first_index_ready_seconds"] = time.monotonic() - beginning

        def observe_queue():
            with httpx.Client(timeout=3, trust_env=False) as observer:
                while not queue_stop.is_set():
                    try:
                        response = observer.get(model + "/__capacity/queue")
                        queue_samples.append(
                            {"phase": control["phase"], "waiting": response.json()["waiting"]}
                        )
                    except (httpx.HTTPError, ValueError, KeyError):
                        queue_samples.append({"phase": control["phase"], "waiting": None})
                    queue_stop.wait(0.25)

        queue_thread = threading.Thread(target=observe_queue, daemon=True)
        queue_thread.start()
        # Warm paths before measured steady window.
        client.get(
            api + "/__capacity/query", headers=headers, params={"question": short[0]}
        ).raise_for_status()
        load("steady", 30, 1.0)
        load("near_limit", 10, 1.5, near)
        overlap_started = time.monotonic()
        second_op = rebuild()
        load("rebuild", 45, 1.0)
        second_generation = wait_ready(second_op)
        timings["overlap_window_until_ready_seconds"] = time.monotonic() - overlap_started
        finalize(second_generation)
        phase("affinity_setup")
        latest = json.loads((output / "samples.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        pids = sorted({p["pid"] for p in latest["processes"]})
        affinity_script = (
            "$ErrorActionPreference='Stop'; foreach ($processId in @("
            + ",".join(map(str, pids))
            + ")) { $p=Get-Process -Id $processId; $p.ProcessorAffinity=[IntPtr]3; $p.Dispose() }"
        )
        subprocess.run(
            [powershell, "-NoProfile", "-Command", affinity_script],
            check=True,
            creationflags=flags,
            capture_output=True,
        )
        load("restricted", 30, 1.0)
        phase("disk")
        with database.session_factory() as db:
            generations = list(db.scalars(select(AssistantIndexGeneration)))
            corpus["generations"] = [
                {
                    "id": g.id,
                    "collection": g.collection_name,
                    "status": g.status,
                    "chunks": len(
                        list(
                            db.scalars(
                                select(AssistantChunk.chunk_id).where(
                                    AssistantChunk.generation_id == g.id
                                )
                            )
                        )
                    ),
                }
                for g in generations
            ]
            active_collection = next(g.collection_name for g in generations if g.status == "active")
        response = client.post(
            f"http://127.0.0.1:{ports['qdrant']}/collections/{active_collection}/snapshots",
            headers={"api-key": config["qdrant_key"]},
        )
        response.raise_for_status()
        import sqlite3

        with (
            sqlite3.connect(output / "content.db") as source,
            sqlite3.connect(output / "content-snapshot.db") as target,
        ):
            source.backup(target)
        paths = {
            "model_artifacts": output / "model",
            "api_venv": API_ROOT / ".venv",
            "inference_venv": model_python.parents[1],
            "nuxt_output": web_entry.parents[1],
            "node_executable": Path(node),
            "qdrant_executable": qdrant,
            "content_db": output / "content.db",
            "content_wal": output / "content.db-wal",
            "runtime_db": output / "runtime.db",
            "qdrant_generations": output / "qdrant",
            "qdrant_snapshot": output / "snapshots",
            "content_snapshot": output / "content-snapshot.db",
            "media": output / "media",
        }
        # Include both interpreter installations; their stdlib/runtime is outside the venvs.
        for label, python in (
            ("api_python_runtime", Path(sys.executable)),
            ("inference_python_runtime", model_python),
        ):
            prefix = (
                subprocess.check_output(
                    [str(python), "-c", "import sys; print(sys.base_prefix)"], creationflags=flags
                )
                .decode()
                .strip()
            )
            paths[label] = Path(prefix)
        disk = {name: directory_bytes(path) for name, path in paths.items()}
        disk["run_logs"] = sum(p.stat().st_size for p in output.glob("*.log"))
        extra = {
            "hardware": hardware,
            "disk_bytes": disk,
            "startup": timings,
            "restricted_affinity_mask": 3,
            "restricted_logical_processors": 2,
            "web_entry_sha256": sha256(web_entry),
            "queries_sha256": sha256(output / "queries.json"),
        }
    except Exception as exc:
        failure = type(exc).__name__
        # Detailed exception text remains local; role/config files may contain secrets.
        import traceback

        (output / "failure-trace.txt").write_text(traceback.format_exc(), encoding="utf-8")
    finally:
        queue_stop.set()
        if queue_thread:
            queue_thread.join(timeout=5)
        write_json(output / "queue.json", queue_samples)
        control["stop"] = True
        write_json(control_path, control)
        if collector:
            try:
                collector.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        (output / "stop-worker").touch()
        # Only live handles created by this run are targeted, never port occupants or old PIDs.
        for process in reversed(owned):
            if process.poll() is None:
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    capture_output=True,
                    creationflags=flags,
                )
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    failure = "CleanupTimeout"
        cleanup = all(p.poll() is not None for p in owned)
        if collector and collector.returncode != 0:
            failure = failure or "CollectorFailed"
        for log in logs:
            log.close()
        client.close()
        database.engine.dispose()
    report = {
        "schema_version": 1,
        "created_at": utc_now().isoformat(),
        "scope": "local-Windows-capacity-estimate-no-Chat",
        "model": MODEL,
        "model_version": VERSION,
        "pipeline": PIPELINE,
        "corpus": corpus,
        "collector": "Windows CIM/Get-Process, nominal 1 second, descendant process trees",
        "cold_start_scope": "process start, filesystem caches not flushed",
        "load": "closed-loop single query, nominal 1 request/s plus SSR and article list",
        "code_sha256": code_hashes,
        "cleanup_complete": cleanup,
        "run_valid": False,
        "failure_type": failure,
        "chat_called": False,
        "production_qualified": False,
        "limitations": [
            "Windows-specific measurements; not cloud-vCPU performance",
            "short controlled synthetic load; no endurance or large-corpus proof",
            "system paging includes unrelated background processes",
            "API retrieval benchmark adapter; online Chat/session/checkpoint path not measured",
            "working sets/shared pages/OS cache can overlap in conservative memory estimate",
            "disk uses logical bytes; hardlinked model counted as one deployable artifact set",
        ],
        **extra,
    }
    if failure is None:
        try:
            if code_hashes != {p.name: sha256(p) for p in code_paths}:
                raise RuntimeError("capacity code changed during experiment")
            samples = [
                json.loads(line)
                for line in (output / "samples.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            report["resources"] = summarize_samples(samples)
            report["latency"] = {
                name: {
                    "queries": len(rows),
                    "errors": sum(not r["ok"] for r in rows),
                    "tokens_min": min(r["tokens"] for r in rows),
                    "tokens_max": max(r["tokens"] for r in rows),
                    "embedding_p95_seconds": percentile([r["embedding_seconds"] for r in rows]),
                    "retrieval_p95_seconds": percentile([r["retrieval_seconds"] for r in rows]),
                    "web_pair_p95_seconds": percentile([r["web_seconds"] for r in rows]),
                    "rebuild_overlapping_queries": sum(r["rebuild_active"] for r in rows),
                    "queue_waiting_max": max(
                        [
                            q["waiting"]
                            for q in queue_samples
                            if q["phase"] == name and q["waiting"] is not None
                        ],
                        default=0,
                    ),
                }
                for name, rows in loads.items()
            }
            queue_valid = bool(queue_samples) and all(
                q["waiting"] is not None for q in queue_samples
            )
            report["queue_sampling_valid"] = queue_valid
            report["run_valid"] = validate_run(loads, cleanup) and queue_valid
            report["local_embedding_latency_target_met"] = all(
                report["latency"][p]["embedding_p95_seconds"] <= 2
                for p in ("steady", "rebuild", "restricted")
            )
            total = sum(report["disk_bytes"].values())
            report["disk_estimate"] = {
                "measured_logical_bytes": total,
                "initial_gib_with_30_percent_and_2gib_log_allowance": int(
                    (total * 1.3 + 2 * GIB) // GIB
                )
                + 1,
                "excludes": "future content/media growth and retention beyond two generations "
                "and one snapshot",
            }
        except Exception as exc:
            report["failure_type"] = type(exc).__name__
    write_json(output / "summary.json", report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", default=".env.e5")
    parser.add_argument("--port-base", type=int, default=32400)
    parser.add_argument("--repeats", type=int, default=24)
    args = parser.parse_args(argv)
    if sys.platform != "win32":
        raise ValueError("this collector requires Windows")
    ports = {
        name: args.port_base + i for i, name in enumerate(("web", "api", "model", "qdrant", "grpc"))
    }
    check_ports(ports)
    base = load_settings(args.env_file)
    output = reserve_output(args.output)
    config, corpus = prepare(base, output, ports, args.repeats)
    report = run(output, config, corpus)
    print(
        json.dumps(
            {
                "summary": str(output / "summary.json"),
                "run_valid": report["run_valid"],
                "failure_type": report["failure_type"],
            }
        )
    )
    return 0 if report["run_valid"] and report.get("local_embedding_latency_target_met") else 1


if __name__ == "__main__":
    raise SystemExit(main())
