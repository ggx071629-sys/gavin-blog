---
id: archive-20260910-studio-theme
level: L2
summary: 为第二版写作台建立独立双主题和本地图标基础
load_when:
  - task:20260910-studio-theme
task_id: 20260910-studio-theme
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录后台主题作用域、资源来源、许可证及验证结论供后续阶段复用。
evidence_sha256: 004a13289498e783a8110a3be23e7ead9a5002b2d5eb0542d7bae5635f7e36e3
state_history:
---

# 20260910-studio-theme

Deterministic compressed record. The original active spec remains in Git history.

## Goal

新增限于后台 shell、login 和后台弹窗的 studio 主题，复用本地 Inter/Noto Sans SC，并提供设计稿官方图标及许可，为后续外壳和控件提供一致基础。

## Acceptance criteria

- AC-1: 后台浅色画布 #ffffff、正文 #080c15、主色 #005dff，深色画布 #10141e、正文 #f0f3fa、主色 #7daaff；后台弹窗保持相同主题，公开页面原始颜色不变。
- AC-2: 后台使用本地 Inter/Noto Sans SC，图标来自选定设计包并保留 Tabler/Lucide 许可证；不发出外部字体或图标网络请求，基础组件类型正确。

## Result

Verified and closed by the harness close command.

## Evidence

[20260910-studio-theme.json](../../verification/evidence/20260910-studio-theme.json)

SHA-256: `004a13289498e783a8110a3be23e7ead9a5002b2d5eb0542d7bae5635f7e36e3`

Closed at 2026-09-10T06:40:18.588913+00:00.
