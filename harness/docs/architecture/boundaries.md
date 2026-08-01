---
id: architecture-boundaries
level: L1
summary: 当前已确认的应用、配置、存储、契约和部署边界
load_when:
  - architecture
  - cross-stack-change
  - deployment
author: Gavin
---

# Architecture boundaries

- `apps/web/` 拥有浏览器交互与呈现。
- `apps/api/` 拥有业务规则、认证、搜索、持久化与媒体协调。
- `packages/contracts/` 只承载跨端契约。
- 配置必须外置，业务代码不得假设具体部署平台。
- 媒体访问通过适配器隔离本地文件系统与未来对象存储。
- SQLite 是当前数据库；迁移只能通过 Alembic 演进。
- 浏览器只通过 `/api/v1` REST 契约访问数据；契约快照位于 `packages/contracts/openapi.json`。
- 认证状态由 API 端持久化 Session 掌管，Web 端不保存认证令牌。
- 文章自动保存使用版本号乐观锁；版本冲突由 API 明确返回 `409`。
- 在部署方案形成独立 spec 前，不创建 `infra/`、`deploy/` 或存储实现目录。
