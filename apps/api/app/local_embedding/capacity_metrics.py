"""Pure calculations for sampled local capacity, never production qualification."""

from __future__ import annotations

import math
from collections import defaultdict

MIB = 1024**2
GIB = 1024**3
ROLES = {"web", "api", "worker", "qdrant", "model"}
PHASES = {"cold", "steady", "near_limit", "rebuild", "restricted"}


def percentile(values: list[float], percent: float = 0.95) -> float:
    if not values:
        raise ValueError("no samples")
    return sorted(values)[max(0, math.ceil(len(values) * percent) - 1)]


def summarize_samples(samples: list[dict]) -> dict:
    if len(samples) < 2:
        raise ValueError("insufficient process samples")
    phases: dict[str, list[dict]] = defaultdict(list)
    peaks: dict[str, dict] = {}
    previous: dict[tuple, float] = {}
    previous_time = None
    for sample in samples:
        current_time = sample["timestamp"]
        if previous_time is not None and current_time <= previous_time:
            raise ValueError("non-monotonic sample timestamp")
        total_ws, total_private, cpu_delta = 0, 0, 0.0
        present = set()
        current = {}
        role_memory: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for row in sample["processes"]:
            role = row["role"]
            if role not in ROLES:
                raise ValueError("unknown process role")
            present.add(role)
            key = (row["pid"], row["started"])
            if key in current:
                raise ValueError("process counted twice")
            current[key] = row["cpu_seconds"]
            if key in previous:
                delta = row["cpu_seconds"] - previous[key]
                if delta < 0:
                    raise ValueError("CPU counter regressed")
                cpu_delta += delta
            total_ws += row["working_set"]
            total_private += row["private_bytes"]
            role_memory[role][0] += row["working_set"]
            role_memory[role][1] += row["private_bytes"]
        for role, (ws, private) in role_memory.items():
            peak = peaks.setdefault(role, {"working_set": 0, "private_bytes": 0})
            peak["working_set"] = max(peak["working_set"], ws)
            peak["private_bytes"] = max(peak["private_bytes"], private)
        phases[sample["phase"]].append(
            {
                "working_set": total_ws,
                "private_bytes": total_private,
                "cores": cpu_delta / (current_time - previous_time) if previous_time else 0,
                "all_roles_present": present == ROLES,
                "interval": current_time - previous_time if previous_time else 0,
                **{
                    k: sample[k]
                    for k in (
                        "available_bytes",
                        "committed_bytes",
                        "pages_in_per_second",
                        "pages_out_per_second",
                        "system_cpu_percent",
                        "collector_seconds",
                        "background_working_set_sum",
                        "background_private_sum",
                    )
                },
            }
        )
        previous, previous_time = current, current_time
    if not PHASES.issubset(phases):
        raise ValueError("required scenario missing")
    if set(peaks) != ROLES:
        raise ValueError("required process role missing")
    result = {}
    for phase in sorted(PHASES):
        rows = phases[phase]
        if len(rows) < 5:
            raise ValueError("scenario has too few samples")
        if phase != "cold" and not all(r["all_roles_present"] for r in rows):
            raise ValueError("required role disappeared during load")
        result[phase] = {
            "samples": len(rows),
            "observed_interval_seconds": sum(r["interval"] for r in rows),
            "sample_interval_p95_seconds": percentile([r["interval"] for r in rows]),
            "working_set_peak_bytes": max(r["working_set"] for r in rows),
            "private_peak_bytes": max(r["private_bytes"] for r in rows),
            "core_equivalent_mean": sum(r["cores"] for r in rows) / len(rows),
            "core_equivalent_p95": percentile([r["cores"] for r in rows]),
            "core_equivalent_peak": max(r["cores"] for r in rows),
            "available_memory_min_bytes": min(r["available_bytes"] for r in rows),
            "system_committed_peak_bytes": max(r["committed_bytes"] for r in rows),
            "system_cpu_p95_percent": percentile([r["system_cpu_percent"] for r in rows]),
            "system_pages_in_p95": percentile([r["pages_in_per_second"] for r in rows]),
            "system_pages_out_p95": percentile([r["pages_out_per_second"] for r in rows]),
            "collector_p95_seconds": percentile([r["collector_seconds"] for r in rows]),
            "background_working_set_sum_peak_bytes": max(
                r["background_working_set_sum"] for r in rows
            ),
            "background_private_sum_peak_bytes": max(r["background_private_sum"] for r in rows),
        }
    ws_envelope = sum(p["working_set"] for p in peaks.values())
    private_envelope = sum(p["private_bytes"] for p in peaks.values())
    baseline = max(ws_envelope, private_envelope)
    headroom = max(math.ceil(baseline * 0.3), 768 * MIB)
    # Explicit assumptions: 0.75–1.5 GiB for OS/cache, in addition to service envelope.
    # Shared pages/cache can be counted twice: this is a conservative planning bound.
    memory_range = [math.ceil((baseline + headroom + os * MIB) / GIB) for os in (768, 1536)]
    busy_p95 = max(result[p]["core_equivalent_p95"] for p in ("steady", "rebuild", "restricted"))
    return {
        "phases": result,
        "role_peaks": peaks,
        "working_set_peak_sum_bytes": ws_envelope,
        "private_peak_sum_bytes": private_envelope,
        "service_envelope_bytes": baseline,
        "headroom_bytes": headroom,
        "assumed_os_cache_mib_range": [768, 1536],
        "estimated_memory_gib_range": memory_range,
        "busy_p95_core_equivalent": busy_p95,
        "assumed_cpu_utilization_target": 0.6,
        "same_cpu_logical_core_budget": max(1, math.ceil(busy_p95 / 0.6)),
        "production_qualified": False,
    }


def validate_run(loads: dict, cleanup: bool) -> bool:
    if not cleanup or not {"steady", "near_limit", "rebuild", "restricted"}.issubset(loads):
        return False
    for rows in loads.values():
        if len(rows) < 10 or any(not r["ok"] for r in rows):
            return False
    return sum(bool(r["rebuild_active"]) for r in loads["rebuild"]) >= 10
