from __future__ import annotations

import ast
import contextvars
import hashlib
import json
import re
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from .config import load_config
from .test_collection import TestCollectionError, collect_test_index

STRUCTURE_ONLY = object()
_REFERENCE_PATHS = contextvars.ContextVar('reference_paths', default=None)

SCHEMA_VERSION = 1
CONTRACT_ID = "gavin-module-coverage-v1"
CONTRACT_RELATIVE_PATH = Path(
    "harness/verification/checks/module_coverage.contract.json"
)
AUTHORITY_REF = "harness/docs/product/brief.md#当前功能模块与责任映射"
EXPECTED_MODULE_IDS = tuple(f"M{number:02d}" for number in range(1, 12))

TOP_LEVEL_FIELDS = frozenset(
    {"schema_version", "contract_id", "authority_ref", "modules"}
)
MODULE_FIELDS = frozenset({"id", "name", "cases"})
CASE_FIELDS = frozenset(
    {
        "id",
        "priority",
        "scenario",
        "expectations",
        "required_gates",
        "test_refs",
    }
)
EXPECTATION_FIELDS = frozenset({"id", "surface", "statement"})
REFERENCE_FIELDS = frozenset({"path", "kind", "name", "gate", "covers"})

_MODULE_ID_RE = re.compile(r"M(?:0[1-9]|1[01])\Z")
_SCOPED_ID_RE = re.compile(r"M(?:0[1-9]|1[01])(?:-[A-Z0-9]+)+\Z")
_PRIORITY_RE = re.compile(r"P[01]\Z")
EXPECTATION_SURFACES = frozenset(
    {"response", "state", "side_effect", "user_visible", "forbidden"}
)
_TS_TEST_CALL_RE = re.compile(
    r"(?<![\w$.])(?:test|it)"
    r"(?:\.(?:only|skip|todo|fixme|fail))?\s*\(\s*(['\"`])"
)


class ModuleVerificationError(ValueError):
    """A closed-contract validation failure with machine-readable details."""

    def __init__(self, details: str | Sequence[str]) -> None:
        if isinstance(details, str):
            normalized = [details]
        else:
            normalized = [str(detail) for detail in details if str(detail)]
        if not normalized:
            normalized = ["module verification contract is invalid"]
        self.details = normalized
        super().__init__(normalized[0])


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ModuleVerificationError(f"contract JSON has duplicate field: {key}")
        result[key] = value
    return result


def _inside_project(project_root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(project_root)
    except ValueError:
        return False
    return True


def _resolve_contract_path(
    project_root: Path,
    contract_path: str | Path | None,
) -> Path:
    root = project_root.resolve()
    raw_path = Path(contract_path) if contract_path is not None else CONTRACT_RELATIVE_PATH
    path = raw_path.resolve() if raw_path.is_absolute() else (root / raw_path).resolve()
    if not _inside_project(root, path):
        raise ModuleVerificationError("contract path must stay inside the project")
    return path


def load_module_contract(
    project_root: Path,
    contract_path: str | Path | None = None,
) -> dict[str, Any]:
    """Load the contract with duplicate JSON fields rejected.

    Structural and semantic validation is deliberately handled by
    :func:`validate_module_contract`; this loader only guarantees that callers
    receive a JSON object from a project-local file.
    """

    path = _resolve_contract_path(project_root, contract_path)
    if not path.is_file():
        relative = (
            path.relative_to(project_root.resolve()).as_posix()
            if _inside_project(project_root.resolve(), path)
            else str(path)
        )
        raise ModuleVerificationError(f"module contract is missing: {relative}")
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_json_object,
        )
    except ModuleVerificationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ModuleVerificationError(f"cannot load module contract: {error}") from error
    if not isinstance(payload, dict):
        raise ModuleVerificationError("module contract must be a JSON object")
    return payload


def contract_digest(payload: Mapping[str, Any]) -> str:
    """Return the stable SHA-256 of the contract's canonical JSON form."""

    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def module_contract_digest(payload: Mapping[str, Any]) -> str:
    """Descriptive alias retained for consumers outside the Harness CLI."""

    return contract_digest(payload)


def case_index(payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Index cases by stable ID and retain their module identity.

    This function is intentionally independent of the validator so downstream
    product verification can consume an already-validated payload without
    reparsing source files.
    """

    result: dict[str, dict[str, Any]] = {}
    modules = payload.get("modules", [])
    if not isinstance(modules, list):
        raise ModuleVerificationError("modules must be an array before indexing")
    for module in modules:
        if not isinstance(module, Mapping):
            raise ModuleVerificationError("module entries must be objects before indexing")
        module_id = module.get("id")
        module_name = module.get("name")
        cases = module.get("cases", [])
        if not isinstance(cases, list):
            raise ModuleVerificationError(f"{module_id}: cases must be an array")
        for case in cases:
            if not isinstance(case, Mapping) or not isinstance(case.get("id"), str):
                raise ModuleVerificationError(f"{module_id}: cannot index an invalid case")
            case_id = case["id"]
            if case_id in result:
                raise ModuleVerificationError(f"duplicate case id: {case_id}")
            result[case_id] = {
                "module_id": module_id,
                "module_name": module_name,
                **dict(case),
            }
    return result


def module_case_index(payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Descriptive alias retained for product-verification consumers."""

    return case_index(payload)


def _field_errors(
    value: Any,
    expected: Collection[str],
    label: str,
    errors: list[str],
) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{label}: must be an object")
        return False
    actual = set(value)
    if expected == REFERENCE_FIELDS:
        optional = {"config", "project", "title_path"}
        supplied = actual & optional
        if supplied and supplied != optional:
            errors.append(f"{label}: config, project and title_path must be supplied together")
        if supplied == optional:
            try:
                from .exact_identity import identity
                identity(value)
            except (ValueError, TypeError) as error:
                errors.append(f"{label}: {error}")
        actual -= optional
    missing = sorted(set(expected) - actual)
    unexpected = sorted(actual - set(expected))
    if missing:
        errors.append(f"{label}: missing fields {', '.join(missing)}")
    if unexpected:
        errors.append(f"{label}: unexpected fields {', '.join(unexpected)}")
    return not missing and not unexpected


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _markdown_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _authority_modules(project_root: Path, errors: list[str]) -> dict[str, str]:
    brief_path = (project_root / "harness/docs/product/brief.md").resolve()
    if not _inside_project(project_root.resolve(), brief_path) or not brief_path.is_file():
        errors.append("authority: harness/docs/product/brief.md is missing")
        return {}
    try:
        lines = brief_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        errors.append(f"authority: cannot read product brief: {error}")
        return {}

    heading = "## 当前功能模块与责任映射"
    heading_positions = [index for index, line in enumerate(lines) if line.strip() == heading]
    if len(heading_positions) != 1:
        errors.append(
            "authority: current module heading must occur exactly once "
            f"(found {len(heading_positions)})"
        )
        return {}

    start = heading_positions[0] + 1
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break

    header_index: int | None = None
    id_column: int | None = None
    name_column: int | None = None
    for index in range(start, end):
        line = lines[index].strip()
        if not line.startswith("|"):
            continue
        cells = _markdown_cells(line)
        id_candidates = {"ID", "模块 ID", "模块ID"}
        possible_ids = [position for position, cell in enumerate(cells) if cell in id_candidates]
        possible_names = [position for position, cell in enumerate(cells) if cell == "模块"]
        if len(possible_ids) == 1 and len(possible_names) == 1:
            header_index = index
            id_column = possible_ids[0]
            name_column = possible_names[0]
            break
    if header_index is None or id_column is None or name_column is None:
        errors.append("authority: current module table must contain ID and 模块 columns")
        return {}
    if header_index + 1 >= end:
        errors.append("authority: current module table is missing its separator row")
        return {}
    separator = _markdown_cells(lines[header_index + 1])
    if len(separator) <= max(id_column, name_column) or not all(
        re.fullmatch(r":?-{3,}:?", cell) for cell in separator
    ):
        errors.append("authority: current module table has an invalid separator row")
        return {}

    modules: dict[str, str] = {}
    for line in lines[header_index + 2 : end]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if modules:
                break
            continue
        cells = _markdown_cells(stripped)
        if len(cells) <= max(id_column, name_column):
            errors.append("authority: malformed current module table row")
            continue
        module_id = cells[id_column]
        module_name = cells[name_column]
        if not _MODULE_ID_RE.fullmatch(module_id):
            errors.append(f"authority: invalid module id {module_id or '<empty>'}")
            continue
        if not module_name:
            errors.append(f"authority: {module_id} has an empty module name")
            continue
        if module_id in modules:
            errors.append(f"authority: duplicate module id {module_id}")
            continue
        modules[module_id] = module_name

    expected = set(EXPECTED_MODULE_IDS)
    actual = set(modules)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        fragments = []
        if missing:
            fragments.append(f"missing {', '.join(missing)}")
        if unexpected:
            fragments.append(f"unexpected {', '.join(unexpected)}")
        errors.append(f"authority: module id set drift ({'; '.join(fragments)})")
    return modules


def _safe_reference_path(
    project_root: Path,
    raw_path: Any,
    label: str,
    errors: list[str],
) -> Path | None:
    if not isinstance(raw_path, str):
        errors.append(f"{label}: path must be a string")
        return None
    cache = _REFERENCE_PATHS.get()
    key = (str(project_root), raw_path)
    if cache is not None and key in cache:
        return cache[key]
    if (
        not raw_path
        or "\\" in raw_path
        or raw_path.startswith("/")
        or PurePosixPath(raw_path).is_absolute()
        or any(part in {"", ".", ".."} for part in raw_path.split("/"))
        or ":" in raw_path.split("/", 1)[0]
    ):
        errors.append(f"{label}: path must be a safe project-relative POSIX path")
        return None
    root = project_root.resolve()
    resolved = (root / Path(*raw_path.split("/"))).resolve()
    if not _inside_project(root, resolved):
        errors.append(f"{label}: path must stay inside the project")
        return None
    if not resolved.is_file():
        errors.append(f"{label}: referenced file does not exist: {raw_path}")
        return None
    if cache is not None:
        cache[key] = resolved
    return resolved


def _expected_gate(path: str, kind: str) -> str | None:
    mappings = (
        ("harness-check", "harness/verification/checks/", "harness-integrity"),
        ("pytest", "apps/api/tests/", "api-tests"),
        ("pytest", "harness/verification/tests/", "harness-tests"),
        ("vitest", "apps/web/tests/unit/", "web-quality"),
        ("playwright", "apps/web/tests/quality/", "web-quality"),
        ("playwright", "apps/web/tests/failure/", "web-quality"),
        ("playwright", "apps/web/tests/e2e/", "e2e"),
        ("playwright", "apps/web/tests/e2e-assistant/", "e2e"),
    )
    for expected_kind, prefix, gate in mappings:
        if kind == expected_kind and path.startswith(prefix):
            return gate
    return None


def _pytest_test_names(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as error:
        raise ModuleVerificationError(f"cannot parse pytest file {path.name}: {error}") from error
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test")
    ]


def _without_js_comments(source: str) -> str:
    """Mask JS/TS comments while preserving strings and source positions."""

    output = list(source)
    index = 0
    state = "normal"
    quote = ""
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if state == "normal":
            if char in {"'", '"', "`"}:
                state = "string"
                quote = char
            elif char == "/" and next_char == "/":
                output[index] = output[index + 1] = " "
                index += 1
                state = "line-comment"
            elif char == "/" and next_char == "*":
                output[index] = output[index + 1] = " "
                index += 1
                state = "block-comment"
        elif state == "string":
            if char == "\\":
                index += 1
            elif char == quote:
                state = "normal"
        elif state == "line-comment":
            if char in {"\r", "\n"}:
                state = "normal"
            else:
                output[index] = " "
        elif state == "block-comment":
            output[index] = " "
            if char == "*" and next_char == "/":
                output[index + 1] = " "
                index += 1
                state = "normal"
        index += 1
    return "".join(output)


def _read_js_literal(source: str, quote_position: int) -> str | None:
    quote = source[quote_position]
    content: list[str] = []
    index = quote_position + 1
    while index < len(source):
        char = source[index]
        if char == "\\":
            if index + 1 >= len(source):
                return None
            escaped = source[index + 1]
            translations = {
                "n": "\n",
                "r": "\r",
                "t": "\t",
                "b": "\b",
                "f": "\f",
                "v": "\v",
            }
            content.append(translations.get(escaped, escaped))
            index += 2
            continue
        if char == quote:
            value = "".join(content)
            if quote == "`" and "${" in value:
                return None
            return value
        if char in {"\r", "\n"} and quote != "`":
            return None
        content.append(char)
        index += 1
    return None


def _typescript_test_names(path: Path) -> list[str]:
    try:
        source = _without_js_comments(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        raise ModuleVerificationError(f"cannot read TypeScript test file {path.name}: {error}") from error
    names: list[str] = []
    for match in _TS_TEST_CALL_RE.finditer(source):
        literal = _read_js_literal(source, match.end() - 1)
        if literal is not None:
            names.append(literal)
    return names


def resolve_test_reference(
    project_root: Path,
    reference: Mapping[str, Any],
    *,
    registered_gates: Collection[str],
    collected_tests: Mapping[
        tuple[str, str, str, str], list[dict[str, Any]]
    ] | None = None,
) -> dict[str, Any]:
    """Resolve one reference against tests collected by its owning framework."""

    errors: list[str] = []
    _field_errors(reference, REFERENCE_FIELDS, "test reference", errors)
    raw_path = reference.get("path")
    kind = reference.get("kind")
    name = reference.get("name")
    gate = reference.get("gate")
    path = _safe_reference_path(project_root, raw_path, "test reference", errors)
    if kind not in {"pytest", "vitest", "playwright", "harness-check"}:
        errors.append("test reference: kind must be pytest, vitest, or playwright")
    if not _non_empty_string(name):
        errors.append("test reference: name must be a non-empty string")
    if not _non_empty_string(gate):
        errors.append("test reference: gate must be a non-empty string")
    elif gate not in registered_gates:
        errors.append(f"test reference: unregistered gate {gate}")
    mapped_gate = _expected_gate(raw_path, kind) if isinstance(raw_path, str) and isinstance(kind, str) else None
    if mapped_gate is None and isinstance(raw_path, str) and isinstance(kind, str):
        errors.append(f"test reference: {kind} path has no registered gate ownership: {raw_path}")
    elif mapped_gate is not None and gate != mapped_gate:
        errors.append(
            f"test reference: {raw_path} belongs to {mapped_gate}, not {gate}"
        )
    if kind == "harness-check":
        if not (isinstance(raw_path, str) and raw_path.startswith("harness/verification/checks/")
                and raw_path.endswith(".py") and name == Path(raw_path).stem.replace("_", "-")
                and gate == "harness-integrity"):
            errors.append("invalid structural check reference")
        if errors:
            raise ModuleVerificationError(errors)
        return dict(reference)
    if collected_tests is STRUCTURE_ONLY:
        if errors:
            raise ModuleVerificationError(errors)
        return dict(reference)
    if (
        path is not None
        and kind in {"pytest", "vitest", "playwright"}
        and _non_empty_string(name)
        and _non_empty_string(gate)
    ):
        if collected_tests is None:
            try:
                collected_tests = collect_test_index(project_root, load_config())
            except TestCollectionError as error:
                errors.append(f"test reference: framework collection failed: {error}")
                collected_tests = {}
        matches = collected_tests.get(
            (str(kind), str(raw_path), str(name), str(gate)), []
        )
        if "title_path" in reference:
            from .exact_identity import identity
            matches = [m for m in matches if identity(m) == identity(reference)]
        if len(matches) != 1:
            errors.append(
                f"test reference: {raw_path}::{name} must be collected exactly once "
                f"by {gate} (found {len(matches)})"
            )
        elif matches[0].get("disabled"):
            disabled = ", ".join(str(value) for value in matches[0]["disabled"])
            errors.append(
                f"test reference: {raw_path}::{name} is disabled by {disabled}"
            )
    if errors:
        raise ModuleVerificationError(errors)
    return {
        "path": str(raw_path),
        "kind": str(kind),
        "name": str(name),
        "gate": str(gate),
        "node": f"{raw_path}::{name}",
    }


def _registered_gates(config: Mapping[str, Any] | None, errors: list[str]) -> set[str]:
    if not isinstance(config, Mapping):
        errors.append("config: must be an object")
        return set()
    verification = config.get("verification")
    if not isinstance(verification, Mapping):
        errors.append("config: verification must be an object")
        return set()
    gates = verification.get("gates")
    if not isinstance(gates, Mapping) or not gates:
        errors.append("config: verification.gates must be a non-empty object")
        return set()
    return {str(gate) for gate in gates}


def _validate_payload(
    payload: dict[str, Any],
    project_root: Path,
    registered_gates: set[str],
    collected_tests: Mapping[tuple[str, str, str, str], list[dict[str, Any]]],
) -> list[str]:
    # One structure pass may reference the same file hundreds of times. Cache
    # successful path resolution only within this call; never across mutations,
    # plan/verify/close calls, processes, or execution phases.
    token = _REFERENCE_PATHS.set({})
    try:
        return _validate_payload_with_paths(payload, project_root, registered_gates, collected_tests)
    finally:
        _REFERENCE_PATHS.reset(token)


def _validate_payload_with_paths(
    payload: dict[str, Any],
    project_root: Path,
    registered_gates: set[str],
    collected_tests: Mapping[
        tuple[str, str, str, str], list[dict[str, Any]]
    ],
) -> list[str]:
    errors: list[str] = []
    exact_top = _field_errors(payload, TOP_LEVEL_FIELDS, "contract", errors)
    if type(payload.get("schema_version")) is not int or payload.get(
        "schema_version"
    ) != SCHEMA_VERSION:
        errors.append(f"contract: schema_version must equal {SCHEMA_VERSION}")
    if payload.get("contract_id") != CONTRACT_ID:
        errors.append(f"contract: contract_id must equal {CONTRACT_ID}")
    if payload.get("authority_ref") != AUTHORITY_REF:
        errors.append(f"contract: authority_ref must equal {AUTHORITY_REF}")

    authority = _authority_modules(project_root, errors)
    raw_modules = payload.get("modules") if exact_top else payload.get("modules", [])
    if not isinstance(raw_modules, list):
        errors.append("contract: modules must be an array")
        return errors
    if not raw_modules:
        errors.append("contract: modules must not be empty")

    seen_modules: set[str] = set()
    seen_cases: set[str] = set()
    seen_expectations: set[str] = set()
    contract_modules: dict[str, str] = {}

    for module_position, module in enumerate(raw_modules):
        module_label = f"modules[{module_position}]"
        if not _field_errors(
            module, MODULE_FIELDS, module_label, errors
        ) and not isinstance(module, dict):
            continue
        module_id = module.get("id")
        module_name = module.get("name")
        raw_cases = module.get("cases")
        if not isinstance(module_id, str) or not _MODULE_ID_RE.fullmatch(module_id):
            errors.append(f"{module_label}: id must be one of M01-M11")
            scoped_module_id = f"{module_label}"
        else:
            scoped_module_id = module_id
            if module_id in seen_modules:
                errors.append(f"{module_label}: duplicate module id {module_id}")
            else:
                seen_modules.add(module_id)
                if isinstance(module_name, str):
                    contract_modules[module_id] = module_name
        if not _non_empty_string(module_name):
            errors.append(f"{scoped_module_id}: name must be a non-empty string")
        if not isinstance(raw_cases, list):
            errors.append(f"{scoped_module_id}: cases must be an array")
            continue
        if not raw_cases:
            errors.append(f"{scoped_module_id}: cases must not be empty")

        priorities: set[str] = set()
        for case_position, case in enumerate(raw_cases):
            case_label = f"{scoped_module_id}.cases[{case_position}]"
            if not _field_errors(
                case, CASE_FIELDS, case_label, errors
            ) and not isinstance(case, dict):
                continue
            case_id = case.get("id")
            priority = case.get("priority")
            scenario = case.get("scenario")
            expectations = case.get("expectations")
            required_gates = case.get("required_gates")
            references = case.get("test_refs")

            if not isinstance(case_id, str) or not _SCOPED_ID_RE.fullmatch(case_id):
                errors.append(f"{case_label}: id must be a stable uppercase scoped id")
                scoped_case_id = case_label
            else:
                scoped_case_id = case_id
                if isinstance(module_id, str) and not case_id.startswith(f"{module_id}-"):
                    errors.append(f"{case_id}: id must start with {module_id}-")
                if case_id in seen_cases:
                    errors.append(f"{case_id}: duplicate case id")
                else:
                    seen_cases.add(case_id)
            if not isinstance(priority, str) or not _PRIORITY_RE.fullmatch(priority):
                errors.append(f"{scoped_case_id}: priority must be P0 or P1")
            else:
                priorities.add(priority)
            if not _non_empty_string(scenario):
                errors.append(f"{scoped_case_id}: scenario must be a non-empty string")
            if not isinstance(expectations, list) or not expectations:
                errors.append(f"{scoped_case_id}: expectations must be a non-empty array")
                expectations = []

            expectation_ids: set[str] = set()
            has_forbidden = False
            has_non_forbidden = False
            for expectation_position, expectation in enumerate(expectations):
                expectation_label = (
                    f"{scoped_case_id}.expectations[{expectation_position}]"
                )
                if not _field_errors(
                    expectation,
                    EXPECTATION_FIELDS,
                    expectation_label,
                    errors,
                ) and not isinstance(expectation, dict):
                    continue
                expectation_id = expectation.get("id")
                surface = expectation.get("surface")
                statement = expectation.get("statement")
                if (
                    not isinstance(expectation_id, str)
                    or not _SCOPED_ID_RE.fullmatch(expectation_id)
                ):
                    errors.append(
                        f"{expectation_label}: id must be a stable uppercase scoped id"
                    )
                else:
                    if isinstance(case_id, str) and not expectation_id.startswith(
                        f"{case_id}-"
                    ):
                        errors.append(
                            f"{expectation_id}: id must start with {case_id}-"
                        )
                    if expectation_id in seen_expectations:
                        errors.append(f"{expectation_id}: duplicate expectation id")
                    else:
                        seen_expectations.add(expectation_id)
                    expectation_ids.add(expectation_id)
                if surface not in EXPECTATION_SURFACES:
                    errors.append(
                        f"{expectation_label}: surface must be one of "
                        f"{', '.join(sorted(EXPECTATION_SURFACES))}"
                    )
                elif surface == "forbidden":
                    has_forbidden = True
                else:
                    has_non_forbidden = True
                if not _non_empty_string(statement):
                    errors.append(
                        f"{expectation_label}: statement must be a non-empty string"
                    )
            if not has_forbidden:
                errors.append(f"{scoped_case_id}: requires a forbidden expectation")
            if not has_non_forbidden:
                errors.append(f"{scoped_case_id}: requires a non-forbidden expectation")

            if not isinstance(required_gates, list) or not required_gates:
                errors.append(f"{scoped_case_id}: required_gates must be a non-empty array")
                required_gates = []
            valid_required_gates = [
                gate for gate in required_gates if isinstance(gate, str) and gate
            ]
            if len(valid_required_gates) != len(required_gates):
                errors.append(f"{scoped_case_id}: required_gates entries must be strings")
            if len(valid_required_gates) != len(set(valid_required_gates)):
                errors.append(f"{scoped_case_id}: required_gates must not contain duplicates")
            for gate in sorted(set(valid_required_gates)):
                if gate not in registered_gates:
                    errors.append(f"{scoped_case_id}: unregistered required gate {gate}")

            if not isinstance(references, list) or not references:
                errors.append(f"{scoped_case_id}: test_refs must be a non-empty array")
                references = []
            referenced_gates: set[str] = set()
            covered_expectations: set[str] = set()
            for reference_position, reference in enumerate(references):
                reference_label = f"{scoped_case_id}.test_refs[{reference_position}]"
                if not _field_errors(
                    reference,
                    REFERENCE_FIELDS,
                    reference_label,
                    errors,
                ) and not isinstance(reference, dict):
                    continue
                gate = reference.get("gate")
                covers = reference.get("covers")
                if isinstance(gate, str) and gate:
                    referenced_gates.add(gate)
                if not isinstance(covers, list) or not covers:
                    errors.append(f"{reference_label}: covers must be a non-empty array")
                    covers = []
                valid_covers = [cover for cover in covers if isinstance(cover, str) and cover]
                if len(valid_covers) != len(covers):
                    errors.append(f"{reference_label}: covers entries must be strings")
                if len(valid_covers) != len(set(valid_covers)):
                    errors.append(f"{reference_label}: covers must not contain duplicates")
                unknown = sorted(set(valid_covers) - expectation_ids)
                if unknown:
                    errors.append(
                        f"{reference_label}: covers unknown expectations {', '.join(unknown)}"
                    )
                covered_expectations.update(set(valid_covers) & expectation_ids)
                try:
                    resolve_test_reference(
                        project_root,
                        reference,
                        registered_gates=registered_gates,
                        collected_tests=collected_tests,
                    )
                except ModuleVerificationError as error:
                    errors.extend(f"{reference_label}: {detail}" for detail in error.details)

            if set(valid_required_gates) != referenced_gates:
                errors.append(
                    f"{scoped_case_id}: required_gates must equal test_refs gates "
                    f"(required={','.join(sorted(set(valid_required_gates))) or '-'}; "
                    f"refs={','.join(sorted(referenced_gates)) or '-'})"
                )
            if covered_expectations != expectation_ids:
                missing_coverage = sorted(expectation_ids - covered_expectations)
                errors.append(
                    f"{scoped_case_id}: test_refs must cover every expectation exactly as a union"
                    + (
                        f" (missing {', '.join(missing_coverage)})"
                        if missing_coverage
                        else ""
                    )
                )

        missing_priorities = sorted({"P0", "P1"} - priorities)
        if missing_priorities:
            errors.append(
                f"{scoped_module_id}: cases must include priorities "
                f"{', '.join(missing_priorities)}"
            )

    expected_module_set = set(EXPECTED_MODULE_IDS)
    contract_module_set = set(contract_modules)
    if contract_module_set != expected_module_set:
        missing = sorted(expected_module_set - contract_module_set)
        unexpected = sorted(contract_module_set - expected_module_set)
        fragments = []
        if missing:
            fragments.append(f"missing {', '.join(missing)}")
        if unexpected:
            fragments.append(f"unexpected {', '.join(unexpected)}")
        errors.append(f"contract: module id set drift ({'; '.join(fragments)})")
    if authority:
        for module_id in sorted(expected_module_set & contract_module_set & set(authority)):
            contract_name = contract_modules[module_id]
            authority_name = authority[module_id]
            if contract_name != authority_name:
                errors.append(
                    f"{module_id}: name drift (contract={contract_name!r}; "
                    f"authority={authority_name!r})"
                )
    return errors


def validate_module_contract(
    project_root: Path,
    harness_root: Path | None,
    config: Mapping[str, Any],
    *,
    contract_path: str | Path | None = None,
    collected_tests: Mapping[
        tuple[str, str, str, str], list[dict[str, Any]]
    ] | None = None,
    structure_only: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    """Load and validate the complete contract without hiding any defects.

    ``harness_root`` is accepted as part of the stable Harness check interface;
    all authority and reference paths remain project-relative by design.
    """

    del harness_root
    errors: list[str] = []
    registered_gates = _registered_gates(config, errors)
    if structure_only:
        collected_tests = STRUCTURE_ONLY
    if collected_tests is None:
        try:
            collected_tests = collect_test_index(project_root, config)
        except TestCollectionError as error:
            errors.append(f"test collection: {error}")
            collected_tests = {}
    try:
        payload = load_module_contract(project_root, contract_path)
    except ModuleVerificationError as error:
        errors.extend(error.details)
        return {}, errors
    errors.extend(
        _validate_payload(
            payload,
            project_root.resolve(),
            registered_gates,
            collected_tests,
        )
    )
    return payload, errors


def resolve_module_contract(
    project_root: Path,
    *,
    registered_gates: Collection[str],
    contract_path: str | Path | None = None,
    config: Mapping[str, Any] | None = None,
    collected_tests: Mapping[
        tuple[str, str, str, str], list[dict[str, Any]]
    ] | None = None,
) -> dict[str, Any]:
    """Validate and return a compact, reusable resolved representation."""

    payload = load_module_contract(project_root, contract_path)
    if collected_tests is None:
        try:
            collected_tests = collect_test_index(
                project_root,
                config if config is not None else load_config(),
            )
        except TestCollectionError as error:
            raise ModuleVerificationError(f"test collection: {error}") from error
    errors = _validate_payload(
        payload,
        project_root.resolve(),
        set(registered_gates),
        collected_tests,
    )
    if errors:
        raise ModuleVerificationError(errors)
    indexed_cases = case_index(payload)
    expectation_count = sum(
        len(case["expectations"]) for case in indexed_cases.values()
    )
    reference_count = sum(len(case["test_refs"]) for case in indexed_cases.values())
    return {
        "contract": payload,
        "digest": contract_digest(payload),
        "case_index": indexed_cases,
        "modules": {module["id"]: module for module in payload["modules"]},
        "counts": {
            "modules": len(payload["modules"]),
            "cases": len(indexed_cases),
            "expectations": expectation_count,
            "test_refs": reference_count,
        },
    }


# Concise aliases for consumers that prefer generic loader/resolver names.
load_contract = load_module_contract
resolve_contract = resolve_module_contract
