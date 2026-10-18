---
id: archive-20260809-restore-writing-desk-entry
level: L2
summary: 在公开站点桌面与移动导航中恢复受认证保护的写作台入口
load_when:
  - task:20260809-restore-writing-desk-entry
author: Gavin
task_id: 20260809-restore-writing-desk-entry
status: compressed
restoration_source: "fa89a6a2a1906ec9f80e596f5906d9ed54ccc52f:harness/specs/active/20260809-restore-writing-desk-entry.md"
restored_at: 2026-08-11
---

# 20260809-restore-writing-desk-entry

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在不改变认证与后台行为的前提下，为桌面和移动端公开导航恢复清晰、一致的“写作台”入口，并复用当前 Electric Editorial 视觉语言。

## Acceptance criteria

1. 桌面断点的公共页头显示“写作台”链接，目标为 `/admin/articles`，视觉层级与当前主按钮样式一致。
2. 移动端菜单打开后显示“写作台”链接，目标为 `/admin/articles`；点击后菜单关闭并进入现有认证流程。
3. 未登录访问入口仍由管理员中间件跳转到 `/admin/login`，不暴露后台内容。
4. 现有公共导航、搜索、主题切换和响应式菜单行为不回归。
5. 相关自动化测试能够观察桌面入口、移动入口及未登录重定向。

## Result

Verified and closed by the harness close command.

## Evidence

[20260809-restore-writing-desk-entry.json](../../verification/evidence/20260809-restore-writing-desk-entry.json)

Closed at 2026-08-09T13:05:23.231907+00:00.
