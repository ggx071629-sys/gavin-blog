---
id: archive-20260910-studio-shell
level: L2
summary: 对齐第二版写作台侧栏移动导航品牌及页头
load_when:
  - task:20260910-studio-shell
task_id: 20260910-studio-shell
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录侧栏断点、主题切换和短视口导航的持续约束。
evidence_sha256: 0d64abbef65bbc2bdd112a66db499f8d7c0512b72c2e4c4f49fd9819f9355d65
state_history:
---

# 20260910-studio-shell

Deterministic compressed record. The original active spec remains in Git history.

## Goal

采用桌面 254px 浅灰蓝侧栏、36px 主内容边距、文字品牌和带本地图标的分组导航；中等屏 230px 侧栏，760px 以下折叠为可访问移动导航。

## Acceptance criteria

- AC-1: 1440/1487px 桌面侧栏 254px、主内容起点 x=290；761–1300px 侧栏 230px；内容/运营九项图标和当前路径状态可辨，深浅主题保持蓝色和同一布局，短视口导航/退出可达。
- AC-2: 320/390/760px 菜单按钮打开 modal 导航，Tab 循环、Escape 和遮罩关闭后归还焦点；路由导航与切回桌面解除 inert/滚动锁，查看站点和真实退出仍可用，无横溢、缺失图标或浏览器错误。

## Result

Verified and closed by the harness close command.

## Evidence

[20260910-studio-shell.json](../../verification/evidence/20260910-studio-shell.json)

SHA-256: `0d64abbef65bbc2bdd112a66db499f8d7c0512b72c2e4c4f49fd9819f9355d65`

Closed at 2026-09-10T06:55:11.839373+00:00.
