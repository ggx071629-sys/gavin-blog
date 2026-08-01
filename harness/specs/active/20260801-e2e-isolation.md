---
id: spec-20260801-e2e-isolation
level: L1
summary: 隔离 Playwright 服务、数据库与媒体目录，使端到端验证可安全重复执行
load_when:
  - task:20260801-e2e-isolation
task_id: 20260801-e2e-isolation
status: verified
---

# E2E isolation

## Context

常规 Playwright 配置允许复用 `3000/8000` 上已有服务，API 启动脚本还会在仓库内固定 `data/e2e.db` 上执行删表重建。若开发服务正在运行，测试可能绕过测试启动脚本并直接修改开发数据库；即使没有复用服务，固定数据库与默认媒体目录也会让测试运行之间互相污染。

## Goal

让常规 E2E 每次只连接由本次 Playwright 运行启动的专用 Web/API 服务，并让所有数据库与上传文件写入本次运行独占的临时目录，从而可以安全执行真实跨栈验证。

## Non-goals

- 不建立 CI、容器编排或生产部署配置。
- 不改变生产和开发服务的默认端口、数据库或媒体配置。
- 不重写现有用户旅程，也不删除仓库中已有的历史 `e2e.db`。
- 本规格不处理业务时区、媒体事务或分页行为。

## Acceptance criteria

- 常规 Playwright 不复用任何已存在的 Web 或 API 服务，并使用区别于开发默认值的专用端口。
- Nuxt E2E 服务显式接收测试 API 地址与站点地址；SEO 断言不再依赖硬编码的开发端口。
- E2E API 每次运行创建唯一的系统临时目录，SQLite 数据库和媒体文件均位于其中，且不执行针对持久数据库的删表语句。
- npm E2E 入口在 Playwright 完成服务关闭后清理本次临时目录，测试失败时也执行清理。
- API 健康检查和 Web 服务均由 Playwright 使用完整 URL 探测，端口占用时安全失败而不是复用未知进程。
- 三条现有 Playwright 用户旅程在隔离配置下通过；API、Vitest、类型检查、构建与 Harness 验证保持通过。

## Risks

- Nuxt 的运行时 API 基址若未传入，会让浏览器仍访问开发端口，因此 Web 启动环境必须同时设置 API 和站点 URL。
- Playwright 强制不复用服务后，专用端口被占用会使测试失败；这是保护数据所需的安全失败行为。
- 包装进程自身被操作系统强制终止时系统临时目录可能延迟清理，但不会写入仓库或开发数据目录；正常成功或失败退出均由 `finally` 清理。

## Verification plan

- 运行常规 `npm run test:e2e`，覆盖登录、自动保存、发布、媒体上传、搜索、回收站、导入导出、移动端体验与 SEO。
- 运行 API 全量 Pytest、Web Vitest、TypeScript no-emit 和 Nuxt 生产构建。
- 检查运行前后的仓库内历史 `data/e2e.db` 指纹不变，并确认没有新增持久 E2E 媒体文件或本次临时目录。
- 刷新索引并运行 `python -m tools.harness verify 20260801-e2e-isolation`。

## Implementation record

- 常规 Playwright 改用 `3100/8100` 专用端口、完整健康检查 URL 与 `reuseExistingServer: false`；Nuxt 测试进程显式接收对应 API 和站点地址。
- E2E API 不再访问仓库内 `data/e2e.db` 或执行删表，而是把 SQLite 和媒体派生文件写入包装器为本次运行创建的唯一系统临时目录。
- Node 包装器直接启动已安装的 Playwright CLI，在 Playwright 停止 Web/API 服务后通过 `finally` 清理临时目录，并保留测试退出码。
- SEO 旅程根据当前测试站点来源验证 canonical 与 sitemap，不再硬编码开发端口。
- 隔离后的 3 条 Playwright 旅程、API 23 项、Web 14 项、Ruff、TypeScript no-emit 与 Nuxt 生产构建均通过；历史 `data/e2e.db` 的 SHA-256 前后保持一致。
- Spec 保留在 active 目录：仓库仍无 Git HEAD，无法满足 deterministic close 的历史前置条件。
