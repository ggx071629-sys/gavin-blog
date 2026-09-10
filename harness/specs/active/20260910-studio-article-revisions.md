---
id: spec-20260910-studio-article-revisions
level: L1
summary: 文章发布历史采用清晰版本列表与快照差异阅读区
load_when:
  - task:20260910-studio-article-revisions
task_id: 20260910-studio-article-revisions
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U4-06 按计划在前置验收归档后实施。
# Goal
文章发布历史采用清晰版本列表与快照差异阅读区
# Non-goals
不移除真实差异与回滚，不新增读书或项目历史，不改变不可变修订合同。
# Acceptance criteria
- AC-1: 版本页返回编辑、预览工作副本、当前发布说明及可选版本列表清晰；桌面双栏手机上下排列，快照与差异可读。
- AC-2: 真实版本加载、查看快照、与当前比较、取消回滚和确认新修订、错误恢复均通过验证，双主题窄屏无溢出。
# Risks
当前公开版本与选中快照必须区分；回滚仍需确认并保留错误可见性。
# Verification plan
## Verification cases
- AC-1 => M02-STUDIO-REVISIONS-01
- AC-2 => M02-STUDIO-REVISIONS-01, M02-DESK-REVISIONS-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
