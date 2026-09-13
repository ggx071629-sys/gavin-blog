---
id: archive-20260809-sync-light-heading-font
level: L2
summary: 将浅色主题标题字体统一为深色主题的 Hanken Grotesk
load_when:
  - task:20260809-sync-light-heading-font
author: Gavin
task_id: 20260809-sync-light-heading-font
status: compressed
restoration_source: "fa89a6a2a1906ec9f80e596f5906d9ed54ccc52f:harness/specs/active/20260809-sync-light-heading-font.md"
restored_at: 2026-08-11
---

# 20260809-sync-light-heading-font

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让浅色和深色主题的全部标题字体消费者共同使用 Hanken Grotesk，并移除不再需要的 Chivo 网络字体请求；正文、等宽字体和其他视觉令牌保持不变。

## Acceptance criteria

1. 根主题 `--ee-heading` 使用与当前深色主题一致的 `"Hanken Grotesk", Inter, ui-sans-serif, system-ui, sans-serif` 字体栈。
2. 深色主题不再单独覆盖 `--ee-heading`，避免未来浅色／深色标题字体再次漂移。
3. Nuxt 字体样式表继续加载 Hanken Grotesk、Inter 与 JetBrains Mono，但不再请求无消费者的 Chivo。
4. 浏览器中同一拉丁标题在浅色／深色切换前后的计算 `font-family` 与字形宽度一致。
5. 正文与等宽字体声明保持不变；现有主题切换和公开页面水合行为不因本任务新增回归。
6. 目标单测、全量 Web 单测、类型检查、生产构建及字体主题浏览器检查通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260809-sync-light-heading-font.json](../../verification/evidence/20260809-sync-light-heading-font.json)

Closed at 2026-08-09T13:05:35.228583+00:00.
