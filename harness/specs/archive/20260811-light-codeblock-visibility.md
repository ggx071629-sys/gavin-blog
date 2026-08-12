---
id: archive-20260811-light-codeblock-visibility
level: L2
summary: 修复浅色模式下正文代码块背景与文字色重叠不可见，并让 highlight.js 主题随颜色主题切换
load_when:
  - task:20260811-light-codeblock-visibility
author: Gavin
task_id: 20260811-light-codeblock-visibility
status: compressed
state_history:
---

# 20260811-light-codeblock-visibility

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让正文代码块在浅色与深色模式下都清晰可读，且 `highlight.js` 语法 token 颜色随颜色主题在浅色与深色主题之间正确切换，消除当前浅色模式下的"深底深字"重叠与 token 对比不足。

## Acceptance criteria

- 浅色模式下 `.prose-gavin.editorial-prose pre` 的背景与文字色对比度 ≥ 4.5:1（WCAG AA 正文标准）。
- 深色模式下代码块外观与当前可用状态保持一致，不回归。
- 无语言或未注册语言（含 `language-text`）的代码块在两种模式下都清晰可读，不依赖语法 token 着色。
- `highlight.js` 主题随 `colorMode` 在浅色主题与深色主题之间切换：浅色模式加载浅色主题，深色模式加载深色主题，切换时不触发整页 reload。
- 浅色与深色模式下，有语言的代码块（如 ```js、```python）的语法 token 与各自背景对比度 ≥ 4.5:1。
- `projects`、`notes`、`books` 三个公开正文页与 `admin/articles/[id]/preview` 后台预览页在两种模式下代码块均不重叠。
- 不新增运行时依赖，不改变 `packages/contracts`、`apps/api`、数据库或两个冻结 GitHub spec。
- 现有 `theme-structure`、`search-theme` 等主题相关 e2e 测试不回归；Lighthouse accessibility 在受测页面仍达到 100。

## Result

Verified and closed by the harness close command.

## Evidence

[20260811-light-codeblock-visibility.json](../../verification/evidence/20260811-light-codeblock-visibility.json)

Closed at 2026-08-12T02:23:13.799663+00:00.
