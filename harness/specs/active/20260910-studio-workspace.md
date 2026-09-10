---
id: spec-20260910-studio-workspace
level: L1
summary: 对齐共用写作工作面与真实 Markdown 工具栏
load_when:
  - task:20260910-studio-workspace
task_id: 20260910-studio-workspace
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U4-01 按计划在前置验收归档后实施。
# Goal
对齐共用写作工作面与真实 Markdown 工具栏
# Non-goals
不重写编辑器、保存队列、媒体上传或发布机制，不改公开 Markdown 消费。
# Acceptance criteria
- AC-1: 共用写作工作面保持正文优先、右侧设置和手机可读分区，Markdown/预览与错误字段定位保留，六个入口双主题无横溢。
- AC-2: 工具栏在当前选择处插入真实 Markdown，字数随内容变化，媒体上传和光标选区保持；工具栏仅在写作工作区启用。
# Risks
共用工作区影响六个新建编辑入口；手机内容设置仍需被错误定位自动揭示。
# Verification plan
## Verification cases
- AC-1 => M02-STUDIO-WORKSPACE-01
- AC-2 => M02-STUDIO-WORKSPACE-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
