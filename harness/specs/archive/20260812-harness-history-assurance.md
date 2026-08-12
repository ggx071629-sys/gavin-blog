---
id: archive-20260812-harness-history-assurance
level: L2
summary: 降低终结 Evolution proposal 路由噪声并显式区分历史 evidence 保证等级
load_when:
  - task:20260812-harness-history-assurance
author: Codex
task_id: 20260812-harness-history-assurance
status: compressed
documentation_impact: required
documentation_targets:
  - harness/evolution/policy.md
  - harness/verification/README.md
documentation_reason: proposal 路由规则和 evidence 保证等级会改变 Agent 对历史控制面资产的解释方式，必须形成长期合同
state_history:
---

# 20260812-harness-history-assurance

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让 Evolution 主索引只暴露政策、历史入口和未终结 proposal，终结 proposal 进入独立生成索引；同时提供只读 evidence inventory，按可复算规则区分当前 v2 产品验证、旧人工产品报告、旧结构检查和无效记录。

## Acceptance criteria

- AC-1: Evolution 主索引排除 `applied`、`reviewed-no-action` 和 `rejected` proposal，但保留 policy、历史入口与 `proposed`/`accepted` 项；终结记录仍可从独立生成索引发现。
- AC-2: 索引过滤由配置驱动并有测试覆盖，未知/无 status 的普通文档不会被意外隐藏；生成索引保持确定性。
- AC-3: `python -m tools.harness evidence-inventory [--json]` 只读扫描主 evidence，输出每个 task 的 schema、状态、辅助资产和 assurance level，并聚合计数。
- AC-4: assurance 至少区分 `v2-product-verified`、`legacy-product-reported`、`legacy-structure-only` 与 `invalid`；schema v1 即使有人工 application evidence 也不能标为 v2 等价。
- AC-5: 文档明确主路由/历史路由语义、各 assurance level 的事实边界及 inventory 不重新验证历史结果。

## Result

Verified and closed by the harness close command.

## Evidence

[20260812-harness-history-assurance.json](../../verification/evidence/20260812-harness-history-assurance.json)

Closed at 2026-08-12T09:26:35.315079+00:00.
