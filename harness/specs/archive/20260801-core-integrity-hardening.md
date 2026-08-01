---
id: archive-20260801-core-integrity-hardening
level: L2
summary: 修复发布一致性、生产配置、SQLite 外键与公开 URL 稳定性
load_when:
  - task:20260801-core-integrity-hardening
task_id: 20260801-core-integrity-hardening
status: compressed
---

# 20260801-core-integrity-hardening

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在不改变现有内容模型与公开路由形状的前提下，使发布动作只发生在最新编辑成功保存之后，使非测试运行时配置安全失败，使 SQLite 外键约束真实生效，并保护三类已发布内容的公开 URL。

## Acceptance criteria

- `AutosaveQueue.flush()` 等待正在执行和随后排队的保存完成；任一最终保存失败时向调用者报告失败，编辑器不得调用发布 API。
- 自动定时保存失败不产生未处理 Promise rejection；失败快照可在后续显式 flush 或新编辑后重试。
- API 不再提供可工作的默认管理员密码；未显式配置环境时采用生产安全默认，生产环境拒绝弱默认密码与非 Secure Cookie。
- Session TTL、登录限流与媒体大小配置拒绝零值或负值；带凭据 CORS 拒绝通配来源。
- API 创建的每个 SQLite 连接都启用 `PRAGMA foreign_keys=ON`，并由集成测试验证。
- 已发布文章、项目和读书笔记修改 slug 返回 `409`；未发布草稿仍可修改 slug，已发布内容的其他字段仍可更新。
- Pytest、Vitest、Ruff、TypeScript no-emit、OpenAPI 同步检查与 Harness verify 通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260801-core-integrity-hardening.json](../../verification/evidence/20260801-core-integrity-hardening.json)

Closed at 2026-08-01T16:42:42.282997+00:00.
