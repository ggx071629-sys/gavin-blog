---
id: spec-20260803-same-origin-auth-proxy
level: L1
summary: 通过 Nuxt 同源代理消除本地前端与 API 主机名不一致导致的登录 CSRF 失败
load_when:
  - task:20260803-same-origin-auth-proxy
author: Gavin
task_id: 20260803-same-origin-auth-proxy
status: verified
---

# Context

本地前端可能通过 `localhost:3000` 或 `127.0.0.1:3000` 访问，而浏览器端 API 基址固定为另一个绝对主机名。浏览器将两者视为不同站点，`SameSite=Lax` 的 Session／CSRF Cookie 不随跨站登录 POST 发送，导致 `/auth/session` 返回 401、`/auth/login` 返回 403。

# Goal

让浏览器只通过当前 Nuxt 源访问 `/api/v1`，由 Nuxt 服务端代理到可配置的 FastAPI 上游，使登录和后续管理请求不依赖访问者选择 `localhost` 或 `127.0.0.1`。

# Non-goals

- 不改变 FastAPI 的 Session、CSRF、密码或限流语义。
- 不改变公开或管理 API 路径与响应契约。
- 不移除 FastAPI 对直接 API 客户端保留的 CORS 配置。

# Acceptance criteria

1. 浏览器端 API 基址默认为相对路径 `/api/v1`，请求与当前前端页面同源。
2. Nuxt 将 `/api/v1/**` 的方法、查询、请求体、Cookie、CSRF 请求头、状态码和 `Set-Cookie` 响应头代理到服务器私有配置的 FastAPI 上游。
3. SSR、RSS 与 sitemap 等服务端消费者直接使用私有上游地址，不依赖浏览器相对 URL。
4. 本地媒体相对 URL 继续解析到当前前端源，不重新引入主机名不一致。
5. E2E 通过同源代理完成管理员登录和核心内容闭环；分别使用 `localhost` 或 `127.0.0.1` 访问前端时，CSRF 登录链路均不返回 403。
6. 类型检查、单元测试、生产构建、E2E 与 harness 验证通过。

# Risks

- 代理未完整透传 `Set-Cookie`、请求体或 CSRF 头会破坏登录和写操作。
- 服务端渲染若使用相对 API URL，可能在 Node 环境产生无效 URL。
- 既有媒体 URL 拼接逻辑以绝对 API 基址为前提，需要同步适配。

# Verification plan

- 为相对媒体 URL 与上游 URL 组合增加单元测试。
- 运行 Web TypeScript、Vitest 与生产构建。
- 更新 Playwright 服务配置，确保浏览器只访问同源 `/api/v1` 并执行现有管理员完整闭环。
- 启动生产预览，分别从 `localhost:3000` 与 `127.0.0.1:3000` 验证 CSRF Cookie 和错误密码登录返回 401 而非 403。
- 运行 `python -m tools.harness verify 20260803-same-origin-auth-proxy`。
