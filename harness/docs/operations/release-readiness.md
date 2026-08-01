---
id: operations-release-readiness
level: L1
summary: 本地发布候选门禁、首发阻断项及备份回滚边界
load_when:
  - release
  - operations
  - deployment
author: Gavin
---

# Release readiness

## Current status

项目当前处于“本地 MVP 完成、工程收口与首发准备进行中”。`npm run quality:release` 通过只表示本地发布候选满足代码、契约、测试、构建、可访问性、性能、SEO 和 Harness 完整性门槛；在部署决策及运维演练完成前不得标记为 production-ready。

## Local release candidate gate

从仓库根目录执行：

```powershell
npm ci
npm run quality:release
```

API 虚拟环境必须位于 `apps/api/.venv`，并已安装 `.[dev]`。门禁依次执行 API Ruff、Pytest、OpenAPI 快照一致性、Web 类型检查、Vitest、生产构建、axe-core、Lighthouse、核心 Playwright E2E 和 Harness checks。任何一步失败都阻断候选版本。

## Before first production release

- 通过独立 spec 确定 Web/API 运行拓扑、域名、TLS、进程管理和部署平台。
- 为 SQLite 指定持久卷、单写者约束、备份频率、保留周期及恢复目标。
- 为媒体目录选择持久本地卷或对象存储适配器，并验证数据库与媒体的一致恢复点。
- 在目标环境配置随机管理员密码、Secure Cookie、精确 CORS 来源、公开 API 地址与 canonical 站点地址。
- 在生产数据副本或等价空库上执行 `alembic upgrade head`，验证迁移链和 FTS5 可用性。
- 完成一次备份恢复演练和一次上一版本回滚演练，记录耗时与人工步骤。
- 从干净检出使用锁文件安装依赖并通过 `npm run quality:release`。
- 确认 Git 工作树干净，生成带版本号和 commit SHA 的发布说明。

## Data boundaries

`.env`、开发日志、SQLite 数据库、本地媒体和原始验证产物不得进入 Git。备份必须同时覆盖 SQLite 数据库与媒体对象；只有数据库或只有媒体的备份不构成可恢复备份。

## Rollback boundary

在部署方案确定前，本项目只定义回滚原则，不虚构平台命令：保留上一可运行应用产物；迁移前创建可验证备份；数据库迁移默认前向修复，只有迁移显式证明可逆时才执行降级；涉及数据库或媒体写入的回滚必须先停止写流量并保护当前副本。

## Go / no-go

只有上述首发条件全部有可复查证据时才能作出 Go 决策。当前结论为 **No-Go for production deployment**，但可以继续生成和验证本地 release candidate。
