from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.tools import test_collection
from harness.tools.config import load_config
from harness.tools.module_verification import (
    AUTHORITY_REF,
    CONTRACT_ID,
    ModuleVerificationError,
    case_index,
    contract_digest,
    resolve_module_contract,
    resolve_test_reference,
    validate_module_contract,
)
from harness.tools.test_collection import (
    TestCollectionError as CollectionError,
)
from harness.tools.test_collection import (
    validate_gate_bindings,
)
from harness.verification.checks import module_coverage as module_coverage_check

MODULE_NAMES = {
    "M01": "公开阅读与导航",
    "M02": "文章写作、发布与修订",
    "M03": "栏目、标签与全站搜索",
    "M04": "项目与读书笔记",
    "M05": "媒体与内容可移植性",
    "M06": "认证与个人资料",
    "M07": "内容发现输出",
    "M08": "工程控制面",
    "M09": "公开问答消费层（默认关闭）",
    "M10": "问答运营控制面（默认关闭）",
    "M11": "关于页内容编辑与发布",
}


def _config() -> dict[str, object]:
    return {
        "verification": {
            "gates": {
                "api-tests": {},
                "harness-tests": {},
                "web-quality": {},
                "e2e": {},
            }
        }
    }


def _write_authority(project_root: Path, names: dict[str, str] | None = None) -> None:
    selected = names or MODULE_NAMES
    table = [
        "# 产品基线",
        "",
        "## 当前功能模块与责任映射",
        "",
        "| ID | 模块 | 长期边界 |",
        "| --- | --- | --- |",
        *[
            f"| {module_id} | {selected[module_id]} | test |"
            for module_id in MODULE_NAMES
        ],
        "",
        "## 后续章节",
    ]
    path = project_root / "harness/docs/product/brief.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(table) + "\n", encoding="utf-8")


def _contract() -> dict[str, object]:
    modules: list[dict[str, object]] = []
    for module_id, module_name in MODULE_NAMES.items():
        cases: list[dict[str, object]] = []
        for priority in ("P0", "P1"):
            suffix = priority
            case_id = f"{module_id}-TRACE-{suffix}"
            test_name = f"test_{module_id.lower()}_{priority.lower()}"
            expectation_ids = [f"{case_id}-ALLOW", f"{case_id}-DENY"]
            cases.append(
                {
                    "id": case_id,
                    "priority": priority,
                    "scenario": f"verify {module_id} {priority}",
                    "expectations": [
                        {
                            "id": expectation_ids[0],
                            "surface": "response",
                            "statement": "allowed behavior remains observable",
                        },
                        {
                            "id": expectation_ids[1],
                            "surface": "forbidden",
                            "statement": "forbidden behavior remains blocked",
                        },
                    ],
                    "required_gates": ["harness-tests"],
                    "test_refs": [
                        {
                            "path": "harness/verification/tests/contract_fixture.py",
                            "kind": "pytest",
                            "name": test_name,
                            "gate": "harness-tests",
                            "covers": expectation_ids,
                        }
                    ],
                }
            )
        modules.append({"id": module_id, "name": module_name, "cases": cases})
    return {
        "schema_version": 1,
        "contract_id": CONTRACT_ID,
        "authority_ref": AUTHORITY_REF,
        "modules": modules,
    }


def _write_project(project_root: Path, payload: dict[str, object] | None = None) -> dict[str, object]:
    _write_authority(project_root)
    fixture = project_root / "harness/verification/tests/contract_fixture.py"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    functions = [
        f"def test_{module_id.lower()}_{priority.lower()}():\n    pass\n"
        for module_id in MODULE_NAMES
        for priority in ("P0", "P1")
    ]
    fixture.write_text("\n".join(functions), encoding="utf-8")
    selected = payload or _contract()
    contract_path = (
        project_root
        / "harness/verification/checks/module_coverage.contract.json"
    )
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(
        json.dumps(selected, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return selected


def _collected(payload: dict[str, object]) -> dict[tuple[str, str, str, str], list[dict[str, object]]]:
    index: dict[tuple[str, str, str, str], list[dict[str, object]]] = {}
    for module in payload["modules"]:  # type: ignore[index]
        for case in module["cases"]:  # type: ignore[index]
            for reference in case["test_refs"]:  # type: ignore[index]
                key = (
                    reference["kind"],
                    reference["path"],
                    reference["name"],
                    reference["gate"],
                )
                index.setdefault(key, []).append(
                    {**reference, "node": "fixture", "disabled": []}
                )
    return index


def test_m08_trace_01_complete_contract(tmp_path: Path) -> None:
    payload = _write_project(tmp_path)

    resolved = resolve_module_contract(
        tmp_path,
        registered_gates=set(_config()["verification"]["gates"]),  # type: ignore[index]
        collected_tests=_collected(payload),
    )
    validated, errors = validate_module_contract(
        tmp_path,
        tmp_path / "harness",
        _config(),
        collected_tests=_collected(payload),
    )

    assert errors == []
    assert validated == payload
    assert resolved["counts"] == {
        "modules": 11,
        "cases": 22,
        "expectations": 44,
        "test_refs": 22,
    }
    assert resolved["digest"] == contract_digest(payload)
    assert set(case_index(payload)) == {
        f"{module_id}-TRACE-{priority}"
        for module_id in MODULE_NAMES
        for priority in ("P0", "P1")
    }


def test_m08_trace_02_rejects_authority_drift(tmp_path: Path) -> None:
    payload = _write_project(tmp_path)
    drifted_names = dict(MODULE_NAMES)
    drifted_names["M04"] = "被静默改名的模块"
    _write_authority(tmp_path, drifted_names)

    validated, errors = validate_module_contract(
        tmp_path,
        tmp_path / "harness",
        _config(),
        collected_tests=_collected(payload),
    )

    assert validated == payload
    assert any("M04: name drift" in error for error in errors)
    with pytest.raises(ModuleVerificationError, match="name drift"):
        resolve_module_contract(
            tmp_path,
            registered_gates={"harness-tests"},
            collected_tests=_collected(payload),
        )


def test_m08_trace_03_resolves_references_and_gate_ownership(tmp_path: Path) -> None:
    pytest_path = tmp_path / "apps/api/tests/test_contract_anchor.py"
    pytest_path.parent.mkdir(parents=True, exist_ok=True)
    pytest_path.write_text(
        "def test_exact_anchor():\n    pass\n",
        encoding="utf-8",
    )
    reference = {
        "path": "apps/api/tests/test_contract_anchor.py",
        "kind": "pytest",
        "name": "test_exact_anchor",
        "gate": "api-tests",
        "covers": ["M01-TRACE-P0-ALLOW"],
    }

    resolved = resolve_test_reference(
        tmp_path,
        reference,
        registered_gates={"api-tests", "harness-tests"},
        collected_tests={
            ("pytest", reference["path"], reference["name"], "api-tests"): [
                {**reference, "disabled": []}
            ]
        },
    )
    assert resolved["node"] == (
        "apps/api/tests/test_contract_anchor.py::test_exact_anchor"
    )

    wrong_owner = {**reference, "gate": "harness-tests"}
    with pytest.raises(ModuleVerificationError) as error:
        resolve_test_reference(
            tmp_path,
            wrong_owner,
            registered_gates={"api-tests", "harness-tests"},
            collected_tests={},
        )
    assert any("belongs to api-tests" in detail for detail in error.value.details)

    duplicate_source = (
        "def test_exact_anchor():\n    pass\n\n"
        "def test_exact_anchor():\n    pass\n"
    )
    pytest_path.write_text(duplicate_source, encoding="utf-8")
    with pytest.raises(ModuleVerificationError) as error:
        resolve_test_reference(
            tmp_path,
            reference,
            registered_gates={"api-tests"},
            collected_tests={
                ("pytest", reference["path"], reference["name"], "api-tests"): [
                    {**reference, "disabled": []},
                    {**reference, "disabled": []},
                ]
            },
        )
    assert any("found 2" in detail for detail in error.value.details)


def test_contract_reports_compact_defects(tmp_path: Path) -> None:
    payload = _contract()
    for module in payload["modules"]:  # type: ignore[index]
        module["extra"] = "closed schema rejects this"  # type: ignore[index]
        module["cases"][0]["extra"] = "a second bounded defect"  # type: ignore[index]
    _write_project(tmp_path, payload)
    context = {
        "project_root": tmp_path,
        "harness_root": tmp_path / "harness",
        "config": _config(),
    }

    result = module_coverage_check.run(context)

    assert result["name"] == "module-coverage"
    assert result["passed"] is False
    assert len(result["details"]) == module_coverage_check.MAX_FAILURE_DETAILS + 1
    assert result["details"][-1].endswith("additional defects omitted")
    assert all(len(detail) < 300 for detail in result["details"])


def test_m08_trace_04_documents_verification_case_boundaries() -> None:
    project_root = Path(__file__).resolve().parents[3]
    paths = {
        "brief": project_root / "harness/docs/product/brief.md",
        "policy": project_root / "harness/verification/README.md",
        "template": project_root / "harness/specs/_sdd/template.md",
        "specify": project_root / "harness/workflows/specify.md",
    }
    documents = {
        name: path.read_text(encoding="utf-8") for name, path in paths.items()
    }

    assert all(document.strip() for document in documents.values())
    assert all(
        f"| M{number:02d} |" in documents["brief"] for number in range(1, 12)
    )
    assert "稳定模块 ID" in documents["brief"]

    for name in ("template", "specify"):
        document = documents[name]
        assert "## Verification cases" in document
        assert "M01-SCENARIO-01" in document
        assert "planned" in document
        assert "task verify" in document
    assert "- AC-1 => M01-SCENARIO-01" in documents["template"]

    policy = documents["policy"]
    assert "## Verification cases" in policy
    assert "Specify 阶段只检查" in policy
    assert "task verify 才" in policy
    assert "模块引用校验直接调用 Pytest、Vitest 与 Playwright" in policy
    assert "Reviewer 在每次新增或修改 case 时必须人工逐条检查" in policy
    assert "不证明 scenario" in policy
    assert "不能把测试名、引用存在或总测试数当作语义证明" in policy


def test_contract_is_fail_closed_and_requires_complete_coverage(tmp_path: Path) -> None:
    payload = _contract()
    first_case = payload["modules"][0]["cases"][0]  # type: ignore[index]
    first_case["unexpected"] = True
    first_case["test_refs"][0]["covers"] = [  # type: ignore[index]
        first_case["expectations"][0]["id"]  # type: ignore[index]
    ]
    _write_project(tmp_path, payload)

    _, errors = validate_module_contract(
        tmp_path,
        tmp_path / "harness",
        _config(),
        collected_tests=_collected(payload),
    )

    assert any("unexpected fields unexpected" in error for error in errors)
    assert any("must cover every expectation" in error for error in errors)


def test_contract_rejects_non_baseline_priority_and_unknown_surface(
    tmp_path: Path,
) -> None:
    payload = _contract()
    first_case = payload["modules"][0]["cases"][0]  # type: ignore[index]
    first_case["priority"] = "P2"  # type: ignore[index]
    first_case["expectations"][0]["surface"] = "success"  # type: ignore[index]
    _write_project(tmp_path, payload)

    _, errors = validate_module_contract(
        tmp_path,
        tmp_path / "harness",
        _config(),
        collected_tests=_collected(payload),
    )

    assert any("priority must be P0 or P1" in error for error in errors)
    assert any("surface must be one of" in error for error in errors)


def test_static_typescript_titles_are_exact_and_comments_do_not_count(
    tmp_path: Path,
) -> None:
    path = tmp_path / "apps/web/tests/unit/module-contract.test.ts"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "// it('commented anchor', () => {})\n"
        "it('literal anchor', () => {})\n"
        "test(`template ${variant}`, () => {})\n",
        encoding="utf-8",
    )
    base = {
        "path": "apps/web/tests/unit/module-contract.test.ts",
        "kind": "vitest",
        "gate": "web-quality",
        "covers": ["M01-TRACE-P0-ALLOW"],
    }

    assert resolve_test_reference(
        tmp_path,
        {**base, "name": "literal anchor"},
        registered_gates={"web-quality"},
        collected_tests={
            ("vitest", base["path"], "literal anchor", "web-quality"): [
                {**base, "name": "literal anchor", "disabled": []}
            ]
        },
    )["name"] == "literal anchor"
    for absent in ("commented anchor", "template value"):
        with pytest.raises(ModuleVerificationError, match="found 0"):
            resolve_test_reference(
                tmp_path,
                {**base, "name": absent},
                registered_gates={"web-quality"},
                collected_tests={},
            )


def test_m08_collector_01_rejects_uncollected_disabled_and_gate_drift(
    tmp_path: Path,
) -> None:
    source = tmp_path / "apps/api/tests/test_anchor.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def wrapper():\n    def test_ghost():\n        pass\n",
        encoding="utf-8",
    )
    reference = {
        "path": "apps/api/tests/test_anchor.py",
        "kind": "pytest",
        "name": "test_ghost",
        "gate": "api-tests",
        "covers": ["M08-COLLECTOR-01-E01"],
    }
    with pytest.raises(ModuleVerificationError, match="collected exactly once"):
        resolve_test_reference(
            tmp_path,
            reference,
            registered_gates={"api-tests"},
            collected_tests={},
        )
    with pytest.raises(ModuleVerificationError, match="disabled by skip"):
        resolve_test_reference(
            tmp_path,
            reference,
            registered_gates={"api-tests"},
            collected_tests={
                ("pytest", reference["path"], reference["name"], "api-tests"): [
                    {**reference, "disabled": ["skip"]}
                ]
            },
        )

    for relative, scripts in {
        "package.json": {"quality:web": "drifted", "test:e2e": "drifted"},
        "apps/web/package.json": {
            "test": "drifted",
            "test:e2e": "drifted",
            "test:quality": "drifted",
            "test:failure-states": "drifted",
        },
    }.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"scripts": scripts}), encoding="utf-8")
    with pytest.raises(CollectionError, match="owner gate command drifted"):
        validate_gate_bindings(tmp_path, _config())


def test_vitest_collector_prepares_nuxt_before_listing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "apps/web/tests/unit/collector.test.ts"
    source.parent.mkdir(parents=True)
    source.write_text("test('collector anchor', () => {})\n", encoding="utf-8")
    calls: list[tuple[list[str], Path]] = []

    def run(command: list[str], cwd: Path) -> str:
        calls.append((command, cwd))
        if "vitest" not in command:
            return ""
        return json.dumps(
            [{"name": "suite > collector anchor", "file": str(source.resolve())}]
        )

    monkeypatch.setattr(test_collection, "_run", run)

    rows = test_collection._collect_vitest(tmp_path)

    assert calls == [
        ([test_collection._npm(), "exec", "nuxt", "--", "prepare"], tmp_path / "apps/web"),
        (
            [
                test_collection._npm(),
                "exec",
                "--",
                "vitest",
                "list",
                "--config",
                "vitest.config.ts",
                "--json",
            ],
            tmp_path / "apps/web",
        ),
    ]
    assert rows == [
        {
            "kind": "vitest",
            "gate": "web-quality",
            "path": "apps/web/tests/unit/collector.test.ts",
            "name": "collector anchor",
            "node": "suite > collector anchor",
            "config": "vitest.config.ts", "project": "",
            "title_path": ["suite", "collector anchor"],
            "disabled": [],
        }
    ]


def test_m08_semantics_01_resolves_the_real_repository_contract() -> None:
    project_root = Path(__file__).resolve().parents[3]
    from harness.tools.module_verification import STRUCTURE_ONLY
    config = load_config()
    resolved = resolve_module_contract(
        project_root,
        registered_gates=set(config["verification"]["gates"]),
        config=config,
        collected_tests=STRUCTURE_ONLY,
    )

    assert resolved["counts"]["modules"] == 11
    assert resolved["counts"]["cases"] == len(resolved["case_index"])
    assert resolved["counts"]["test_refs"] >= resolved["counts"]["cases"]


def test_m08_validator_01_rejects_float_schema_and_sanitizes_details(
    tmp_path: Path,
) -> None:
    payload = _write_project(tmp_path)
    payload["schema_version"] = 1.0
    payload["modules"][0]["cases"][0]["priority"] = ["P0"]  # type: ignore[index]
    _write_project(tmp_path, payload)

    _, errors = validate_module_contract(
        tmp_path,
        tmp_path / "harness",
        _config(),
        collected_tests=_collected(payload),
    )
    assert any("schema_version must equal 1" in error for error in errors)
    assert any("priority must be P0 or P1" in error for error in errors)

    compact = module_coverage_check._compact(
        [f"line-{index}\n\x00secret" for index in range(20)]
    )
    assert len(compact) == module_coverage_check.MAX_FAILURE_DETAILS + 1
    assert all("\n" not in detail and "\x00" not in detail for detail in compact)
    assert all(len(detail) <= 280 for detail in compact)
