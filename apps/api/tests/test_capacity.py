from __future__ import annotations

import copy
import json
import socket
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.local_embedding.capacity import check_ports
from app.local_embedding.capacity_metrics import (
    GIB,
    MIB,
    PHASES,
    ROLES,
    summarize_samples,
    validate_run,
)
from app.local_embedding.capacity_roles import create_capacity_api, read_configuration
from app.local_embedding.evaluation import isolated_settings, reserve_output


def samples():
    rows = []
    for phase in sorted(PHASES):
        for _ in range(10):
            t = len(rows) + 1
            rows.append(
                {
                    "timestamp": float(t),
                    "phase": phase,
                    "processes": [
                        {
                            "role": role,
                            "pid": i,
                            "started": "start",
                            "cpu_seconds": t * 0.1,
                            "working_set": 100 * MIB,
                            "private_bytes": 200 * MIB,
                        }
                        for i, role in enumerate(sorted(ROLES))
                    ],
                    "available_bytes": GIB,
                    "committed_bytes": 3 * GIB,
                    "pages_in_per_second": 0,
                    "pages_out_per_second": 0,
                    "system_cpu_percent": 25,
                    "collector_seconds": 0.02,
                    "background_working_set_sum": GIB,
                    "background_private_sum": 2 * GIB,
                }
            )
    return rows


def test_capacity_metrics_require_complete_samples_and_bound_estimates():
    rows = samples()
    result = summarize_samples(rows)
    assert result["working_set_peak_sum_bytes"] == 500 * MIB
    assert result["private_peak_sum_bytes"] == 1000 * MIB
    assert result["headroom_bytes"] == 768 * MIB
    assert result["estimated_memory_gib_range"] == [3, 4]
    assert result["busy_p95_core_equivalent"] == pytest.approx(0.5)
    assert result["same_cpu_logical_core_budget"] == 1
    assert not result["production_qualified"]
    # PID reuse is a new identity, not a large CPU delta from the earlier process.
    reused = copy.deepcopy(rows)
    for row in reused[20:]:
        row["processes"][0]["started"] = "new"
        row["processes"][0]["cpu_seconds"] += 1000
    assert summarize_samples(reused)["busy_p95_core_equivalent"] == pytest.approx(0.5)
    invalid = copy.deepcopy(rows)
    invalid[20]["processes"].pop()
    with pytest.raises(ValueError, match="role disappeared"):
        summarize_samples(invalid)
    invalid = copy.deepcopy(rows)
    invalid[2]["timestamp"] = 1
    with pytest.raises(ValueError, match="non-monotonic"):
        summarize_samples(invalid)
    with pytest.raises(ValueError, match="scenario missing"):
        summarize_samples([r for r in rows if r["phase"] != "cold"])
    invalid = copy.deepcopy(rows)
    invalid[5]["processes"].append(invalid[5]["processes"][0])
    with pytest.raises(ValueError, match="counted twice"):
        summarize_samples(invalid)


def test_capacity_isolation_ports_configuration_and_explicit_api(tmp_path, client, monkeypatch):
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        port = occupied.getsockname()[1]
        with pytest.raises(OSError):
            check_ports({"api": port})
    with pytest.raises(ValueError, match="distinct"):
        check_ports({"api": 40000, "web": 40000})
    with pytest.raises(FileExistsError):
        reserve_output(tmp_path)
    settings = isolated_settings(client.app.state.settings, tmp_path, "capacity_unique")
    config = {"settings": settings.model_dump(mode="json"), "token": "x" * 32}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    assert read_configuration(path)[1].database_url == settings.database_url
    config["settings"]["database_url"] = client.app.state.settings.database_url
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="isolated"):
        read_configuration(path)
    config["settings"]["database_url"] = settings.database_url
    config["settings"]["assistant_online_enabled"] = True
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="online disabled"):
        read_configuration(path)
    # Normal production application does not install the benchmark route.
    assert client.get("/__capacity/query", params={"question": "hello"}).status_code == 404
    import app.assistant_index.retriever as retriever_module
    import app.assistant_index.runtime as runtime_module
    import app.main as main_module
    from app.local_embedding.client import E5Embeddings

    calls = []

    def embed(question):
        calls.append(question)
        return SimpleNamespace(vector=[1.0], input_tokens=34)

    embeddings = object.__new__(E5Embeddings)
    embeddings.prepare_retrieval_query = lambda question, history: (question, False)
    embeddings.embed_query_metered = embed
    runtime = SimpleNamespace(database=client.app.state.database, embeddings=embeddings)
    monkeypatch.setattr(runtime_module, "build_runtime", lambda *args: runtime)
    monkeypatch.setattr(
        retriever_module,
        "retrieve",
        lambda *args, **kwargs: SimpleNamespace(
            status="ok",
            degraded=False,
            candidates=["verified-candidate"],
        ),
    )
    app = create_capacity_api(settings, "x" * 32)
    try:
        with TestClient(app) as benchmark:
            assert (
                benchmark.get("/__capacity/query", params={"question": "hello"}).status_code == 401
            )
            assert benchmark.post("/__capacity/finalize/1").status_code == 401

            def reject_write_fence(*args):
                raise AssertionError("read-only query must not acquire mutation fence")

            monkeypatch.setattr(main_module, "content_write_fence", reject_write_fence)
            response = benchmark.get(
                "/__capacity/query",
                params={"question": "hello"},
                headers={"Authorization": "Bearer " + "x" * 32},
            )
            assert response.status_code == 200 and response.json()["hits"] == 1
            assert response.json()["chat_called"] is False and calls == ["hello"]
    finally:
        app.state.database.engine.dispose()
    with pytest.raises(ValueError, match="development-only"):
        create_capacity_api(settings.model_copy(update={"environment": "production"}), "x" * 32)


def test_capacity_report_rejects_errors_missing_load_and_cleanup_failures():
    loads = {
        name: [{"ok": True, "rebuild_active": name == "rebuild"} for _ in range(10)]
        for name in ("steady", "near_limit", "rebuild", "restricted")
    }
    assert validate_run(loads, True)
    assert not validate_run(loads, False)
    broken = copy.deepcopy(loads)
    broken["steady"][0]["ok"] = False
    assert not validate_run(broken, True)
    broken = copy.deepcopy(loads)
    broken["rebuild"][0]["rebuild_active"] = False
    assert not validate_run(broken, True)
    del broken["near_limit"]
    assert not validate_run(broken, True)
