---
id: spec-20260801-utc-time-semantics
level: L1
summary: 统一认证、内容、搜索和导出路径的 UTC 时间语义
load_when:
  - task:20260801-utc-time-semantics
task_id: 20260801-utc-time-semantics
status: verified
---

# UTC time semantics

## Context

API 的模型、Session 过期、内容发布与删除均使用无时区 `datetime.utcnow()`，SQLite 读取也返回无时区对象。API 因此输出不带偏移的 ISO 字符串，浏览器会按本地时间解释；若逐处改成有时区时间，又会让旧 Session 比较发生 naive/aware `TypeError`。文章和读书笔记的年月 URL 也依赖发布时间的日历语义。

## Goal

在不重写已有 SQLite 时间值和不移动既有公开 URL 的前提下，将所有瞬时时间统一为 UTC-aware 应用语义，使认证比较安全、API 序列化明确、搜索与导出一致。

## Non-goals

- 不把日期型 `reading_date` 转换成瞬时时间。
- 不引入用户可配置展示时区或修改浏览器本地化显示偏好。
- 不改变登录限流使用的单调时钟。
- 不迁移 SQLite 物理列类型，也不重建已有搜索索引。

## Acceptance criteria

- 统一时钟返回带 UTC 时区的 `datetime`，不再调用已弃用的 `datetime.utcnow()`。
- 所有 ORM 瞬时列写入前归一化为 UTC；SQLite 继续存储兼容的无偏移 UTC 值，读取时统一返回 UTC-aware 对象。
- 已有无时区数据库值按 UTC 解释；过期 Session 被正常拒绝而不发生 naive/aware 比较异常。
- API 中所有非空瞬时时间携带明确的 UTC 偏移，前端 `Date` 不再按本地墙上时间误读。
- 带非 UTC 偏移的输入在持久化后归一化为 UTC；文章和读书笔记年月路径按 UTC 日历生成，保持旧行为语义。
- 搜索索引中的旧无偏移发布时间在响应时也归一化为 UTC；Markdown 导出时间包含 UTC 偏移。
- API 全量测试、Ruff、OpenAPI 契约比较、Web 测试、类型检查、E2E、生产构建与 Harness 验证通过。

## Risks

- SQLite 不保存时区信息，因此必须在单一 SQLAlchemy 类型边界完成双向归一化，不能依赖驱动行为。
- 已有值究竟代表 UTC 还是本地时间不可从数据本身判断；由于旧代码由 `utcnow()` 生成，本规格明确按 UTC 解释。
- 公开 URL 采用发布时间的 UTC 年月；若改用展示时区会移动临近月界的 URL，因此本批不改变该规则。

## Verification plan

- 单元/集成测试覆盖 UTC 时钟、SQLite 旧无时区值读取、非 UTC 偏移写入归一化和 Session 过期比较。
- API 测试覆盖创建、发布、搜索与 Markdown 导出的 UTC 序列化，以及月界发布时间的稳定公开路径。
- 运行 API 全量 Pytest、Ruff、OpenAPI 比较、Web Vitest、TypeScript no-emit、Playwright E2E 与 Nuxt 生产构建。
- 刷新索引并运行 `python -m tools.harness verify 20260801-utc-time-semantics`。

## Implementation record

- 新增 `UTCDateTime` SQLAlchemy 类型：带偏移输入先转为 UTC，SQLite 绑定保持原有无偏移存储格式，所有读取值恢复为 UTC-aware；`utc_now()` 成为唯一当前时间来源。
- 分类、标签、三类内容、媒体和 Session 的全部瞬时字段迁移到统一类型；发布、更新、删除、Session 过期和导出文件名不再调用 `datetime.utcnow()`。
- FTS 搜索结果对历史无偏移 ISO 时间执行同一 UTC 归一化，旧索引无需重建即可输出明确偏移。
- 决策 0002 固化了历史无偏移值按 UTC 解释、日期字段不转换、年月路径使用 UTC 日历且 SQLite 无需物理迁移的边界。
- 新增 5 项测试覆盖旧 Session、SQLite 偏移归一化、月界 URL、API／搜索／Markdown UTC 输出和旧 FTS 值；API 全量 28 项、Web 14 项、Playwright 3 项、Ruff、TypeScript no-emit、Nuxt 构建及 OpenAPI 同步均通过。
- Spec 保留在 active 目录：仓库仍无 Git HEAD，无法满足 deterministic close 的历史前置条件。
