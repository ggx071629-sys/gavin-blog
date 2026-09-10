---
id: spec-20260910-studio-operations-acceptance
level: L1
summary: 阶段五七页运营状态与响应式最终验收
load_when:
  - task:20260910-studio-operations-acceptance
task_id: 20260910-studio-operations-acceptance
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U5-08 按计划在前置验收归档后实施。
# Goal
阶段五七页运营状态与响应式最终验收
# Non-goals
完成阶段五后停止，绝不进入阶段六；不修改公开页面和无关用户改动。
# Acceptance criteria
- AC-1: 七个入口在双主题及 320–1440px 可达、无横向溢出，关键操作与无障碍检查通过。
- AC-2: 名片冲突、关于保存失败/重试、历史读取失败恢复、媒体与回收站空态保持真实语义；完成档案准确并停止于阶段五。
# Risks
组合验收发现问题只修复运营范围；截图/日志保持本地，未通过任务不得归档。
# Verification plan
## Verification cases
- AC-1 => M05-STUDIO-OPERATIONS-LAYOUT-01
- AC-2 => M05-STUDIO-OPERATIONS-STATES-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
