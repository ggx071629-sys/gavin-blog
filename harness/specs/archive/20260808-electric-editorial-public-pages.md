---
id: archive-20260808-electric-editorial-public-pages
level: L2
summary: 按 Stitch Electric Editorial 原型完成全部公开内容页面的双主题 UI 重构
load_when:
  - task:20260808-electric-editorial-public-pages
author: Gavin
task_id: 20260808-electric-editorial-public-pages
status: compressed
restoration_source: "c3da86edaddec06b596dabaaad239f61d5e36319:harness/specs/active/20260808-electric-editorial-public-pages.md"
restored_at: 2026-08-11
---

# 20260808-electric-editorial-public-pages

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在不改变 API、数据模型、公开 URL、认证、SEO 契约和业务状态机的前提下，完成全部公开内容列表、详情、归档、关于、搜索与错误页的 Electric Editorial 重构，并在浅色／深色、桌面／移动四象限下可重复验证。

## Acceptance criteria

- 十个公开页面文件和 Nuxt 错误页统一使用第一阶段语义令牌及公共阅读组件，不再依赖页面级 slate／rounded 旧主题表达。
- 文章列表保留栏目、标签、计数、查询参数和分页；桌面采用侧栏索引，移动端安全折叠为可横向换行的筛选区。
- 文章、项目和读书详情保留真实内容、Markdown、外链、参考资料、关联文章、SEO 和 404 行为。
- 项目与读书列表按对应 Stitch 页面建立高密度编辑卡片；缺少封面或 Hero 时提供不伪造内容的排版型占位。
- 归档保留按年分组和分页；搜索保留查询、禁用状态、结果类型、分页、`noindex` 及 hydration 行为。
- 404 提供返回首页、搜索和浏览文章入口，并对浅色／深色分别呈现，而不是简单颜色反转。
- 所有小号文字对所在背景满足 WCAG AA；酸性绿在浅色主题中只承担信号／填充／边框，除非实际对比度达到要求。
- 390px 宽度无横向溢出，交互目标至少 44px，焦点可见，减少动态效果偏好有效。
- 文章列表、文章详情、项目列表／详情、读书列表／详情、归档、关于、搜索和 404 的代表页覆盖四象限视觉检查；适用页面通过 axe A/AA。
- Web 类型检查、Vitest、生产构建、相关 Playwright E2E 和质量门禁通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260808-electric-editorial-public-pages.json](../../verification/evidence/20260808-electric-editorial-public-pages.json)

Closed at 2026-08-09T11:31:50.817210+00:00.
