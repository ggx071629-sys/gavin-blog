---
id: spec-20260811-light-codeblock-visibility
level: L1
summary: 修复浅色模式下正文代码块背景与文字色重叠不可见，并让 highlight.js 主题随颜色主题切换
load_when:
  - task:20260811-light-codeblock-visibility
author: Gavin
task_id: 20260811-light-codeblock-visibility
status: active
state_history:
---

# Context

正文页统一通过 `MarkdownArticle` 渲染 Markdown，并在 `projects/[slug]`、`notes/[year]/[month]/[slug]`、`books/[year]/[month]/[slug]`、`admin/articles/[id]/preview` 四个页面给组件传入 `editorial-prose` class，使根元素同时带有 `prose-gavin` 与 `editorial-prose`。

`apps/web/assets/css/main.css` 中：

- `.prose-gavin pre` 设置 `background: var(--ee-canvas)` 与 `color: var(--ee-ink)`。
- `.prose-gavin.editorial-prose pre` 仅覆盖 `background` 为硬编码 `#0b0d12`，**未同步覆盖 `color`**。

浅色模式下 `--ee-ink` 为 `#191c1d`，与硬编码的 `#0b0d12` 背景对比度约 1.05:1，导致浅色模式正文代码块文字与背景几乎完全重叠。`language-text` 等未注册语言走 `escapeHtml` fallback，无语法 token 着色，整段文字直接使用 `pre` 的 `color`，重叠最严重。

此外 `nuxt.config.ts` 仅全局加载 `highlight.js/styles/github-dark.css` 单一深色主题，不随颜色主题切换。浅色模式下即便修复 `pre` 的 `color`，有语言的代码块 token 仍使用为深色背景设计的浅色，与浅色背景对比不足。

# Goal

让正文代码块在浅色与深色模式下都清晰可读，且 `highlight.js` 语法 token 颜色随颜色主题在浅色与深色主题之间正确切换，消除当前浅色模式下的"深底深字"重叠与 token 对比不足。

# Non-goals

不重做 `editorial-prose` 设计系统或其他正文排版令牌；不修改 `highlight.js` 语言注册、`markdown-it` 配置或 Mermaid 渲染流程；不改变 API、数据模型、契约或数据库；不触碰两个冻结的 GitHub spec；不引入新的运行时依赖；不调整公开站布局、卡片结构或字体令牌。

# Acceptance criteria

- 浅色模式下 `.prose-gavin.editorial-prose pre` 的背景与文字色对比度 ≥ 4.5:1（WCAG AA 正文标准）。
- 深色模式下代码块外观与当前可用状态保持一致，不回归。
- 无语言或未注册语言（含 `language-text`）的代码块在两种模式下都清晰可读，不依赖语法 token 着色。
- `highlight.js` 主题随 `colorMode` 在浅色主题与深色主题之间切换：浅色模式加载浅色主题，深色模式加载深色主题，切换时不触发整页 reload。
- 浅色与深色模式下，有语言的代码块（如 ```js、```python）的语法 token 与各自背景对比度 ≥ 4.5:1。
- `projects`、`notes`、`books` 三个公开正文页与 `admin/articles/[id]/preview` 后台预览页在两种模式下代码块均不重叠。
- 不新增运行时依赖，不改变 `packages/contracts`、`apps/api`、数据库或两个冻结 GitHub spec。
- 现有 `theme-structure`、`search-theme` 等主题相关 e2e 测试不回归；Lighthouse accessibility 在受测页面仍达到 100。

# Risks

- **FOUC（首屏闪烁）**：hljs 主题若按 `colorMode` 在客户端动态加载，SSR 阶段可能先渲染错主题再切换。实现必须保证 SSR 输出与首屏主题一致，优先考虑用作用域 CSS（如 `:root:not(.dark) .hljs` 与 `:root.dark .hljs`）同时承载两套主题，而非运行时换 `<link>`。
- **主题作用域冲突**：hljs 官方主题以单一 `.hljs` 选择器定义 token 颜色，两套主题同时存在于 `main.css` 会互相覆盖。需要在实现阶段用作用域选择器或 CSS 层级隔离，避免直接修改 `node_modules` 中的主题文件。
- **`editorial-prose` 设计意图漂移**：当前硬编码 `#0b0d12` 可能被误当作"代码块永远深色"的设计意图。`web_prototype/light/` 浅色原型中代码块并未强制深色，应以此判定为偏离而非设计，修复应让浅色模式回归浅底深字。
- **后台预览同步**：`admin/articles/[id]/preview` 也使用 `editorial-prose`，修复必须覆盖后台预览，不能只改公开页。
- **回归面广**：四个正文页 + 主题切换 + hljs 主题加载方式，任一改动都可能影响主题结构 e2e 与 Lighthouse a11y 评分，需在实现后跑完整主题回归。

# Verification plan

1. **单元/组件测试**：为 `MarkdownArticle` 补充代码块在浅色与深色模式下的渲染快照或计算样式断言，覆盖有语言、无语言、`language-text` 三类 fence。
2. **对比度断言**：在测试中读取 `pre` 与典型 hljs token 的计算 `color` 与 `background-color`，断言对比度 ≥ 4.5:1。
3. **e2e 回归**：扩展 `theme-structure.spec.ts` 或新增 `codeblock-theme.spec.ts`，在 `projects`、`notes`、`books`、`admin preview` 四页的浅色与深色模式下，断言 `pre` 内文字计算颜色与背景颜色不相等且对比度达标；切换主题后断言 hljs 主题已切换且无整页 reload。
4. **质量门禁**：运行 `npm --workspace @gavin/web run test:quality`，确认 Lighthouse accessibility 仍为 100。
5. **类型与构建**：运行 Web 单测、类型检查与生产构建，确认无新增告警或失败。
6. **手动核验**：在本地浏览器浅色与深色模式下，打开含 ```js、```text 与无语言 fence 的正文，切换主题，确认代码块始终可读、token 颜色随主题切换、无闪烁。
7. **变更边界**：`git diff --check` 通过；`git diff --name-only` 不触及 `apps/api`、`packages/contracts`、数据库迁移、`my_blog_fork` 或两个冻结 GitHub spec；不执行 commit 或 push。
8. **Harness 验证**：运行 `python -m tools.harness verify 20260811-light-codeblock-visibility` 通过。
