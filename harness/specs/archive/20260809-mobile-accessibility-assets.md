---
id: archive-20260809-mobile-accessibility-assets
level: L2
summary: 建立可访问移动后台抽屉、合格触控目标与自托管字体边界
load_when:
  - task:20260809-mobile-accessibility-assets
author: Codex
task_id: 20260809-mobile-accessibility-assets
status: compressed
restoration_source: "ed6bcb7f9ae3b9796875eb942bfd66fbc88bb2ed:harness/specs/active/20260809-mobile-accessibility-assets.md"
restored_at: 2026-08-11
---

# 20260809-mobile-accessibility-assets

Deterministic compressed record. The original active spec remains in Git history.

## Goal

把移动导航明确实现为键盘和辅助技术一致的 modal drawer；让相邻小图标按钮满足 WCAG 2.2 触控目标基线；把实际使用字体及字重作为构建资产自托管，断网时不产生外部字体请求或布局溢出。

## Acceptance criteria

1. 移动抽屉具有 `role=dialog`、`aria-modal=true`、可见标题/label，打开后初始焦点进入抽屉，Tab/Shift+Tab 在抽屉可用控件内循环，Escape 和遮罩关闭并把焦点返回触发按钮。
2. 抽屉打开时主内容及移动 header 的非抽屉部分不可聚焦/交互；路由变化、跨桌面 breakpoint 与组件卸载均释放 body lock 和 inert 状态。
3. Profile 技能上移、下移、删除按钮及同组相邻图标按钮具有至少 32×32 CSS px 的命中区；移动验证目标优先达到 44×44，禁用状态不缩小布局。
4. Inter 400/500/600、Hanken Grotesk 700/800、JetBrains Mono 400/500/600 的 WOFF2 构建资产本地提供，`font-display` 明确；删除 Google Fonts stylesheet 与 preconnect。
5. CSP Report-Only 的 font/style 来源同步收敛到 self；浏览器网络记录无 `fonts.googleapis.com` 或 `fonts.gstatic.com` 请求。
6. 390×844、375×667 与移动横屏完成焦点循环、背景不可聚焦、Escape/返回焦点；200% 文本缩放不遮挡关闭按钮和末项导航，断网/字体失败 fallback 不产生水平溢出。

## Result

Verified and closed by the harness close command.

## Evidence

[20260809-mobile-accessibility-assets.json](../../verification/evidence/20260809-mobile-accessibility-assets.json)

Closed at 2026-08-11T09:48:55.422537+00:00.
