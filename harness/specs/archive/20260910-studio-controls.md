---
id: archive-20260910-studio-controls
level: L2
summary: 统一写作台共用控件状态分隔行与弹窗视觉
load_when:
  - task:20260910-studio-controls
task_id: 20260910-studio-controls
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录共用控件尺度和状态语义边界供后续页面复用。
evidence_sha256: e6db3d0e2e0214ccbf61ecef605511f4f7b1953e7ac5e9e779595f822ef72fd0
state_history:
---

# 20260910-studio-controls

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在 studio 作用域统一按钮、字段、页签、状态、开放列表分隔线与确认弹窗；保持所有真实业务状态及确认行为。修复版本预览所复用 ThemeToggle 的初始读屏状态水合不一致，公开视觉不变。

## Acceptance criteria

- AC-1: 后台主要/次要按钮桌面至少 48px、手机至少 44px；字段边框、字号、圆角和聚焦层级一致；页签保持选中反馈，窄屏与双主题可读且无页面横溢。
- AC-2: 草稿、已发布、有未发布修改和保存/错误状态保留不同真实语义，列表采用开放行和细分隔线，确认弹窗继承后台双主题并保留取消、Escape、焦点归还与真实回滚。

## Result

Verified and closed by the harness close command.

## Evidence

[20260910-studio-controls.json](../../verification/evidence/20260910-studio-controls.json)

SHA-256: `e6db3d0e2e0214ccbf61ecef605511f4f7b1953e7ac5e9e779595f822ef72fd0`

Closed at 2026-09-10T07:06:44.997373+00:00.
