---
id: archive-20260801-e2e-isolation
level: L2
summary: 隔离 Playwright 服务、数据库与媒体目录，使端到端验证可安全重复执行
load_when:
  - task:20260801-e2e-isolation
task_id: 20260801-e2e-isolation
status: compressed
---

# 20260801-e2e-isolation

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让常规 E2E 每次只连接由本次 Playwright 运行启动的专用 Web/API 服务，并让所有数据库与上传文件写入本次运行独占的临时目录，从而可以安全执行真实跨栈验证。

## Acceptance criteria

- 常规 Playwright 不复用任何已存在的 Web 或 API 服务，并使用区别于开发默认值的专用端口。
- Nuxt E2E 服务显式接收测试 API 地址与站点地址；SEO 断言不再依赖硬编码的开发端口。
- E2E API 每次运行创建唯一的系统临时目录，SQLite 数据库和媒体文件均位于其中，且不执行针对持久数据库的删表语句。
- npm E2E 入口在 Playwright 完成服务关闭后清理本次临时目录，测试失败时也执行清理。
- API 健康检查和 Web 服务均由 Playwright 使用完整 URL 探测，端口占用时安全失败而不是复用未知进程。
- 三条现有 Playwright 用户旅程在隔离配置下通过；API、Vitest、类型检查、构建与 Harness 验证保持通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260801-e2e-isolation.json](../../verification/evidence/20260801-e2e-isolation.json)

Closed at 2026-08-01T16:42:50.482036+00:00.
