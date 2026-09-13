---
id: archive-20260909-assistant-orb-motion
level: L2
summary: 用 GSAP 将助手入口改为可暂停的持续动效能量球
load_when:
  - task:20260909-assistant-orb-motion
task_id: 20260909-assistant-orb-motion
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 记录持续动效、暂停偏好和响应式生命周期。
evidence_sha256: aefdc495a86042c4dae0e9d1bdf285e9d3569adaf0d910f56d8c516ee5f75fa7
state_history:
---

# 20260909-assistant-orb-motion

Deterministic compressed record. The original active spec remains in Git history.

## Goal

以主题色能量核心、轨道和呼吸光晕强化助手入口；滚动仅驱动装饰环；持续动效可暂停。

## Acceptance criteria

- AC-1: 双主题能量球持续悬浮和旋转，滚动驱动装饰环；双端点击、拖动吸边、引导和焦点恢复保持可用。
- AC-2: 用户可暂停并记住选择；减少动态效果下静态可用；后台、隐藏、拖动和聚焦停止常态动画；路由卸载清理自身时间线与 ScrollTrigger，反复进入不累积。

## Result

Verified and closed by the harness close command.

## Evidence

[20260909-assistant-orb-motion.json](../../verification/evidence/20260909-assistant-orb-motion.json)

SHA-256: `aefdc495a86042c4dae0e9d1bdf285e9d3569adaf0d910f56d8c516ee5f75fa7`

Closed at 2026-09-09T14:48:53.406661+00:00.
