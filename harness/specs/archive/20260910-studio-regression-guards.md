---
id: archive-20260910-studio-regression-guards
level: L2
summary: 修正整体验收暴露的旧源码断言与无用助手变量
load_when:
  - task:20260910-studio-regression-guards
task_id: 20260910-studio-regression-guards
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录完整回归发现的旧断言与保持的错误显示合同。
evidence_sha256: 8822a6fdfbe3348c9142bcd87438ad49ec9d031696d7d8c66f5dc5723f0d7126
state_history:
---

# 20260910-studio-regression-guards

Deterministic compressed record. The original active spec remains in Git history.

## Goal

恢复完整静态与单元回归，保持现有 UI、错误恢复及入口开关行为。

## Acceptance criteria

- AC-1: 列表和媒体的错误优先于空态，测试检查实际共用组件及重试入口；主页入口断言检查实际组合组件。
- AC-2: 移除无用局部变量，助手入口开关与路径隔离仍由原 composable 控制。

## Result

Verified and closed by the harness close command.

## Evidence

[20260910-studio-regression-guards.json](../../verification/evidence/20260910-studio-regression-guards.json)

SHA-256: `8822a6fdfbe3348c9142bcd87438ad49ec9d031696d7d8c66f5dc5723f0d7126`

Closed at 2026-09-10T12:40:00.662340+00:00.
