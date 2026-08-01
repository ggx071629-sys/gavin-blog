---
id: spec-20260801-seo-discovery
level: L1
summary: 为全部公开内容补齐规范元数据、结构化数据、RSS、站点地图与爬虫入口
load_when:
  - task:20260801-seo-discovery
author: Gavin
task_id: 20260801-seo-discovery
status: verified
---

# SEO and discovery

## Context

第三阶段公共体验基线已经验证，产品基线要求的 RSS、站点地图、规范链接、Open Graph 与结构化数据尚未形成完整输出。现有页面只有零散标题和描述，内容详情缺少可解析实体信息，爬虫也没有稳定发现入口。

## Goal

搜索引擎、阅读器和链接预览服务能够发现全部公开内容，并从每个公开页面获得唯一规范地址、完整社交元数据和与页面类型一致的 JSON-LD。

## Non-goals

- 搜索引擎提交、站长平台验证或线上域名部署。
- 为草稿、预览、管理后台或搜索结果建立索引。
- 新增数据库字段、摘要生成或站内推荐算法。
- 在缺少可验证成品时发布占位社交图片。

## Acceptance criteria

- 所有公共页面输出基于 `NUXT_PUBLIC_SITE_URL` 的绝对 canonical，并包含 Open Graph 站点名、页面标题、描述、类型与 URL。
- 首页输出 `WebSite` JSON-LD；文章、项目和读书笔记详情分别输出 `BlogPosting`、`CreativeWork` 与 `Review`／`Book` 结构化数据。
- 管理后台、草稿预览与站内搜索结果声明 `noindex`；公开集合页保持可索引。
- `/rss.xml` 输出已发布文章的 RSS 2.0，包含稳定绝对链接、摘要、发布时间和更新时间。
- `/sitemap.xml` 覆盖静态公共页面及已发布文章、项目和读书笔记，并携带可用的最后修改时间。
- `/robots.txt` 允许公开抓取、阻止管理与预览路径，并指向绝对站点地图 URL。
- XML 对标题、摘要和 URL 中的特殊字符进行安全转义；API 或草稿数据不会泄漏到公开输出。
- Vitest 覆盖 URL 规范化、XML 转义、RSS 与站点地图生成；Playwright 验证关键页面元数据与发现端点。

## Risks

- 站点 URL 配置不规范可能生成双斜杠或相对 canonical，因此统一去除尾斜杠并只接受绝对 HTTP(S) 基址。
- XML 特殊字符可能破坏订阅与抓取，因此所有文本和属性值经过同一转义函数。
- JSON-LD 若直接拼接 HTML 可能引入脚本边界问题，因此通过 Nuxt head API 序列化结构化对象。
- 社交图生成若文本不准确或资产不可用，将省略 `og:image`，不发布通用占位图。

## Verification plan

- 先以 Vitest 描述 URL 与 XML 输出，再实现纯生成函数。
- Playwright 请求三个发现端点，并检查首页与代表性详情页的 canonical、Open Graph、robots 和 JSON-LD。
- 执行类型检查、现有单元测试、E2E 与生产构建。
- 刷新 harness 索引并运行 `python -m tools.harness verify 20260801-seo-discovery`。

## Implementation record

- 新增统一 `useSiteSeo` composable，为公开页面输出绝对 canonical、Open Graph、Twitter 摘要卡与 RSS 发现链接；管理后台和搜索结果使用 `noindex`。
- 首页、集合页及三类详情页分别输出 `WebSite`、`CollectionPage`、`BlogPosting`、`CreativeWork` 与 `Review`／`Book` JSON-LD。
- Nitro 新增 `/rss.xml`、`/sitemap.xml` 和 `/robots.txt`；RSS 与站点地图只读取公开 API，并使用经过测试的 URL 规范化和 XML 转义。
- 专属社交图按构建流程发起一次生成，但图像服务发生网络错误，未得到可验证资产；因此遵循规格省略 `og:image`，未发布占位图。
- Vitest XML／URL 测试、类型检查、生产构建和 Playwright 发布后发现旅程均通过。
- Spec 保留在 active 目录：仓库仍无 Git HEAD，无法满足 deterministic close 的历史前置条件。
