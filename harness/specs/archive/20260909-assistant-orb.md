---
id: archive-20260909-assistant-orb
level: L2
summary: 保留导航并增加可拖动悬浮球与一次性提示
load_when:
  - task:20260909-assistant-orb
task_id: 20260909-assistant-orb
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 记录悬浮球位置偏好、引导生命周期和移除首页提示。
evidence_sha256: 3807f7d0cd9ae11cdb8b8b80f3bece77ca2ad8d4f493d07f18d41f2010352174
state_history:
---

# 20260909-assistant-orb

Deterministic compressed record. The original active spec remains in Git history.

## Goal

允许公开路径显示导航和悬浮球；页面稳定约三秒后展示可关闭提示；关闭或打开助手结束引导；拖动吸附最近左右边缘并记住位置。

## Acceptance criteria

- AC-1: 顶部入口保留，首页行内提示移除；双端悬浮球点击打开同一助手，关闭恢复原触发点；禁止路径和禁用开关不展示。
- AC-2: 首次约三秒展示提示及影响阅读可关闭文案；关闭仅隐藏提示，任一入口打开助手也结束引导，同浏览器刷新和跨路由不再展开；存储异常安全降级。
- AC-3: 鼠标和触摸拖动不会误触打开；松手吸附最近左右边缘，刷新恢复位置；改变视口仍在安全可见范围，提示也不横溢。

## Result

Verified and closed by the harness close command.

## Evidence

[20260909-assistant-orb.json](../../verification/evidence/20260909-assistant-orb.json)

SHA-256: `3807f7d0cd9ae11cdb8b8b80f3bece77ca2ad8d4f493d07f18d41f2010352174`

Closed at 2026-09-09T13:41:26.772284+00:00.
