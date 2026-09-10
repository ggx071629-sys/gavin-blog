---
id: spec-20260910-studio-regression-guards
level: L1
summary: 修正整体验收暴露的旧源码断言与无用助手变量
load_when:
  - task:20260910-studio-regression-guards
task_id: 20260910-studio-regression-guards
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录完整回归发现的旧断言与保持的错误显示合同。
state_history:
---
# Context
U6-03 全量 Web 单元测试发现列表/媒体和首页组合组件的源码断言过时，ESLint 发现助手未使用变量。
# Goal
恢复完整静态与单元回归，保持现有 UI、错误恢复及入口开关行为。
# Non-goals
不改公开页面设计、用户既有修改、运行时契约或质量阈值。
# Acceptance criteria
- AC-1: 列表和媒体的错误优先于空态，测试检查实际共用组件及重试入口；主页入口断言检查实际组合组件。
- AC-2: 移除无用局部变量，助手入口开关与路径隔离仍由原 composable 控制。
# Risks
不能通过删除正负预期掩盖缺陷；全量单元和 lint 需复验。
# Verification plan
## Verification cases
- AC-1 => M06-STUDIO-FAILURE-GUARDS-01, M07-UNIT-TYPOGRAPHY-01
- AC-2 => M10-STUDIO-HOST-GUARD-01
## Gates
- web-quality => AC-1, AC-2
- harness-integrity => AC-1, AC-2
