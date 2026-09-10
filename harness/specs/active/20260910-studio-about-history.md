---
id: spec-20260910-studio-about-history
level: L1
summary: 关于页开放版本列表、真实差异和确认回滚
load_when:
  - task:20260910-studio-about-history
task_id: 20260910-studio-about-history
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U5-04 按计划在前置验收归档后实施。
# Goal
关于页开放版本列表、真实差异和确认回滚
# Non-goals
不新增其他内容版本历史，不修改公开关于页；本项归档后转 U5-05。
# Acceptance criteria
- AC-1: 历史以开放列表和读取区呈现，当前发布与所选快照区分，接入已有分页并支持失败重试。
- AC-2: 真实快照、差异和回滚保持不可变修订及未发布修改约束；双主题和窄屏可读。
# Risks
读取失败不能保留误导性旧快照；回滚必须确认并创建新修订。
# Verification plan
## Verification cases
- AC-1 => M11-STUDIO-ABOUT-HISTORY-01
- AC-2 => M11-STUDIO-ABOUT-HISTORY-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
