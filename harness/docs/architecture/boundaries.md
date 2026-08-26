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
- SQLite 是内容、不可变发布修订、引用、公开关系、搜索与认证状态的唯一事实库；迁移只能通过 Alembic 演进。
- 浏览器只通过 `/api/v1` REST 契约访问数据；契约快照位于 `packages/contracts/openapi.json`。
- 认证状态由 API 端持久化 Session 掌管，Web 端不保存认证令牌。
- 文章自动保存使用版本号乐观锁；版本冲突由 API 明确返回 `409`。
- 知识孵化、Worker、Retrieval Service、第三方 LLM 审计和派生向量存储不属于主项目运行边界；如需恢复，必须从独立归档重新立项并保持进程、数据和发布接口隔离。
- 在部署方案形成独立 spec 前，不创建 `infra/`、`deploy/` 或存储实现目录。
