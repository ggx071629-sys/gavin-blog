---
id: archive-20260803-same-origin-auth-proxy
level: L2
summary: 通过 Nuxt 同源代理消除本地前端与 API 主机名不一致导致的登录 CSRF 失败
load_when:
  - task:20260803-same-origin-auth-proxy
author: Gavin
task_id: 20260803-same-origin-auth-proxy
status: compressed
restoration_source: "d28d3137a02ef696b9830c926d397262128eb503:harness/specs/active/20260803-same-origin-auth-proxy.md"
restored_at: 2026-08-11
---

# 20260803-same-origin-auth-proxy

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让浏览器只通过当前 Nuxt 源访问 `/api/v1`，由 Nuxt 服务端代理到可配置的 FastAPI 上游，使登录和后续管理请求不依赖访问者选择 `localhost` 或 `127.0.0.1`。

## Acceptance criteria

1. 浏览器端 API 基址默认为相对路径 `/api/v1`，请求与当前前端页面同源。
2. Nuxt 将 `/api/v1/**` 的方法、查询、请求体、Cookie、CSRF 请求头、状态码和 `Set-Cookie` 响应头代理到服务器私有配置的 FastAPI 上游。
3. SSR、RSS 与 sitemap 等服务端消费者直接使用私有上游地址，不依赖浏览器相对 URL。
4. 本地媒体相对 URL 继续解析到当前前端源，不重新引入主机名不一致。
5. E2E 通过同源代理完成管理员登录和核心内容闭环；分别使用 `localhost` 或 `127.0.0.1` 访问前端时，CSRF 登录链路均不返回 403。
6. 类型检查、单元测试、生产构建、E2E 与 harness 验证通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260803-same-origin-auth-proxy.json](../../verification/evidence/20260803-same-origin-auth-proxy.json)

Closed at 2026-08-02T16:35:14.019740+00:00.
