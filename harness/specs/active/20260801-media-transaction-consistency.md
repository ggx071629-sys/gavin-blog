---
id: spec-20260801-media-transaction-consistency
level: L1
summary: 以批量原子文件发布和数据库失败补偿保证媒体上传一致性
load_when:
  - task:20260801-media-transaction-consistency
task_id: 20260801-media-transaction-consistency
status: verified
---

# Media transaction consistency

## Context

媒体上传先 flush 数据库获得 ID，再把 WebP/AVIF 逐个写入最终目录，最后提交数据库。任一文件写入或数据库提交失败都会留下半成品目录或没有数据库记录的孤儿文件；现有 `MediaStorage.delete()` 从未进入失败路径。

## Goal

使所有可捕获的上传失败保持数据库和媒体存储一致：多个派生文件要么作为完整批次发布，要么全部不可见；数据库无法提交时删除本次随机 key 下的全部文件并回滚事务。

## Non-goals

- 不实现跨数据库与对象存储的分布式两阶段提交。
- 不新增媒体删除 API，也不删除已成功登记且可能被 Markdown 引用的资产。
- 不改变媒体响应结构、公开 URL 或图片转换参数。
- 不在本批建立崩溃后扫描历史孤儿文件的后台任务。

## Acceptance criteria

- 存储协议以一个 key 批量写入全部派生文件；本地实现先写唯一暂存目录，全部成功后在同一文件系统原子发布最终目录。
- 批量写入中途失败会清除暂存内容，最终 key 目录不存在。
- 上传路由在文件系统失败或数据库 flush/commit 失败时回滚 Session，并补偿删除本次随机 key 下的所有文件。
- 补偿清理失败会记录日志但不覆盖原始异常；成功提交后的响应刷新失败不得误删已提交媒体。
- 成功上传、公开读取和外链登记行为保持不变，OpenAPI 契约不变。
- Pytest 通过失败注入验证文件中途失败、存储适配器失败和数据库提交失败均不留下媒体记录或文件。
- API、Web、E2E、构建和 Harness 全量验证通过。

## Risks

- 文件系统与数据库不共享事务，进程在目录发布后、数据库提交前被强制终止仍可能留下孤儿目录；随机 key 使其不会覆盖现有资产，后续可由独立巡检回收。
- 原子目录重命名依赖暂存目录与最终目录位于同一媒体根目录，本地适配器必须维持该约束。
- 补偿删除只允许作用于服务端生成且通过校验的 32 位 key，不能接受用户路径。

## Verification plan

- 单元测试在第二个派生文件写入时注入异常，确认暂存与最终目录均不存在。
- 集成测试分别注入存储失败和 SQLAlchemy commit 失败，确认返回 500、事务回滚且媒体根目录为空。
- 执行媒体测试、API 全量 Pytest、Ruff、OpenAPI 哈希比较、Web Vitest、TypeScript no-emit、隔离 E2E 与 Nuxt 构建。
- 刷新索引并运行 `python -m tools.harness verify 20260801-media-transaction-consistency`。

## Implementation record

- `MediaStorage` 从逐文件写入升级为 key 级批量写入；本地适配器在媒体根目录中写唯一暂存目录，全部派生文件成功后才用目录重命名发布。
- 暂存写入失败会删除暂存目录；清理自身失败只记录原始路径和异常，不覆盖最初的写入错误。
- 上传路由在数据库 flush/commit 或存储失败时回滚 Session，并在 `finally` 中对未提交 key 执行幂等补偿删除；`committed` 边界保证成功提交后的刷新异常不会误删文件。
- 新增 4 个失败路径测试，连同既有成功/验证测试共 6 项，覆盖派生写入中断、适配器部分写入、数据库 commit 失败及补偿删除失败。
- API 全量 32 项、Web 14 项、Playwright 3 项、Ruff、TypeScript no-emit、Nuxt 构建及 OpenAPI 同步均通过；E2E 临时目录无残留。
- Spec 保留在 active 目录：仓库仍无 Git HEAD，无法满足 deterministic close 的历史前置条件。
