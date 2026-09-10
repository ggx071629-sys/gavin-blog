---
id: spec-20260910-studio-coverage
level: L1
summary: 核对二十个真实写作台入口与同主题视觉基线
load_when:
  - task:20260910-studio-coverage
task_id: 20260910-studio-coverage
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U6-01 按计划在前置验收归档后实施。
# Goal
核对二十个真实写作台入口与同主题视觉基线
# Non-goals
不部署、不扩大功能、不改动无关用户修改；样例内容差异不得伪装为业务数据。
# Acceptance criteria
- AC-1: 二十个设计入口均对应真实页面，标题、公共外壳、主题字体与关键布局符合既定设计，无遗漏。
# Risks
截图与原始日志保持本地；仅相同主题视口状态可比较。
# Verification plan
## Verification cases
- AC-1 => M07-STUDIO-COVERAGE-01
## Gates
- e2e => AC-1
- harness-integrity => AC-1
