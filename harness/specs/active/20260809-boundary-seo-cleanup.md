---
id: spec-20260809-boundary-seo-cleanup
level: L1
summary: 收敛孵化日期与分页边界，并修复 Mermaid 主题降级和搜索结构化数据
load_when:
  - task:20260809-boundary-seo-cleanup
author: Codex
task_id: 20260809-boundary-seo-cleanup
status: active
---

# Context

批次 7 覆盖 AUD-17～AUD-20：孵化列表将日期上限发送为当日 `23:59:59Z` 且 API 使用包含比较，会遗漏最后一秒的微秒记录；全局 `MAX_PAGE=5001` 只适合 20 条分页，12 条公开列表会提前截断；Mermaid 只在内容变化时渲染，且无效源码会抛出未处理异常；首页 SearchAction 的 target 占位符与 `query-input` 参数名不一致。

# Goal

以最小共享边界消除四个低频正确性缺陷：日期上限改为次日零点排他语义，页码上限由 page size 和 API max offset 推导，Mermaid 可随 resolved theme 独立重绘并就地降级，SearchAction 契约与实际 `/search?q=` 一致。

# Non-goals

- 不将 offset pagination 改造为 cursor pagination，不调整 API 的 `offset<=100000` 边界。
- 不重做孵化筛选 UI、Markdown 解析器或全站 SEO 架构。
- 不在主题切换时重新解析整篇 Markdown。
- 不修改两个既有 GitHub active spec，不预建后续 spec。

# Acceptance criteria

1. inbox、audits、drafts 和 tasks 的结束日期统一传次日 `00:00:00Z`；对应 sources、audits、drafts 和 jobs API 对上限使用排他 `< created_to`。
2. API 可执行测试证明当日 `23:59:59.000000`、`.000001`、`.999999` 均被包含，次日 `00:00:00.000000` 被排除；前端日期转换不受本地时区偏移影响。
3. 页码上限使用 `floor(maxOffset / pageSize) + 1` 推导；12 条页可访问 offset 99996，20 条页可访问 offset 100000，更大/无效页码稳定收敛到规范页。
4. 所有分页消费者显式使用其 endpoint page size；请求不依赖隐式 `Math.min` 把越界页压到重复 offset。
5. Mermaid 仅在 Markdown 内容变化时重新解析文章；resolved light/dark 变化时使用原图源码重绘节点，快速切换不留下旧主题结果。
6. 无效 Mermaid 只显示局部 `role=alert` 错误与可选择/复制的转义源码，页面不产生未处理 Promise rejection；有效图在 light/dark 切换后均可读。
7. 首页 WebSite JSON-LD 的 SearchAction target 和 `query-input` 统一为 `search_term_string`，且 target 仍映射实际 `/search?q=`；schema 单测/E2E 阻断参数漂移。

# Risks

- 把包含上限改为排他上限会影响直接 API 调用者；前后端必须同批切换，并用边界数据固化语义。
- 页码规范化若在 route watch 中反复写回可造成导航循环；只在原始查询与规范值不同时 replace。
- Mermaid 是异步渲染；需要丢弃已过期结果，并隔离单个图的解析失败。
- 降级 HTML 来自用户 Markdown，必须转义源码，不允许无效 Mermaid 变成 HTML 注入。

# Verification plan

1. Vitest 覆盖次日 UTC 边界、page size 12/20 的最大页/offset、越界规范化和 SearchAction schema。
2. API 集成测试在 sources、audits、drafts、jobs 中插入微秒边界数据，验证排他上限与 OpenAPI 契约。
3. Playwright 用有效/无效 Mermaid 验证 light/dark 重绘、局部 fallback、源码可复制与零 pageerror/console error；验证越界页码 URL 收敛。
4. 运行 API lint/相关测试、Web typecheck/unit/build/相关 E2E 及完整 `npm run quality:release`。
5. 从 `harness/` 运行 verify；全部通过后用确定性 close 命令归档本 spec。
