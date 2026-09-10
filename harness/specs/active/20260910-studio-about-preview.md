---
id: spec-20260910-studio-about-preview
level: L1
summary: 关于草稿预览与共用身份资料
load_when:
  - task:20260910-studio-about-preview
task_id: 20260910-studio-about-preview
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U5-03 按计划在前置验收归档后实施。
# Goal
关于草稿预览与共用身份资料
# Non-goals
不修改公开关于模板和名片字段；完成后转 U5-04。
# Acceptance criteria
- AC-1: 预览采用 Studio 外壳与返回编辑/历史导航，真实工作副本和公开状态明确。
- AC-2: 身份资料来自共用公开 profile，后台可核对公开模板未呈现的引言和写作范围，双主题与窄屏可读。
# Risks
草稿不可误示为公开版本；隐藏联系资料不能泄露。
# Verification plan
## Verification cases
- AC-1 => M11-STUDIO-ABOUT-PREVIEW-01
- AC-2 => M11-STUDIO-ABOUT-PREVIEW-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
