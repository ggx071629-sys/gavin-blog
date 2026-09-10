---
id: spec-20260910-studio-about-editor
level: L1
summary: 关于页开放内容分区与真实保存发布状态
load_when:
  - task:20260910-studio-about-editor
task_id: 20260910-studio-about-editor
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U5-02 按计划在前置验收归档后实施。
# Goal
关于页开放内容分区与真实保存发布状态
# Non-goals
不重做公开关于页，不复制名片身份字段；本项归档后再进入 U5-03。
# Acceptance criteria
- AC-1: 身份资料入口与五个内容分区清晰，十项限额、增删排序和字段约束保留。
- AC-2: 草稿自动保存、预览前保存和显式发布区分，双主题与窄屏可用。
# Risks
保持自动保存队列和发布前保存屏障；不可把未发布修改显示为已发布。
# Verification plan
## Verification cases
- AC-1 => M11-STUDIO-ABOUT-EDITOR-01
- AC-2 => M11-STUDIO-ABOUT-EDITOR-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
