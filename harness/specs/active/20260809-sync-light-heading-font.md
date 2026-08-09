---
id: spec-20260809-sync-light-heading-font
level: L1
summary: 将浅色主题标题字体统一为深色主题的 Hanken Grotesk
load_when:
  - task:20260809-sync-light-heading-font
author: Gavin
task_id: 20260809-sync-light-heading-font
status: verified
---

# Context

Electric Editorial 初始基线有意让浅色标题使用 Chivo、深色标题使用 Hanken Grotesk。浏览器验证确认两套 Web 字体均会加载，同一拉丁标题在主题切换后会改变计算字体和字形宽度。用户现明确要求以深色主题为准统一标题排版，因此本任务是对既有视觉基线的显式变更，不按偶发字体回退处理。

# Goal

让浅色和深色主题的全部标题字体消费者共同使用 Hanken Grotesk，并移除不再需要的 Chivo 网络字体请求；正文、等宽字体和其他视觉令牌保持不变。

# Non-goals

- 不改变正文 Inter 与等宽 JetBrains Mono 字体栈。
- 不改变字号、字重、行高、字距、颜色、布局、圆角或组件结构。
- 不改变主题切换、导航、认证、API、数据或页面 URL。
- 不借本任务调整 Hanken Grotesk 现有字重集合或重新设计中文字体回退。
- 不改动当前进行中的写作台入口与浅色 signal 色任务文件。

# Acceptance criteria

1. 根主题 `--ee-heading` 使用与当前深色主题一致的 `"Hanken Grotesk", Inter, ui-sans-serif, system-ui, sans-serif` 字体栈。
2. 深色主题不再单独覆盖 `--ee-heading`，避免未来浅色／深色标题字体再次漂移。
3. Nuxt 字体样式表继续加载 Hanken Grotesk、Inter 与 JetBrains Mono，但不再请求无消费者的 Chivo。
4. 浏览器中同一拉丁标题在浅色／深色切换前后的计算 `font-family` 与字形宽度一致。
5. 正文与等宽字体声明保持不变；现有主题切换和公开页面水合行为不因本任务新增回归。
6. 目标单测、全量 Web 单测、类型检查、生产构建及字体主题浏览器检查通过。

# Risks

- Hanken Grotesk 与 Chivo 的字宽不同，浅色页面可能出现标题换行变化；需要在桌面与移动视口检查代表页面无横向溢出。
- Chivo 可能存在未通过 `--ee-heading` 表达的隐式消费者；移除字体请求前必须做全仓检索并以静态测试防回归。
- 当前工作树包含其他 active spec 的未提交修改；本任务必须将差异限制在独立 spec、字体令牌、字体请求与新增测试／evidence，不覆盖相邻任务。

# Verification plan

- 先新增字体令牌静态测试，断言共享 Hanken 字体栈、深色无覆盖、字体请求不含 Chivo，并确认测试在现状下失败。
- 最小修改 `main.css` 与 `nuxt.config.ts`，再运行目标测试和全量 Vitest。
- 运行 Nuxt 类型检查与生产构建。
- 用 Playwright 在浅色／深色下读取同一拉丁标题的计算字体与字形宽度，并在 1440px、390px 视口检查无页面级横向溢出。
- 生成紧凑 application evidence，并从 `harness/` 运行索引生成与 `python -m tools.harness verify 20260809-sync-light-heading-font`。

# Result

浅色与深色标题现共享 Hanken Grotesk 根令牌，深色不再重复覆盖；Chivo 已从运行时字体请求移除。静态守卫、64 项 Vitest、类型检查、生产构建，以及桌面／移动 Playwright 主题切换与横向溢出检查均通过。
