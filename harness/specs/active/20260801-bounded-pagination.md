---
id: spec-20260801-bounded-pagination
level: L1
summary: 为高增长内容列表建立有界查询、稳定排序和完整消费者分批读取
load_when:
  - task:20260801-bounded-pagination
task_id: 20260801-bounded-pagination
status: verified
---

# Bounded pagination

## Context

文章、项目、读书笔记、媒体和回收站列表当前会一次读取全部记录；公开搜索虽限制返回数量，但不能翻页。数据增长后，这些端点会造成无界数据库读取、响应体和浏览器内存占用。首页、RSS、站点地图与项目关联选择又共享这些端点，直接增加默认上限会令必须完整或固定数量的消费者静默缺失内容。

## Goal

为所有高增长列表提供统一且有上限的 `limit`/`offset` 查询，保留现有数组响应以减少契约破坏；普通页面提供稳定翻页，固定数量和完整集合消费者明确声明自己的读取语义。

## Non-goals

- 不改变栏目和标签等低基数配置列表。
- 不改变 Markdown 完整导出的产品语义或 ZIP 内存模型。
- 不引入总数查询、响应 envelope、游标令牌或无限滚动。
- 不改变现有内容模型、迁移或公开详情 URL。

## Acceptance criteria

- 文章、项目、读书笔记的公开与管理列表、管理媒体、统一回收站均接受 `limit`（默认 20，1–100）和 `offset`（默认 0，0–100000）。
- 搜索保留单页最多 50 条并新增相同 offset 边界；所有端点的负数、零值、超上限值返回 422。
- 所有分页查询在数据库层应用 limit/offset，并使用业务时间降序加 ID 降序作为稳定顺序；关联关系通过批量加载避免分页内 N+1。
- 回收站通过三类内容的 SQL 联合查询完成全局排序和数据库级分页，不在 Python 中读取全部记录后排序。
- 公开文章、项目、读书和归档页，管理文章、项目、读书和回收站页，以及搜索页提供上一页／下一页；筛选和搜索换页时保留当前条件，新条件从第一页开始。
- 媒体选择器每次只读取一页并提供“加载更多”；上传或登记成功后重置到最新第一页。
- 首页只请求最近 4 篇文章；RSS 只请求最近 50 篇；站点地图和项目编辑器文章选择按 100 条一批读取至完整集合。
- OpenAPI 快照和生成契约同步，API、Web、E2E、构建与 Harness 全量验证通过。

## Risks

- offset 分页在并发插入时可能发生跨页漂移；稳定次序可消除同时间戳歧义，但不提供快照隔离。当前单管理员、低写入频率场景接受该权衡。
- 保持数组响应意味着没有总数；页面通过请求 `pageSize + 1` 判断下一页，显示的是当前页数量而非总数。
- 完整消费者需循环多次调用；批次硬上限把单次资源占用限制在 100 条，并避免默认上限造成静默截断。

## Verification plan

- Pytest 覆盖默认上限、limit/offset 验证、稳定跨页顺序、搜索翻页、回收站联合分页以及媒体列表分页。
- Vitest 覆盖页码规范化、查询拼接、分页切片和分批完整读取。
- 检查 OpenAPI 参数边界并重新生成 `packages/contracts/openapi.json` 与派生类型。
- 执行 API 全量 Pytest、Ruff、Web Vitest、TypeScript no-emit、隔离 E2E 与 Nuxt 构建。
- 刷新索引并运行 `python -m tools.harness verify 20260801-bounded-pagination`。

## Implementation record

- 新增统一分页类型，八个高增长内容／媒体／回收站列表采用默认 20、最多 100 条的 limit/offset；搜索保留最多 50 条并支持 offset，所有 offset 上限为 100000。
- 普通 ORM 列表在数据库层分页，并以业务时间和 ID 降序稳定排序；文章与项目列表使用 select-in 批量加载关系。
- 回收站改为文章、读书笔记、项目三路 `UNION ALL` 后统一排序、limit 和 offset，不再加载三张表的全部删除记录。
- 新增复用分页工具与导航组件；公开文章、项目、读书、归档、搜索和管理文章、项目、读书、回收站均可前后翻页，媒体库支持分批加载更多。
- 首页固定读取最近 4 篇，RSS 固定读取最近 50 篇；站点地图和项目关联文章选择器按 100 条批次读取至完整集合，超出支持窗口时明确失败而非静默截断。
- 新增 13 项 API 分页回归测试、5 项 Web 分页工具测试，并在 E2E 中真实创建超过一页的管理文章后验证下一页和上一页。
- API 全量 53 项、Web 19 项、Playwright 3 项、Ruff、TypeScript no-emit、Nuxt 构建及 OpenAPI 参数边界均通过；E2E 临时目录无残留。
- OpenAPI SHA256 从 `8CF749D220217EAD76887659E1825A0530AE57B6BFF4B702DCE2FCE2BD4CF4AB` 变为预期的 `9AD9CBF8FB22D4F1EF5567FA27BA095C0E73E62FBBA96E5827A1947794686A91`。
- Spec 保留在 active 目录：仓库仍无 Git HEAD，无法满足 deterministic close 的历史前置条件。
