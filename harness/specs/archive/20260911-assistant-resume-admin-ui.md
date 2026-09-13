---
id: archive-20260911-assistant-resume-admin-ui
level: L2
summary: Q3-05 简历同步状态与立即刷新管理界面
load_when:
  - task:20260911-assistant-resume-admin-ui
task_id: 20260911-assistant-resume-admin-ui
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 记录首次/换址自动同步、手动刷新与状态展示。
evidence_sha256: 1fac58f4fe873be9dab6fbab7e6ce9bd48a479bf4705ae741a364c0cf4427b59
state_history:
---

# 20260911-assistant-resume-admin-ui

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在现有名片设置旁提供清楚可操作的同步状态，区分保存、排队、检查与索引结果。

## Acceptance criteria

- AC-1: 展示未配置/处理中/成功/失败、可用性、最后检查与索引时间和可操作错误；仅显式按钮POST刷新。未保存换址时禁用刷新并说明先保存；刷新不重置其他草稿，409提示绑定冲突，429说明冷却。
- AC-2: 保存后重新读取状态，活动任务只轮询GET、离开页面停止；键盘可用、手机无溢出、双主题可读，读状态失败不伪称同步成功。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-assistant-resume-admin-ui.json](../../verification/evidence/20260911-assistant-resume-admin-ui.json)

SHA-256: `1fac58f4fe873be9dab6fbab7e6ce9bd48a479bf4705ae741a364c0cf4427b59`

Closed at 2026-09-10T18:25:29.531482+00:00.
