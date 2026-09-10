---
id: archive-20260910-studio-dialogs
level: L2
summary: 统一助手预算费用同步维护弹窗及真实确认状态
load_when:
  - task:20260910-studio-dialogs
task_id: 20260910-studio-dialogs
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录助手弹窗、维护直达链接与确认错误反馈。
evidence_sha256: d47b43e5beb3004afad40e94ce046a9e5e2223fc75d38c725aee37beb1f995c7
state_history:
---

# 20260910-studio-dialogs

Deterministic compressed record. The original active spec remains in Git history.

## Goal

共用一个焦点与滚动边界呈现预算、费用、同步和高级维护，避免叠加弹窗；仍可直达维护链接，确认取消返回原上下文，失败可见且可重试。

## Acceptance criteria

- AC-1: 费用、同步、预算、维护使用统一有名称弹窗；320–1440px 双主题无溢出、axe 通过，Escape/关闭/焦点恢复与直接维护链接可用。
- AC-2: 保留金额精度和版本确认，隔离真实预算保存及单项同步操作；未知结果不显示成功，确认失败留在可见上下文，取消不得发送写入。

## Result

Verified and closed by the harness close command.

## Evidence

[20260910-studio-dialogs.json](../../verification/evidence/20260910-studio-dialogs.json)

SHA-256: `d47b43e5beb3004afad40e94ce046a9e5e2223fc75d38c725aee37beb1f995c7`

Closed at 2026-09-10T07:46:13.167140+00:00.
