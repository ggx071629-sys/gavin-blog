---
id: spec-20260801-site-search
level: L1
summary: 使用 SQLite FTS5 提供覆盖已发布内容与文章分类信息的全站搜索闭环
load_when:
  - task:20260801-site-search
author: Gavin
task_id: 20260801-site-search
status: verified
---

# Site search

## Context

第二阶段已经具备文章、栏目、标签、项目与读书笔记。产品基线要求使用 SQLite FTS5 提供全站搜索，并确保公开读取边界不泄露草稿。

## Goal

读者可以从统一搜索页检索已发布的文章、项目和读书笔记；文章的栏目与标签名称也能命中对应文章。

## Non-goals

- 拼写纠正、语义向量搜索、搜索建议和搜索分析。
- 管理端草稿搜索。
- 独立展示栏目或标签详情作为搜索结果。

## Acceptance criteria

- Alembic 创建 FTS5 虚拟表并为已有已发布内容建立索引。
- 新发布或更新的文章、项目和读书笔记会同步索引；文章栏目与标签文本进入索引。
- 公开搜索 API 接受长度受限的查询，返回类型、标题、摘要、公开路径、片段和相关度。
- 草稿、已删除内容及其分类信息永不出现在公开搜索结果中。
- Nuxt 提供 `/search` 页面、主导航入口、加载/空结果状态和可访问的搜索表单。
- Pytest 覆盖迁移、跨内容检索、分类命中、索引同步与公开隔离；OpenAPI 和 TypeScript 契约同步。

## Risks

- FTS 索引可能与业务表漂移，因此写路径必须集中调用幂等同步函数，搜索前也能安全补齐虚拟表。
- FTS 查询语法可被畸形输入触发错误，因此服务端将用户文本转换为安全的前缀词项。
- 摘要片段可能包含标记，因此 API 返回纯文本，前端不使用任意 HTML。

## Verification plan

- 在空 SQLite 数据库执行 Alembic 到 head，并确认 FTS5 表存在。
- Pytest 执行搜索集成测试和既有回归。
- Vitest、Nuxt typecheck、生产构建与 Playwright 搜索闭环通过。
- 重新生成 OpenAPI 快照并运行 Harness verify。

## Implementation record

- Alembic 增加 FTS5 虚拟表并迁移已有已发布内容；API 写路径使用幂等同步函数维护索引。
- 公开搜索覆盖文章标题/摘要/正文/栏目/标签、项目和读书笔记作者，返回类型、路径、纯文本片段与 BM25 分数。
- 所有公开查询、分类计数和项目关联均排除草稿与回收站内容。
- Nuxt `/search` 页面和主导航已接入；Pytest 搜索集成测试及 Playwright 真实搜索闭环通过。
