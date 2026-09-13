---
id: archive-20260809-boundary-seo-cleanup
level: L2
summary: 收敛孵化日期与分页边界，并修复 Mermaid 主题降级和搜索结构化数据
load_when:
  - task:20260809-boundary-seo-cleanup
author: Codex
task_id: 20260809-boundary-seo-cleanup
status: compressed
restoration_source: "6db023ee5e5710b9ca2f2092306a6057aa57d82b:harness/specs/active/20260809-boundary-seo-cleanup.md"
restored_at: 2026-08-11
---

# 20260809-boundary-seo-cleanup

Deterministic compressed record. The original active spec remains in Git history.

## Goal

以最小共享边界消除四个低频正确性缺陷：日期上限改为次日零点排他语义，页码上限由 page size 和 API max offset 推导，Mermaid 可随 resolved theme 独立重绘并就地降级，SearchAction 契约与实际 `/search?q=` 一致。

## Acceptance criteria

1. inbox、audits、drafts 和 tasks 的结束日期统一传次日 `00:00:00Z`；对应 sources、audits、drafts 和 jobs API 对上限使用排他 `< created_to`。
2. API 可执行测试证明当日 `23:59:59.000000`、`.000001`、`.999999` 均被包含，次日 `00:00:00.000000` 被排除；前端日期转换不受本地时区偏移影响。
3. 页码上限使用 `floor(maxOffset / pageSize) + 1` 推导；12 条页可访问 offset 99996，20 条页可访问 offset 100000，更大/无效页码稳定收敛到规范页。
4. 所有分页消费者显式使用其 endpoint page size；请求不依赖隐式 `Math.min` 把越界页压到重复 offset。
5. Mermaid 仅在 Markdown 内容变化时重新解析文章；resolved light/dark 变化时使用原图源码重绘节点，快速切换不留下旧主题结果。
6. 无效 Mermaid 只显示局部 `role=alert` 错误与可选择/复制的转义源码，页面不产生未处理 Promise rejection；有效图在 light/dark 切换后均可读。
7. 首页 WebSite JSON-LD 的 SearchAction target 和 `query-input` 统一为 `search_term_string`，且 target 仍映射实际 `/search?q=`；schema 单测/E2E 阻断参数漂移。

## Result

Verified and closed by the harness close command.

## Evidence

[20260809-boundary-seo-cleanup.json](../../verification/evidence/20260809-boundary-seo-cleanup.json)

Closed at 2026-08-11T10:56:03.986719+00:00.
