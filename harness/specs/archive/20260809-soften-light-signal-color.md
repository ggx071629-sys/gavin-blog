---
id: archive-20260809-soften-light-signal-color
level: L2
summary: 以低饱和批注紫替换浅色主题中过于突兀的酸柠檬信号色
load_when:
  - task:20260809-soften-light-signal-color
author: Gavin
task_id: 20260809-soften-light-signal-color
status: compressed
restoration_source: "fa89a6a2a1906ec9f80e596f5906d9ed54ccc52f:harness/specs/active/20260809-soften-light-signal-color.md"
restored_at: 2026-08-11
---

# 20260809-soften-light-signal-color

Deterministic compressed record. The original active spec remains in Git history.

## Goal

将浅色主题信号色改为低饱和“批注紫”，降低视觉刺激，同时保留 Electric Editorial 的明确批注感、交互可见性和无障碍对比度。

## Acceptance criteria

1. 浅色主题 `--ee-signal` 使用 `#8878c0`，`--ee-signal-ink` 使用 `#171326`。
2. 深色主题继续使用 `--ee-signal: #c7f300` 与现有 signal ink，不发生回归。
3. 浅色信号色与 `#f8f9fa` 画布达到至少 `3:1` 对比度；信号色与 signal ink 达到至少 `4.5:1`。
4. 全站现有 signal 消费者通过语义令牌自动更新，不新增组件级 raw palette 值。
5. 浅色与深色首页在桌面、移动视口均无 axe 违规或横向溢出。

## Result

Verified and closed by the harness close command.

## Evidence

[20260809-soften-light-signal-color.json](../../verification/evidence/20260809-soften-light-signal-color.json)

Closed at 2026-08-09T13:05:29.210662+00:00.
