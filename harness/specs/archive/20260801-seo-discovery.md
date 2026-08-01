---
id: archive-20260801-seo-discovery
level: L2
summary: 为全部公开内容补齐规范元数据、结构化数据、RSS、站点地图与爬虫入口
load_when:
  - task:20260801-seo-discovery
author: Gavin
task_id: 20260801-seo-discovery
status: compressed
---

# 20260801-seo-discovery

Deterministic compressed record. The original active spec remains in Git history.

## Goal

搜索引擎、阅读器和链接预览服务能够发现全部公开内容，并从每个公开页面获得唯一规范地址、完整社交元数据和与页面类型一致的 JSON-LD。

## Acceptance criteria

- 所有公共页面输出基于 `NUXT_PUBLIC_SITE_URL` 的绝对 canonical，并包含 Open Graph 站点名、页面标题、描述、类型与 URL。
- 首页输出 `WebSite` JSON-LD；文章、项目和读书笔记详情分别输出 `BlogPosting`、`CreativeWork` 与 `Review`／`Book` 结构化数据。
- 管理后台、草稿预览与站内搜索结果声明 `noindex`；公开集合页保持可索引。
- `/rss.xml` 输出已发布文章的 RSS 2.0，包含稳定绝对链接、摘要、发布时间和更新时间。
- `/sitemap.xml` 覆盖静态公共页面及已发布文章、项目和读书笔记，并携带可用的最后修改时间。
- `/robots.txt` 允许公开抓取、阻止管理与预览路径，并指向绝对站点地图 URL。
- XML 对标题、摘要和 URL 中的特殊字符进行安全转义；API 或草稿数据不会泄漏到公开输出。
- Vitest 覆盖 URL 规范化、XML 转义、RSS 与站点地图生成；Playwright 验证关键页面元数据与发现端点。

## Result

Verified and closed by the harness close command.

## Evidence

[20260801-seo-discovery.json](../../verification/evidence/20260801-seo-discovery.json)

Closed at 2026-08-01T16:44:01.855754+00:00.
