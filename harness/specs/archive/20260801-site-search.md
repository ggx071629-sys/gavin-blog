---
id: archive-20260801-site-search
level: L2
summary: 使用 SQLite FTS5 提供覆盖已发布内容与文章分类信息的全站搜索闭环
load_when:
  - task:20260801-site-search
author: Gavin
task_id: 20260801-site-search
status: compressed
---

# 20260801-site-search

Deterministic compressed record. The original active spec remains in Git history.

## Goal

读者可以从统一搜索页检索已发布的文章、项目和读书笔记；文章的栏目与标签名称也能命中对应文章。

## Acceptance criteria

- Alembic 创建 FTS5 虚拟表并为已有已发布内容建立索引。
- 新发布或更新的文章、项目和读书笔记会同步索引；文章栏目与标签文本进入索引。
- 公开搜索 API 接受长度受限的查询，返回类型、标题、摘要、公开路径、片段和相关度。
- 草稿、已删除内容及其分类信息永不出现在公开搜索结果中。
- Nuxt 提供 `/search` 页面、主导航入口、加载/空结果状态和可访问的搜索表单。
- Pytest 覆盖迁移、跨内容检索、分类命中、索引同步与公开隔离；OpenAPI 和 TypeScript 契约同步。

## Result

Verified and closed by the harness close command.

## Evidence

[20260801-site-search.json](../../verification/evidence/20260801-site-search.json)

Closed at 2026-08-01T16:44:09.865515+00:00.
