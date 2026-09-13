---
id: archive-20260827-externalize-retired-github-specs
level: L2
summary: 将两份未完成的 GitHub 知识孵化规格从主项目开放列表迁出，并以独立只读归档保留原始基线
load_when:
  - task:20260827-externalize-retired-github-specs
author: Gavin
task_id: 20260827-externalize-retired-github-specs
status: compressed
documentation_impact: required
documentation_targets:
  - README.md
  - harness/docs/decisions/0006-freeze-github-source-crawler-spec.md
  - harness/docs/decisions/0007-freeze-github-discovery-ingestion-spec.md
  - harness/docs/decisions/0008-harness-freeze-lifecycle.md
  - harness/docs/decisions/20260826-retire-knowledge-incubator.md
  - harness/docs/decisions/20260827-externalize-retired-github-specs.md
documentation_reason: 主项目不再保留两份冻结规格，需要用长期决策和项目入口准确记录外部归档、未完成语义与未来恢复边界。
state_history:
---

# 20260827-externalize-retired-github-specs

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在保持独立知识孵化归档及其不可变标签不变的前提下，从博客主项目开放规格列表移除两份未完成的 GitHub 孵化规格，并通过长期 ADR 明确“取消并外置、不是完成”的审计语义；同时修复 Harness 在 merge 历史中漏判原始 active spec 的路径查询，使本次变更能够通过真实的历史完整性门禁。

## Acceptance criteria

- AC-1: 主项目 `harness/specs/active/` 和生成索引不再包含 `20260807-github-discovery-ingestion`、`20260807-github-source-crawler`，frozen 计数为 0；主项目不生成这两项的 compressed spec 或完成事件。
- AC-2: 新的长期 ADR 记录独立归档仓库、远端提交、不可变标签、归档内原路径、Git blob、SHA-256，以及两项“未完成、不可从博客恢复”的语义；0006、0007、0008 和知识孵化退役 ADR 明确引用该后续决策。
- AC-3: 根 README 不再把两项描述成主项目中的冻结规格，而是说明未完成设计仅由独立只读归档保存，未来恢复必须作为独立产品重新立项。
- AC-4: `history-integrity` 的 active-spec 历史查询在 merge 提交发生路径简化时仍能发现当前 HEAD 祖先中的原始规格，并有回归测试；全局 Harness 完整性检查通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260827-externalize-retired-github-specs.json](../../verification/evidence/20260827-externalize-retired-github-specs.json)

Closed at 2026-08-27T14:30:17.057630+00:00.
