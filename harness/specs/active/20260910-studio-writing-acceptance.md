---
id: spec-20260910-studio-writing-acceptance
level: L1
summary: 阶段四写作闭环与失败冲突跨尺寸最终验收
load_when:
  - task:20260910-studio-writing-acceptance
task_id: 20260910-studio-writing-acceptance
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U4-07 按计划在前置验收归档后实施。
# Goal
阶段四写作闭环与失败冲突跨尺寸最终验收
# Non-goals
完成本项即停止，不进入阶段五或六；保留用户原有未提交改动。
# Acceptance criteria
- AC-1: 三类新建编辑的发布前保存、取消确认、失败重试、离页保护、409 冲突、媒体与不完整引用均按既有合同工作。
- AC-2: 六个新建编辑入口、文章预览和历史的真实行为、双主题及 320–1440px 布局通过最终组合回归。
- AC-3: 编辑器版本/Slug/保存屏障合同、类型与静态检查通过；各项完成档案及阶段状态准确。
# Risks
跨页保存、冲突和媒体校验不得因视觉改造失效；所有验收需基于真实浏览器和保存合同。
# Verification plan
## Verification cases
- AC-1 => M02-DESK-SAFETY-01, M02-DESK-RESOURCES-01, M02-UNIT-ARTICLE-LOOP-01
- AC-2 => M02-STUDIO-WORKSPACE-01, M02-STUDIO-ARTICLE-EDITOR-01, M03-STUDIO-BOOK-EDITOR-01, M04-STUDIO-PROJECT-EDITOR-01, M02-STUDIO-PREVIEW-01, M02-STUDIO-REVISIONS-01
- AC-3 => M02-UNIT-EDITOR-SAVE-CONTRACT-01
## Gates
- e2e => AC-1, AC-2, AC-3
- web-quality => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
