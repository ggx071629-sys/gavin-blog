---
id: spec-20260812-harness-history-assurance
level: L1
summary: 降低终结 Evolution proposal 路由噪声并显式区分历史 evidence 保证等级
load_when:
  - task:20260812-harness-history-assurance
author: Codex
task_id: 20260812-harness-history-assurance
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - harness/evolution/policy.md
  - harness/verification/README.md
documentation_reason: proposal 路由规则和 evidence 保证等级会改变 Agent 对历史控制面资产的解释方式，必须形成长期合同
state_history:
---

# Context

Evolution 主索引目前列出 45 个 proposal，其中 43 个 `reviewed-no-action`、2 个 `applied`，没有待审 proposal；历史终态占满 L1 路由面。Verification evidence 同时存在 schema v1 与 v2，旧结构检查、旧人工产品报告和当前隔离产品验证都显示为 passed，容易形成保证等级误读。

# Goal

让 Evolution 主索引只暴露政策、历史入口和未终结 proposal，终结 proposal 进入独立生成索引；同时提供只读 evidence inventory，按可复算规则区分当前 v2 产品验证、旧人工产品报告、旧结构检查和无效记录。

# Non-goals

- 不删除、移动或重写历史 proposal、event、archive 或 evidence。
- 不把历史 schema v1 自动升级为 v2，也不声称旧产品报告具有当前证据指纹强度。
- 不自动接受、拒绝或应用 proposal，不让 inventory 触发 Evolution。
- 不实现 agent eval runner、CI provider、远端 dashboard 或历史产品重新验证。

# Acceptance criteria

- AC-1: Evolution 主索引排除 `applied`、`reviewed-no-action` 和 `rejected` proposal，但保留 policy、历史入口与 `proposed`/`accepted` 项；终结记录仍可从独立生成索引发现。
- AC-2: 索引过滤由配置驱动并有测试覆盖，未知/无 status 的普通文档不会被意外隐藏；生成索引保持确定性。
- AC-3: `python -m tools.harness evidence-inventory [--json]` 只读扫描主 evidence，输出每个 task 的 schema、状态、辅助资产和 assurance level，并聚合计数。
- AC-4: assurance 至少区分 `v2-product-verified`、`legacy-product-reported`、`legacy-structure-only` 与 `invalid`；schema v1 即使有人工 application evidence 也不能标为 v2 等价。
- AC-5: 文档明确主路由/历史路由语义、各 assurance level 的事实边界及 inventory 不重新验证历史结果。

# Risks

- 过滤条件错误可能隐藏待审 proposal；只有明确终态可以从主索引排除。
- 旧 evidence 形态不一致；inventory 必须保守分类，解析不确定时标记 invalid，不能猜测通过。
- 独立历史索引仍会很长；它是按需 L2 审计入口，不应从普通任务预加载。

# Verification plan

- harness-tests => AC-1, AC-2, AC-3, AC-4
- harness-integrity => AC-1, AC-2, AC-5
