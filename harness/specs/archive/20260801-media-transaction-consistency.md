---
id: archive-20260801-media-transaction-consistency
level: L2
summary: 以批量原子文件发布和数据库失败补偿保证媒体上传一致性
load_when:
  - task:20260801-media-transaction-consistency
task_id: 20260801-media-transaction-consistency
status: compressed
---

# 20260801-media-transaction-consistency

Deterministic compressed record. The original active spec remains in Git history.

## Goal

使所有可捕获的上传失败保持数据库和媒体存储一致：多个派生文件要么作为完整批次发布，要么全部不可见；数据库无法提交时删除本次随机 key 下的全部文件并回滚事务。

## Acceptance criteria

- 存储协议以一个 key 批量写入全部派生文件；本地实现先写唯一暂存目录，全部成功后在同一文件系统原子发布最终目录。
- 批量写入中途失败会清除暂存内容，最终 key 目录不存在。
- 上传路由在文件系统失败或数据库 flush/commit 失败时回滚 Session，并补偿删除本次随机 key 下的所有文件。
- 补偿清理失败会记录日志但不覆盖原始异常；成功提交后的响应刷新失败不得误删已提交媒体。
- 成功上传、公开读取和外链登记行为保持不变，OpenAPI 契约不变。
- Pytest 通过失败注入验证文件中途失败、存储适配器失败和数据库提交失败均不留下媒体记录或文件。
- API、Web、E2E、构建和 Harness 全量验证通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260801-media-transaction-consistency.json](../../verification/evidence/20260801-media-transaction-consistency.json)

Closed at 2026-08-01T16:43:15.553995+00:00.
