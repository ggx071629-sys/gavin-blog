---
id: spec-20260910-studio-final-operations
level: L1
summary: U6-03 运营与助手真实流程有界验收组
load_when:
  - task:20260910-studio-final-operations
task_id: 20260910-studio-final-operations
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 明确最终验收的运营与助手流程边界及真实测试依据。
state_history:
---
# Context
U6-03 的 21 个独立浏览器场景包含逐次冷启动成本，拆分为两组保留完整场景和每个门禁 600 秒预算。
# Goal
真实验证名片、关于页、栏目标签、媒体迁移和助手管理闭环。
# Non-goals
不更改产品代码或质量门槛，不部署，不连接实时付费供应商。此组完成不能单独标记 U6-03 完成。
# Acceptance criteria
- AC-1: 名片、关于编辑预览历史、栏目、媒体与回收站迁移真实流程通过。
- AC-2: 助手概览、预算和确认弹窗、本地受控供应商试问及开放切换通过。
# Risks
不复用被中止运行的证据；该组与最终写作/共享边界组均通过后才能归档 U6-03。
# Verification plan
## Verification cases
- AC-1 => M06-STUDIO-PROFILE-01, M11-STUDIO-ABOUT-EDITOR-01, M11-STUDIO-ABOUT-PREVIEW-01, M11-STUDIO-ABOUT-HISTORY-01, M03-STUDIO-TAXONOMY-01, M05-STUDIO-MEDIA-01, M05-STUDIO-CONTENT-01
- AC-2 => M10-STUDIO-TRIAL-01, M10-STUDIO-DIALOGS-01, M10-STUDIO-OVERVIEW-01
## Gates
- e2e => AC-1, AC-2
- web-quality => AC-2
- harness-integrity => AC-1, AC-2
