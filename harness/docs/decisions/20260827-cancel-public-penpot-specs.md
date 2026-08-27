---
id: decision-cancel-public-penpot-specs
level: L1
summary: 取消八个未完成的公开页面 Penpot 对齐规格，并由 Git 历史保留原始设计与验收边界
load_when:
  - architecture-decision
  - penpot
  - public-ui
  - spec-lifecycle
  - task:20260821-penpot-chrome-home
  - task:20260822-penpot-about
  - task:20260822-penpot-archive
  - task:20260822-penpot-articles-index
  - task:20260822-penpot-books-index
  - task:20260822-penpot-projects-index
  - task:20260822-penpot-search
  - task:20260825-article-detail-penpot-alignment
author: Gavin
---

# Decision: cancel the public Penpot alignment specs

## Status

Accepted on 2026-08-27.

## Context

公开站曾建立八个 Penpot 对齐规格，覆盖 Chrome/Home、About、Archive、Articles、Books、Projects、Search 和 Article Detail。用户决定停止该批次，不再继续这些规格。

取消时的 Harness 状态全部为 active 且 evidence invalid：About、Archive、Articles、Books、Projects、Search 没有 task evidence；Chrome/Home 与 Article Detail 仅在本地主工作树存在未跟踪的 failed evidence，分别受未提交源码漂移和风险门禁不匹配阻断。没有一项满足确定性 close 条件。

| Task ID | 取消时状态 |
| --- | --- |
| `20260821-penpot-chrome-home` | active；本地 failed evidence，源码存在未提交漂移 |
| `20260822-penpot-about` | active；evidence missing |
| `20260822-penpot-archive` | active；evidence missing |
| `20260822-penpot-articles-index` | active；evidence missing |
| `20260822-penpot-books-index` | active；evidence missing |
| `20260822-penpot-projects-index` | active；evidence missing |
| `20260822-penpot-search` | active；evidence missing |
| `20260825-article-detail-penpot-alignment` | active；本地 failed evidence，风险推导门禁不完整 |

## Decision

- 从 `harness/specs/active/` 删除上述八个规格，并由生成索引移除开放任务条目。
- 不运行旧任务的 verify/close，不在 `harness/specs/archive/` 创建对应 compressed 记录，不生成 passed evidence 或 `spec.completed` 事件。取消不表示交付完成。
- 原始 spec、实现提交和后续修改继续由当前 Git 历史保存；需要审计时使用对应 task ID 和原路径查询历史，不另建会被误解为已完成的常驻副本。
- 当前主工作树中已有的 Web、E2E、截图、QA 文档和本地 evidence 不随规格删除，也不因本决策获得已验证、可提交或可合入状态。它们必须由后续独立判断保留、重做或回退。
- `20260827-admin-login-penpot-alignment` 不在本次用户指定范围内，继续保持 active。
- 未来若恢复任何公开页面视觉对齐，必须基于当时的产品代码和设计基线创建新的 task/spec；不得恢复旧 task ID 或沿用其失效 evidence。

## Consequences

- 本清理任务关闭后，主项目只剩 1 个 active spec、0 个 frozen spec。
- 根 README 不再声称公开页面 Penpot 批次仍在推进，而是明确该批次已取消、Admin Login 规格仍保留。
- 已实现但未提交或未验证的界面改动成为未绑定工作；删除规格本身不决定这些代码的产品去留。
- 历史提交中的规格文本和设计节点仍可审计，但不代表现行需求或未来验收合同。

## Re-evaluate when

只有在重新确认页面范围、当前实现状态、设计版本、维护成本和验证预算后，才为具体页面建立新的短生命周期规格。不得把本次取消记录解释为对现有未提交 UI 改动的验收。
