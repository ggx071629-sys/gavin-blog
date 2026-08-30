from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from . import qualification
from .config import project_root

RUN_SCHEMA_VERSION = 1
OBSERVATION_SCHEMA_VERSION = 1
SUMMARY_SCHEMA_VERSION = 1
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_NETWORK_FILESYSTEMS = frozenset(
    {"nfs", "nfs4", "cifs", "smb", "smb2", "sshfs", "9p", "fuse.sshfs"}
)


class QualificationRunnerError(RuntimeError):
    """A target-runner invariant failed before evidence could be trusted."""


def _canonical_digest(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise QualificationRunnerError(f"qualification artifact cannot be hashed: {path}") from exc
    return "sha256:" + digest.hexdigest()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QualificationRunnerError(f"{label} is unreadable: {path}") from exc
    if not isinstance(payload, dict):
        raise QualificationRunnerError(f"{label} root must be an object")
    return payload


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _exact_fields(payload: dict[str, Any], fields: set[str], label: str) -> None:
    missing = sorted(fields - set(payload))
    extra = sorted(set(payload) - fields)
    if missing or extra:
        parts = []
        if missing:
            parts.append("missing " + ", ".join(missing))
        if extra:
            parts.append("unexpected " + ", ".join(extra))
        raise QualificationRunnerError(f"{label} fields are invalid: {'; '.join(parts)}")


def _timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise QualificationRunnerError(f"{label} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualificationRunnerError(f"{label} is not a valid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise QualificationRunnerError(f"{label} must include an offset")
    return parsed.astimezone(UTC)


def _safe_workspace(path: Path, profile: Any) -> Path:
    resolved = path.resolve()
    approved = Path(profile.storage.paths.qualification_root).resolve()
    if not resolved.is_relative_to(approved):
        raise QualificationRunnerError("workspace must be beneath the approved qualification_root")
    repository = project_root().resolve()
    if resolved == repository or resolved.is_relative_to(repository):
        raise QualificationRunnerError("qualification workspace must remain outside the Git checkout")
    return resolved


def _configured_inputs(task_id: str) -> tuple[Path, Path]:
    config = qualification.load_config()
    definition = qualification._task_config(task_id, config)
    if definition is None:
        raise QualificationRunnerError("task has no configured qualification inputs")
    return (
        qualification._configured_path(definition["profile"], "qualification profile"),
        qualification._configured_path(definition["case_suite"], "qualification case suite"),
    )


def _load_profile(path: Path) -> Any:
    api_root = project_root() / "apps" / "api"
    import sys

    added = str(api_root) not in sys.path
    if added:
        sys.path.insert(0, str(api_root))
    try:
        from app.assistant_qualification.profile import load_profile

        return load_profile(path)
    finally:
        if added:
            sys.path.remove(str(api_root))


def _suite(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]], str]:
    payload = _read_json(path, "qualification case suite")
    try:
        digest, contracts = qualification._case_suite(path)
    except (OSError, ValueError) as exc:
        raise QualificationRunnerError(str(exc)) from exc
    cases: dict[str, dict[str, Any]] = {}
    for raw in payload["cases"]:
        case_id = raw["case_id"]
        cases[case_id] = {
            **contracts[case_id],
            "mode": raw["mode"],
            "billable": raw["billable"],
            "destructive_isolation": raw["destructive_isolation"],
            "depends_on": list(raw["depends_on"]),
        }
    return payload, cases, digest


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=project_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise QualificationRunnerError(result.stderr.strip() or "target Git check failed")
    return result.stdout.strip()


def _source_commit(*, require_clean: bool) -> str:
    commit = _git("rev-parse", "HEAD")
    if _COMMIT_RE.fullmatch(commit) is None:
        raise QualificationRunnerError("target source commit is not a full Git SHA")
    if require_clean and _git("status", "--porcelain", "--untracked-files=no"):
        raise QualificationRunnerError("target checkout has tracked source drift")
    return commit


def _effective_cpu_cores() -> int:
    values = [len(os.sched_getaffinity(0))] if hasattr(os, "sched_getaffinity") else []
    host = os.cpu_count()
    if host:
        values.append(host)
    cpu_max = Path("/sys/fs/cgroup/cpu.max")
    if cpu_max.is_file():
        try:
            quota, period = cpu_max.read_text(encoding="utf-8").strip().split()
            if quota != "max":
                values.append(max(1, int(quota) // int(period)))
        except (OSError, ValueError, ZeroDivisionError):
            pass
    if not values:
        raise QualificationRunnerError("target CPU allocation cannot be observed")
    return min(value for value in values if value > 0)


def _host_memory_bytes() -> int:
    if os.name == "nt":
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise QualificationRunnerError("target physical memory cannot be observed")
        return int(status.total_physical)
    page_size = os.sysconf("SC_PAGE_SIZE")
    pages = os.sysconf("SC_PHYS_PAGES")
    return int(page_size * pages)


def _effective_memory_bytes() -> int:
    values = [_host_memory_bytes()]
    memory_max = Path("/sys/fs/cgroup/memory.max")
    if memory_max.is_file():
        try:
            raw = memory_max.read_text(encoding="utf-8").strip()
            if raw != "max":
                values.append(int(raw))
        except (OSError, ValueError):
            pass
    return min(value for value in values if value > 0)


def _os_facts() -> tuple[str, str]:
    release_path = Path("/etc/os-release")
    if release_path.is_file():
        values: dict[str, str] = {}
        for line in release_path.read_text(encoding="utf-8").splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"')
        return values.get("NAME", platform.system()), values.get(
            "VERSION_ID", platform.release()
        )
    return platform.system(), platform.version()


def _filesystem_type(path: Path) -> str:
    resolved = path.resolve()
    if os.name == "nt":
        import ctypes

        root = Path(resolved.anchor)
        filesystem = ctypes.create_unicode_buffer(64)
        ok = ctypes.windll.kernel32.GetVolumeInformationW(
            str(root), None, 0, None, None, None, filesystem, len(filesystem)
        )
        if not ok:
            raise QualificationRunnerError("target filesystem cannot be observed")
        return filesystem.value.lower()
    mountinfo = Path("/proc/self/mountinfo")
    if not mountinfo.is_file():
        raise QualificationRunnerError("target mount table is unavailable")
    best: tuple[int, str] | None = None
    for line in mountinfo.read_text(encoding="utf-8").splitlines():
        before, separator, after = line.partition(" - ")
        if not separator:
            continue
        fields = before.split()
        post = after.split()
        if len(fields) < 5 or not post:
            continue
        mount = Path(fields[4].replace("\\040", " "))
        try:
            resolved.relative_to(mount)
        except ValueError:
            continue
        candidate = (len(str(mount)), post[0].lower())
        if best is None or candidate[0] > best[0]:
            best = candidate
    if best is None:
        raise QualificationRunnerError("target filesystem mount cannot be resolved")
    return best[1]


def observe_target(profile: Any) -> dict[str, Any]:
    storage_paths = {
        name: Path(str(getattr(profile.storage.paths, name))).resolve()
        for name in profile.storage.paths.__class__.model_fields
    }
    missing = sorted(name for name, path in storage_paths.items() if not path.exists())
    if missing:
        raise QualificationRunnerError(
            "approved target storage paths do not exist: " + ", ".join(missing)
        )
    filesystems = {name: _filesystem_type(path) for name, path in storage_paths.items()}
    network = sorted(
        name for name, filesystem in filesystems.items() if filesystem in _NETWORK_FILESYSTEMS
    )
    if network:
        raise QualificationRunnerError(
            "network/shared filesystems are forbidden: " + ", ".join(network)
        )
    if set(filesystems.values()) != {profile.host.filesystem_type}:
        raise QualificationRunnerError("target storage filesystem differs from the profile")
    cpu_cores = _effective_cpu_cores()
    memory_bytes = _effective_memory_bytes()
    observed_memory_mib = memory_bytes // (1024 * 1024)
    if cpu_cores != profile.host.cpu_cores:
        raise QualificationRunnerError("target effective CPU allocation is not 2 vCPU")
    if not 3_840 <= observed_memory_mib <= 4_352:
        raise QualificationRunnerError("target effective memory is not a 4 GiB allocation")
    os_name, os_version = _os_facts()
    architecture = platform.machine().lower()
    aliases = {"amd64": "x86_64", "arm64": "aarch64"}
    architecture = aliases.get(architecture, architecture)
    if architecture != profile.host.architecture:
        raise QualificationRunnerError("target architecture differs from the profile")
    approved_os = profile.host.os_name.lower()
    observed_os = os_name.lower()
    if approved_os not in observed_os and observed_os not in approved_os:
        raise QualificationRunnerError("target OS name differs from the profile")
    if os_version != profile.host.os_version:
        raise QualificationRunnerError("target OS version differs from the profile")
    return {
        "observed_at": datetime.now(UTC).isoformat(),
        "effective_cpu_cores": cpu_cores,
        "effective_memory_bytes": memory_bytes,
        "os_name": os_name,
        "os_version": os_version,
        "architecture": architecture,
        "filesystems": filesystems,
        "network_filesystem_detected": False,
        "host_identifier_retained": False,
        "ip_address_retained": False,
    }


def _validate_target_observation(observed: dict[str, Any], profile: Any) -> None:
    _exact_fields(
        observed,
        {
            "observed_at",
            "effective_cpu_cores",
            "effective_memory_bytes",
            "os_name",
            "os_version",
            "architecture",
            "filesystems",
            "network_filesystem_detected",
            "host_identifier_retained",
            "ip_address_retained",
        },
        "target observation",
    )
    _timestamp(observed["observed_at"], "target observed_at")
    if observed["effective_cpu_cores"] != 2:
        raise QualificationRunnerError("target observation is not the real 2 vCPU allocation")
    memory = observed["effective_memory_bytes"]
    if not isinstance(memory, int) or not 3_840 * 1024**2 <= memory <= 4_352 * 1024**2:
        raise QualificationRunnerError("target observation is not the real 4 GiB allocation")
    for field, expected in (
        ("os_version", profile.host.os_version),
        ("architecture", profile.host.architecture),
    ):
        if observed[field] != expected:
            raise QualificationRunnerError(f"target observed {field} differs from profile")
    observed_os = str(observed["os_name"]).lower()
    approved_os = profile.host.os_name.lower()
    if observed_os not in approved_os and approved_os not in observed_os:
        raise QualificationRunnerError("target observed OS differs from profile")
    filesystems = observed["filesystems"]
    if not isinstance(filesystems, dict) or not filesystems:
        raise QualificationRunnerError("target filesystem observations are missing")
    if set(filesystems.values()) != {profile.host.filesystem_type}:
        raise QualificationRunnerError("target observed filesystem differs from profile")
    if any(
        observed[field] is not False
        for field in (
            "network_filesystem_detected",
            "host_identifier_retained",
            "ip_address_retained",
        )
    ):
        raise QualificationRunnerError("target observation violates privacy or local-disk policy")


def initialize_run(
    *,
    task_id: str,
    artifact_path: Path,
    workspace: Path,
    now: datetime | None = None,
    source_commit: str | None = None,
    require_clean: bool = True,
    target_observation: dict[str, Any] | None = None,
) -> Path:
    profile_path, suite_path = _configured_inputs(task_id)
    profile = _load_profile(profile_path)
    profile_hash = qualification._profile_digest(profile_path)
    workspace = _safe_workspace(workspace, profile)
    run_path = workspace / "run.json"
    if run_path.exists():
        raise QualificationRunnerError("qualification workspace is already initialized")
    if not artifact_path.is_file():
        raise QualificationRunnerError("immutable deployment artifact manifest is missing")
    _, _, suite_hash = _suite(suite_path)
    commit = source_commit or _source_commit(require_clean=require_clean)
    if _COMMIT_RE.fullmatch(commit) is None:
        raise QualificationRunnerError("source_commit must be a full lowercase Git SHA")
    observed = target_observation or observe_target(profile)
    _validate_target_observation(observed, profile)
    current = (now or datetime.now(UTC)).astimezone(UTC)
    run = {
        "schema_version": RUN_SCHEMA_VERSION,
        "task_id": task_id,
        "status": "collecting",
        "source_commit": commit,
        "artifact_digest": _file_digest(artifact_path),
        "profile_digest": profile_hash,
        "case_suite_digest": suite_hash,
        "started_at": current.isoformat(),
        "target_observation_digest": _canonical_digest(observed),
    }
    workspace.mkdir(parents=True, exist_ok=True)
    _atomic_json(workspace / "target-observation.json", observed)
    (workspace / "cases").mkdir(exist_ok=True)
    _atomic_json(run_path, run)
    return run_path


def _load_run(workspace: Path) -> dict[str, Any]:
    run = _read_json(workspace / "run.json", "qualification run")
    _exact_fields(
        run,
        {
            "schema_version",
            "task_id",
            "status",
            "source_commit",
            "artifact_digest",
            "profile_digest",
            "case_suite_digest",
            "started_at",
            "target_observation_digest",
        },
        "qualification run",
    )
    if run["schema_version"] != RUN_SCHEMA_VERSION or run["status"] != "collecting":
        raise QualificationRunnerError("qualification run is not collecting evidence")
    for field in ("artifact_digest", "profile_digest", "case_suite_digest"):
        if not isinstance(run[field], str) or _DIGEST_RE.fullmatch(run[field]) is None:
            raise QualificationRunnerError(f"qualification run {field} is invalid")
    _timestamp(run["started_at"], "qualification run started_at")
    return run


def _case_results(workspace: Path) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for path in sorted((workspace / "cases").glob("*.json")):
        result = _read_json(path, "case result")
        case_id = result.get("case_id")
        if not isinstance(case_id, str) or case_id in results:
            raise QualificationRunnerError("case result IDs are invalid or duplicated")
        results[case_id] = result
    return results


def _dependency_ancestors(case_id: str, suite: dict[str, dict[str, Any]]) -> set[str]:
    ancestors: set[str] = set()
    pending = list(suite[case_id]["depends_on"])
    while pending:
        dependency = pending.pop()
        if dependency in ancestors:
            continue
        ancestors.add(dependency)
        pending.extend(suite[dependency]["depends_on"])
    return ancestors


def record_case(
    *,
    workspace: Path,
    observation_path: Path,
    enforce_source: bool = True,
) -> Path:
    workspace = workspace.resolve()
    run = _load_run(workspace)
    if enforce_source and (
        _source_commit(require_clean=True) != run["source_commit"]
    ):
        raise QualificationRunnerError("target source changed during qualification")
    profile_path, suite_path = _configured_inputs(run["task_id"])
    if qualification._profile_digest(profile_path) != run["profile_digest"]:
        raise QualificationRunnerError("qualification profile drifted during the target run")
    _, suite, suite_hash = _suite(suite_path)
    if suite_hash != run["case_suite_digest"]:
        raise QualificationRunnerError("qualification case suite drifted during the target run")
    observation = _read_json(observation_path, "case observation")
    _exact_fields(
        observation,
        {
            "schema_version",
            "case_id",
            "status",
            "reviewer",
            "reviewed_at",
            "artifact_records",
        },
        "case observation",
    )
    if observation["schema_version"] != OBSERVATION_SCHEMA_VERSION:
        raise QualificationRunnerError("case observation schema is unsupported")
    case_id = observation.get("case_id")
    if not isinstance(case_id, str) or case_id not in suite:
        raise QualificationRunnerError("case observation does not belong to the versioned suite")
    output = workspace / "cases" / f"{case_id}.json"
    if output.exists():
        raise QualificationRunnerError("case result already exists and cannot be overwritten")
    status, blocker = qualification._validate_status(
        observation.get("status"), f"case {case_id} status"
    )
    existing = _case_results(workspace)
    dependencies = suite[case_id]["depends_on"]
    missing_dependencies = [value for value in dependencies if value not in existing]
    if missing_dependencies:
        raise QualificationRunnerError(
            f"case {case_id} dependencies are not yet recorded: {missing_dependencies}"
        )
    failed_dependencies = [
        value for value in dependencies if existing[value]["status"] != "pass"
    ]
    if failed_dependencies and status != "blocked_by":
        raise QualificationRunnerError(
            f"case {case_id} must be blocked by a failed direct dependency"
        )
    if status == "blocked_by":
        if blocker not in _dependency_ancestors(case_id, suite):
            raise QualificationRunnerError(
                f"case {case_id} blocker must be a suite dependency ancestor"
            )
        if existing[blocker]["status"] != "measured_fail":
            raise QualificationRunnerError(
                f"case {case_id} blocker must be a directly measured failure"
            )
    reviewer = observation.get("reviewer")
    if not isinstance(reviewer, str) or len(reviewer.strip()) < 2:
        raise QualificationRunnerError("case reviewer is required")
    reviewed_at = _timestamp(observation.get("reviewed_at"), "case reviewed_at")
    if reviewed_at < _timestamp(run["started_at"], "qualification started_at"):
        raise QualificationRunnerError("case review predates qualification start")
    artifact_records = observation.get("artifact_records")
    if not isinstance(artifact_records, list) or not artifact_records:
        raise QualificationRunnerError("case observation requires reviewed raw artifacts")
    final_artifacts = []
    artifact_hashes = []
    for index, raw in enumerate(artifact_records, start=1):
        if not isinstance(raw, dict):
            raise QualificationRunnerError("case artifact record must be an object")
        _exact_fields(
            raw,
            {
                "artifact_id",
                "kind",
                "path",
                "location_category",
                "retention_days",
                "reviewed",
            },
            f"case artifact {index}",
        )
        path = Path(str(raw["path"])).resolve()
        if path == project_root().resolve() or path.is_relative_to(project_root().resolve()):
            raise QualificationRunnerError("raw qualification artifacts cannot live in Git")
        digest = _file_digest(path)
        if raw["location_category"] not in {
            "encrypted-off-host-object-store",
            "encrypted-off-host-filesystem",
        }:
            raise QualificationRunnerError("raw artifact is not in an approved off-host class")
        if raw["reviewed"] is not True:
            raise QualificationRunnerError("raw artifact must be reviewed before case recording")
        if not isinstance(raw["retention_days"], int) or raw["retention_days"] < 1:
            raise QualificationRunnerError("raw artifact retention is invalid")
        for field in ("artifact_id", "kind"):
            if not isinstance(raw[field], str) or not raw[field].strip():
                raise QualificationRunnerError(f"raw artifact {field} is invalid")
        artifact_hashes.append(digest)
        final_artifacts.append(
            {
                "artifact_id": raw["artifact_id"],
                "kind": raw["kind"],
                "sha256": digest,
                "location_category": raw["location_category"],
                "retention_days": raw["retention_days"],
                "reviewed": True,
            }
        )
    result = {
        "case_id": case_id,
        "suite_version": suite[case_id]["suite_version"],
        "status": observation["status"],
        "category": suite[case_id]["category"],
        "classification": suite[case_id]["classification"],
        "reviewer": reviewer.strip(),
        "reviewed_at": reviewed_at.isoformat(),
        "artifact_hashes": sorted(set(artifact_hashes)),
        "artifacts": final_artifacts,
    }
    _atomic_json(output, result)
    return output


def _provider_matches_profile(provider: dict[str, Any], profile: Any) -> None:
    if provider.get("real_provider") is not True:
        raise QualificationRunnerError("provider summary must represent the final real provider")
    pairs = (
        (provider.get("chat", {}).get("provider"), profile.providers.chat.provider, "Chat provider"),
        (provider.get("chat", {}).get("model"), profile.providers.chat.model, "Chat model"),
        (
            provider.get("chat", {}).get("version"),
            profile.providers.chat.model_version,
            "Chat version",
        ),
        (
            provider.get("chat", {}).get("input_price_micro_cny_per_million"),
            profile.providers.chat.input_price_micro_cny_per_million,
            "Chat input price",
        ),
        (
            provider.get("chat", {}).get("output_price_micro_cny_per_million"),
            profile.providers.chat.output_price_micro_cny_per_million,
            "Chat output price",
        ),
        (
            provider.get("embedding", {}).get("provider"),
            profile.providers.embedding.provider,
            "Embedding provider",
        ),
        (
            provider.get("embedding", {}).get("model"),
            profile.providers.embedding.model,
            "Embedding model",
        ),
        (
            provider.get("embedding", {}).get("version"),
            profile.providers.embedding.model_version,
            "Embedding version",
        ),
        (
            provider.get("embedding", {}).get("dimension"),
            profile.providers.embedding.dimension,
            "Embedding dimension",
        ),
        (
            provider.get("embedding", {}).get("input_price_micro_cny_per_million"),
            profile.providers.embedding.input_price_micro_cny_per_million,
            "Embedding input price",
        ),
    )
    for actual, expected, label in pairs:
        if actual != expected:
            raise QualificationRunnerError(f"{label} drifted from the approved profile")


def _generation_matches_profile(generation: dict[str, Any], profile: Any) -> None:
    generation_id = generation.get("id")
    expected = {
        "collection": f"{profile.qdrant.collection_prefix}_{generation_id}",
        "dimension": profile.qdrant.vector_dimension,
        "distance": profile.qdrant.distance,
        "pipeline_version": profile.qdrant.pipeline_version,
    }
    for field, value in expected.items():
        if generation.get(field) != value:
            raise QualificationRunnerError(f"active generation {field} drifted from profile")


def assemble_manifest(
    *,
    workspace: Path,
    summary_path: Path,
    output_path: Path,
    enforce_source: bool = True,
) -> Path:
    workspace = workspace.resolve()
    run = _load_run(workspace)
    if enforce_source and (
        _source_commit(require_clean=True) != run["source_commit"]
    ):
        raise QualificationRunnerError("target source changed before manifest assembly")
    profile_path, suite_path = _configured_inputs(run["task_id"])
    if qualification._profile_digest(profile_path) != run["profile_digest"]:
        raise QualificationRunnerError("qualification profile drifted before assembly")
    _, suite, suite_hash = _suite(suite_path)
    if suite_hash != run["case_suite_digest"]:
        raise QualificationRunnerError("qualification case suite drifted before assembly")
    profile = _load_profile(profile_path)
    workspace = _safe_workspace(workspace, profile)
    target_observation = _read_json(
        workspace / "target-observation.json", "target observation"
    )
    if _canonical_digest(target_observation) != run["target_observation_digest"]:
        raise QualificationRunnerError("target observation was modified after initialization")
    case_results = _case_results(workspace)
    if set(case_results) != set(suite):
        missing = sorted(set(suite) - set(case_results))
        extra = sorted(set(case_results) - set(suite))
        raise QualificationRunnerError(
            f"qualification cases are incomplete: missing={missing}; unexpected={extra}"
        )
    summary = _read_json(summary_path, "qualification summary")
    _exact_fields(
        summary,
        {
            "schema_version",
            "completed_at",
            "provider",
            "active_generation",
            "switches",
            "qualification_usage",
            "results",
            "operator",
        },
        "qualification summary",
    )
    if summary["schema_version"] != SUMMARY_SCHEMA_VERSION:
        raise QualificationRunnerError("qualification summary schema is unsupported")
    completed = _timestamp(summary["completed_at"], "qualification completed_at")
    started = _timestamp(run["started_at"], "qualification started_at")
    if completed < started:
        raise QualificationRunnerError("qualification completion predates start")
    provider = summary["provider"]
    generation = summary["active_generation"]
    if not isinstance(provider, dict) or not isinstance(generation, dict):
        raise QualificationRunnerError("provider and generation summaries must be objects")
    _provider_matches_profile(provider, profile)
    _generation_matches_profile(generation, profile)
    usage = summary["qualification_usage"]
    if not isinstance(usage, dict):
        raise QualificationRunnerError("qualification usage must be an object")
    budgets = profile.providers.budgets
    if usage.get("max_calls") != budgets.qualification_max_calls or usage.get(
        "max_micro_cny"
    ) != budgets.qualification_max_micro_cny:
        raise QualificationRunnerError("qualification usage envelope drifted from profile")
    cases = []
    artifacts_by_id: dict[str, dict[str, Any]] = {}
    for case_id in suite:
        stored = case_results[case_id]
        artifacts = stored.pop("artifacts", None)
        if not isinstance(artifacts, list) or not artifacts:
            raise QualificationRunnerError(f"case {case_id} has no artifact registry")
        cases.append(stored)
        for artifact in artifacts:
            previous = artifacts_by_id.get(artifact["artifact_id"])
            if previous is not None and previous != artifact:
                raise QualificationRunnerError("artifact ID collision has inconsistent facts")
            artifacts_by_id[artifact["artifact_id"]] = artifact
    results_summary = summary["results"]
    if not isinstance(results_summary, dict):
        raise QualificationRunnerError("qualification results must be an object")
    has_failure = any(case["status"] != "pass" for case in cases) or any(
        not isinstance(result, dict) or result.get("status") != "pass"
        for result in results_summary.values()
    )
    state = "QUALIFICATION_NO_GO" if has_failure else "QUALIFICATION_GO_CANDIDATE"
    target = {
        "real_target": True,
        "cpu_cores": profile.host.cpu_cores,
        "memory_mib": profile.host.memory_mib,
        "os_name": profile.host.os_name,
        "os_version": profile.host.os_version,
        "architecture": profile.host.architecture,
        "filesystem": profile.host.filesystem_type,
        "deployment_kind": profile.host.deployment_kind,
        "host_class": f"single-host-2vcpu-4g:{profile.profile_id}",
    }
    manifest = {
        "schema_version": qualification.MANIFEST_SCHEMA_VERSION,
        "task_id": run["task_id"],
        "qualification_state": state,
        "source_commit": run["source_commit"],
        "artifact_digest": run["artifact_digest"],
        "profile_digest": run["profile_digest"],
        "case_suite_digest": run["case_suite_digest"],
        "started_at": started.isoformat(),
        "completed_at": completed.isoformat(),
        "expires_at": (completed + timedelta(seconds=profile.evidence.ttl_seconds)).isoformat(),
        "invalidation_paths": sorted(profile.evidence.invalidation_paths),
        "target": target,
        "provider": provider,
        "active_generation": generation,
        "switches": summary["switches"],
        "qualification_usage": usage,
        "results": summary["results"],
        "cases": cases,
        "artifacts": sorted(artifacts_by_id.values(), key=lambda item: item["artifact_id"]),
        "operator": summary["operator"],
    }
    try:
        qualification._validate_manifest_structure(
            {
                **manifest,
                "signature": {
                    "key_id": "unsigned-target-run",
                    "algorithm": qualification.ALGORITHM,
                    "value": "AA",
                },
            }
        )
    except ValueError as exc:
        raise QualificationRunnerError(f"assembled qualification manifest is invalid: {exc}") from exc
    _atomic_json(output_path, manifest)
    return output_path
