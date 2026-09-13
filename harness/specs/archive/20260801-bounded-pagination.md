---
id: archive-20260801-bounded-pagination
level: L2
summary: 为高增长内容列表建立有界查询、稳定排序和完整消费者分批读取
load_when:
  - task:20260801-bounded-pagination
task_id: 20260801-bounded-pagination
status: compressed
---

# 20260801-bounded-pagination

Deterministic compressed record. The original active spec remains in Git history.

## Goal

为所有高增长列表提供统一且有上限的 `limit`/`offset` 查询，保留现有数组响应以减少契约破坏；普通页面提供稳定翻页，固定数量和完整集合消费者明确声明自己的读取语义。

## Acceptance criteria

- 文章、项目、读书笔记的公开与管理列表、管理媒体、统一回收站均接受 `limit`（默认 20，1–100）和 `offset`（默认 0，0–100000）。
- 搜索保留单页最多 50 条并新增相同 offset 边界；所有端点的负数、零值、超上限值返回 422。
- 所有分页查询在数据库层应用 limit/offset，并使用业务时间降序加 ID 降序作为稳定顺序；关联关系通过批量加载避免分页内 N+1。
- 回收站通过三类内容的 SQL 联合查询完成全局排序和数据库级分页，不在 Python 中读取全部记录后排序。
- 公开文章、项目、读书和归档页，管理文章、项目、读书和回收站页，以及搜索页提供上一页／下一页；筛选和搜索换页时保留当前条件，新条件从第一页开始。
- 媒体选择器每次只读取一页并提供“加载更多”；上传或登记成功后重置到最新第一页。
- 首页只请求最近 4 篇文章；RSS 只请求最近 50 篇；站点地图和项目编辑器文章选择按 100 条一批读取至完整集合。
- OpenAPI 快照和生成契约同步，API、Web、E2E、构建与 Harness 全量验证通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260801-bounded-pagination.json](../../verification/evidence/20260801-bounded-pagination.json)

Closed at 2026-08-01T16:41:29.026308+00:00.
