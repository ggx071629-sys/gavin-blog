---
id: spec-20260910-studio-article-preview
level: L1
summary: 文章草稿预览接入 Studio 阅读工作副本与返回编辑导航
load_when:
  - task:20260910-studio-article-preview
task_id: 20260910-studio-article-preview
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U4-05 按计划在前置验收归档后实施。
# Goal
文章草稿预览接入 Studio 阅读工作副本与返回编辑导航
# Non-goals
不改变公开阅读页、不复制发布逻辑；从返回编辑继续校验保存和确认发布。
# Acceptance criteria
- AC-1: 预览使用 Studio 外壳、清晰工作副本标记和返回编辑/版本历史入口，保留真实正文、目录、代码复制与单一一级标题。
- AC-2: 草稿及已发布未更新副本均读取真实数据且不改变公开版本；返回编辑保留已保存内容，双主题与窄屏可读。
# Risks
草稿和发布工作副本说明必须准确；标题层级、代码复制和真实阅读渲染保留。
# Verification plan
## Verification cases
- AC-1 => M02-STUDIO-PREVIEW-01
- AC-2 => M02-STUDIO-PREVIEW-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
