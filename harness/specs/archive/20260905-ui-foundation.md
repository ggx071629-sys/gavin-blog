---
id: archive-20260905-ui-foundation
level: L2
summary: 完成视觉提案第一阶段的共用基础、公开外壳与后台框架
load_when:
  - task:20260905-ui-foundation
task_id: 20260905-ui-foundation
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 记录真实共用组件、尺度与外壳边界，区分本轮阶段和既有产品阶段。
evidence_sha256: d0d3e998bfc8cba41659e4e9244dc5d0dd4e929b7abe0f01404db3c6eb82c540
state_history:
---

# 20260905-ui-foundation

Deterministic compressed record. The original active spec remains in Git history.

## Goal

整理实际路由、共用组件与设计差异，在真实 Nuxt 中落实安静背景、统一尺度、共用主题按钮、公开页头页尾和后台框架，并提供可复查验证记录。

## Acceptance criteria

- AC-1: 现有字体和浅蓝/深黄绿语义色保持，页面背景不再全屏点阵；共用按钮、表单、反馈、列表、阅读容器使用明确尺度；双主题与代表宽度无新增横滚，未迁移的页面业务回归通过。
- AC-2: 公开页头与页尾层级收敛，桌面和移动导航保留现有入口顺序、当前页标记、认证入口和主题持久化；菜单维持全屏/抽屉/桌面断点、焦点循环、Escape 还焦点与背景解锁；菜单导航后焦点到达正文。
- AC-3: 后台框架以紧凑侧栏和轻量分组支持所有原有入口，共用主题组件正常；短视口导航可滚动，手机模态、焦点和认证行为不退化；页面与组件清单、改造前检查及验证结果可追踪，本地设计查询链接按真实文件路径验证且缺失/不稳定引用仍失败。

## Result

Verified and closed by the harness close command.

## Evidence

[20260905-ui-foundation.json](../../verification/evidence/20260905-ui-foundation.json)

SHA-256: `d0d3e998bfc8cba41659e4e9244dc5d0dd4e929b7abe0f01404db3c6eb82c540`

Closed at 2026-09-05T11:55:36.188969+00:00.
