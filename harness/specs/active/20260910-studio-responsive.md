---
id: spec-20260910-studio-responsive
level: L1
summary: 二十页双主题响应式与键盘失败状态验收
load_when:
  - task:20260910-studio-responsive
task_id: 20260910-studio-responsive
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U6-02 按计划在前置验收归档后实施。
# Goal
二十页双主题响应式与键盘失败状态验收
# Non-goals
不扩大产品范围，不连接实时供应商，不部署。
# Acceptance criteria
- AC-1: 二十页双主题六个视口无横向溢出，主内容 WCAG A/AA 自动扫描通过。
- AC-2: 导航键盘焦点闭环以及列表、运营、助手适用空错冲突状态通过。
# Risks
主题切换需等待控件过渡完成；不把错误状态当作空数据。
# Verification plan
## Verification cases
- AC-1 => M07-STUDIO-RESPONSIVE-01
- AC-2 => M02-STUDIO-SHELL-01, M02-STUDIO-LIST-STATES-01, M05-STUDIO-OPERATIONS-STATES-01, M10-STUDIO-STATES-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
