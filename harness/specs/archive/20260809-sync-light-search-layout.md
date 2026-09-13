---
id: archive-20260809-sync-light-search-layout
level: L2
summary: 让桌面搜索页浅色主题复用暗色主题的居中卡片布局
load_when:
  - task:20260809-sync-light-search-layout
author: Gavin
task_id: 20260809-sync-light-search-layout
status: compressed
restoration_source: "fa89a6a2a1906ec9f80e596f5906d9ed54ccc52f:harness/specs/active/20260809-sync-light-search-layout.md"
restored_at: 2026-08-11
---

# 20260809-sync-light-search-layout

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让浅色主题在桌面视口复用暗色主题的搜索页结构：外层居中、内容限制为 `max-w-4xl`，面板具备边框、内边距、语义表面背景和主题阴影；颜色、圆角和阴影值继续由各主题的现有语义令牌决定。

## Acceptance criteria

1. 在宽度至少 `1024px` 的视口中，浅色与暗色搜索页的 stage 都使用水平、垂直居中的 flex 布局。
2. 两种主题的搜索面板都使用相同的最大宽度、水平定位、边框宽度和 `32px` 内边距，切换主题不再改变卡片的主要几何结构。
3. 面板背景、边框、圆角和阴影继续引用现有 `--ee-*` 语义令牌，不新增 raw palette 值。
4. 小于 `1024px` 时不应用桌面卡片化规则，现有移动布局保持不变。
5. 自动化 E2E 覆盖桌面双主题的布局一致性，并确认移动视口没有横向溢出。

## Result

Verified and closed by the harness close command.

## Evidence

[20260809-sync-light-search-layout.json](../../verification/evidence/20260809-sync-light-search-layout.json)

Closed at 2026-08-09T13:05:41.231172+00:00.
