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
- 已提交的 Alembic revision 与持久化模型接受的只读历史枚举属于升级兼容边界，不等同于当前产品模块；删除或收窄必须通过数据迁移 spec 证明旧库升级和历史记录读取不受损。
- 浏览器受支持的运行边界只通过同源 `/api/v1` REST 契约访问数据；可配置的基址覆盖项不构成跨域部署支持，契约快照位于 `packages/contracts/openapi.json`。
- 认证状态由 API 端持久化 Session 掌管，Web 端不保存认证令牌。
- 文章自动保存使用版本号乐观锁；版本冲突由 API 明确返回 `409`。
- 未列入产品模块表的后台进程、外部模型服务、第三方审计和派生存储不属于当前运行边界；新增此类能力必须通过独立 spec 明确进程、数据和接口所有权。
- 在部署方案形成独立 spec 前，不创建 `infra/`、`deploy/` 或存储实现目录。
