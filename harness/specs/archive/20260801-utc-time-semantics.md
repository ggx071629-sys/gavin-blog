---
id: archive-20260801-utc-time-semantics
level: L2
summary: 统一认证、内容、搜索和导出路径的 UTC 时间语义
load_when:
  - task:20260801-utc-time-semantics
task_id: 20260801-utc-time-semantics
status: compressed
---

# 20260801-utc-time-semantics

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在不重写已有 SQLite 时间值和不移动既有公开 URL 的前提下，将所有瞬时时间统一为 UTC-aware 应用语义，使认证比较安全、API 序列化明确、搜索与导出一致。

## Acceptance criteria

- 统一时钟返回带 UTC 时区的 `datetime`，不再调用已弃用的 `datetime.utcnow()`。
- 所有 ORM 瞬时列写入前归一化为 UTC；SQLite 继续存储兼容的无偏移 UTC 值，读取时统一返回 UTC-aware 对象。
- 已有无时区数据库值按 UTC 解释；过期 Session 被正常拒绝而不发生 naive/aware 比较异常。
- API 中所有非空瞬时时间携带明确的 UTC 偏移，前端 `Date` 不再按本地墙上时间误读。
- 带非 UTC 偏移的输入在持久化后归一化为 UTC；文章和读书笔记年月路径按 UTC 日历生成，保持旧行为语义。
- 搜索索引中的旧无偏移发布时间在响应时也归一化为 UTC；Markdown 导出时间包含 UTC 偏移。
- API 全量测试、Ruff、OpenAPI 契约比较、Web 测试、类型检查、E2E、生产构建与 Harness 验证通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260801-utc-time-semantics.json](../../verification/evidence/20260801-utc-time-semantics.json)

Closed at 2026-08-01T16:44:17.787215+00:00.
