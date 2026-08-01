---
id: decision-utc-time-semantics
level: L1
summary: 瞬时时间在应用边界统一为 UTC-aware，SQLite 无偏移旧值按 UTC 解释
load_when:
  - datetime-change
  - persistence-change
  - api-time-contract
  - architecture-decision
author: Gavin
---

# Decision 0002: UTC time semantics

## Status

Accepted.

## Decision

所有表示瞬间的 Python `datetime` 在应用与 API 边界必须携带 UTC 时区。SQLite 仍以无偏移 `DATETIME` 保存 UTC，以兼容已有数据库；SQLAlchemy 自定义类型在写入时转换到 UTC，在 SQLite 绑定时移除偏移，并在读取时恢复 UTC 时区。历史无偏移值按 UTC 解释，因为它们由旧版 `datetime.utcnow()` 产生。

`reading_date` 等纯日期不应用此策略。登录限流继续使用单调时钟。文章和读书笔记的年月公开路径使用发布时间的 UTC 年月，避免改变已有 URL 语义。

## Consequences

- API ISO 8601 时间携带 `Z` 或 `+00:00`，浏览器和外部消费者可无歧义解析。
- Session 与当前时间始终为同类 UTC-aware 对象，旧记录不会导致比较异常。
- SQLite 无需破坏性迁移；未来使用支持时区的数据库方言时保存有偏移值。
- 无法自动纠正曾由人工写入且实际代表本地时间的历史无偏移值，此类数据必须显式修正。
