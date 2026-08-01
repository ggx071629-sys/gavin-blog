---
id: spec-20260801-core-integrity-hardening
level: L1
summary: 修复发布一致性、生产配置、SQLite 外键与公开 URL 稳定性
load_when:
  - task:20260801-core-integrity-hardening
task_id: 20260801-core-integrity-hardening
status: verified
---

# Core integrity hardening

## Context

全项目审查发现四个阻断级风险：自动保存失败或仍在执行时仍可能继续发布；运行时配置在遗漏生产环境标志时允许已知默认密码与非安全 Cookie；SQLite 连接未启用外键；已发布内容仍可修改 slug 并破坏公开地址。

## Goal

在不改变现有内容模型与公开路由形状的前提下，使发布动作只发生在最新编辑成功保存之后，使非测试运行时配置安全失败，使 SQLite 外键约束真实生效，并保护三类已发布内容的公开 URL。

## Non-goals

- 本批不实现分页、媒体 URL 迁移、时区迁移或 Markdown 导入重构。
- 不新增部署、CI、重定向表或 slug 历史表。
- 不改变现有 OpenAPI 路径和成功响应模型。

## Acceptance criteria

- `AutosaveQueue.flush()` 等待正在执行和随后排队的保存完成；任一最终保存失败时向调用者报告失败，编辑器不得调用发布 API。
- 自动定时保存失败不产生未处理 Promise rejection；失败快照可在后续显式 flush 或新编辑后重试。
- API 不再提供可工作的默认管理员密码；未显式配置环境时采用生产安全默认，生产环境拒绝弱默认密码与非 Secure Cookie。
- Session TTL、登录限流与媒体大小配置拒绝零值或负值；带凭据 CORS 拒绝通配来源。
- API 创建的每个 SQLite 连接都启用 `PRAGMA foreign_keys=ON`，并由集成测试验证。
- 已发布文章、项目和读书笔记修改 slug 返回 `409`；未发布草稿仍可修改 slug，已发布内容的其他字段仍可更新。
- Pytest、Vitest、Ruff、TypeScript no-emit、OpenAPI 同步检查与 Harness verify 通过。

## Risks

- 自动保存队列的并发状态处理不当可能造成死锁、重复保存或吞掉错误，因此必须用可控 Promise 覆盖进行中保存与排队保存。
- 收紧配置可能暴露依赖旧默认值的本地脚本；开发与测试环境必须继续通过显式配置启动。
- 启用 SQLite 外键可能暴露既有孤儿数据；本批只保证新连接执行约束，不自动清理现有数据库。
- 禁止已发布 slug 变化会改变当前后台行为，但优先保护既有公开链接；重定向能力留给独立 spec。

## Verification plan

- Vitest 覆盖保存失败传播、失败重试、进行中保存等待与最新快照排空。
- Pytest 覆盖配置安全默认与校验、SQLite 外键开关、三类内容发布后 slug 冲突及草稿 slug 可编辑。
- 执行 API 全量测试、Ruff、Web 单元测试与 TypeScript no-emit。
- 在内存中比较当前 OpenAPI 与契约快照，并运行不写 evidence 的 Harness verify。

## Implementation record

- 自动保存队列现在串行排空进行中与最新快照，失败会保留待重试内容并向发布动作传播；定时保存显式吸收已记录错误，避免未处理 rejection。
- 运行时配置改为生产安全默认，管理员密码必须显式提供，数值限制和带凭据 CORS 在启动前校验；FastAPI 改用应用工厂入口，测试导入不再触发隐式配置加载。
- SQLite 应用连接统一启用外键，并用真实关联表非法写入验证约束生效。
- 三类已发布内容拒绝 slug 变化，草稿 slug 与已发布内容的其他字段仍可更新。
- API 23 项、Web 14 项、Ruff、TypeScript no-emit、Nuxt 生产构建、34 路径 OpenAPI 同步及 Harness checks 均通过。
