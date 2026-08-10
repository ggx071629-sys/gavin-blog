---
id: spec-20260809-failure-state-contracts
level: L1
summary: 让公开页面与管理认证准确区分空数据、404、未登录、限流和上游故障
load_when:
  - task:20260809-failure-state-contracts
author: Codex
task_id: 20260809-failure-state-contracts
status: active
---

# Context

AUD-04 已确认公开首页、列表和详情页忽略或压平 API 错误：上游故障会被展示为 200 空站，详情的任意失败会被转换为 404。AUD-12 已确认管理端把 session 的所有失败当作未登录、登录把多数失败当作错误密码，并在 logout 失败时仍宣称退出成功。这些行为会误导用户，并让 SSR 向搜索引擎发送错误状态。

# Goal

建立 Web 端共享的失败分类，使公开 SSR、客户端页面和管理认证只根据可证明的上游状态呈现空数据、404、登录、限流或服务故障，并为用户提供真实的恢复信息。

# Non-goals

- 不改变 FastAPI 的认证、限流或业务响应 schema。
- 不处理 AUD-08 的 AsyncData key 冲突和主题 hydration，不把其警告并入本 spec。
- 不重构孵化轮询、媒体上传或全站视觉系统。
- 不引入离线缓存、重试队列或新的部署代理。

# Acceptance criteria

1. 公开首页、文章／项目／书摘／归档列表在上游网络故障或 5xx 时不显示空态；SSR 返回对应 5xx，无法取得 HTTP 状态的连接故障返回 503。
2. 文章、项目和书摘详情只有明确的 API 404 映射为页面 404；网络、超时、429、403 和 5xx 不得伪装成资源不存在。
3. 成功的空数组仍返回 200 并显示现有空态，不与故障状态混淆。
4. 管理路由 session 检查仅在 401 时转到登录页，并保留站内 `returnTo`；403、429、5xx 和网络故障显示相应错误，不伪装成未登录。
5. 登录明确区分错误凭据 401、安全校验 403、限流 429、服务端 5xx 与网络故障；只有成功后才按安全的管理端 `returnTo` 跳转。
6. logout 只有成功或服务端已确认无有效 session 时才进入登录页；403、5xx 或网络失败时留在当前页面并显示可访问的错误提示。
7. 主要后台内容列表在数据加载失败时不显示“还没有内容”的空态。
8. README 记录共享失败语义；不改变 OpenAPI snapshot。

# Risks

- Nuxt SSR 与客户端导航的错误对象形状不同；状态提取必须覆盖 `status`、`statusCode` 和响应状态，未知错误只保守映射为 503。
- 在页面 setup 中抛错会进入全局错误页；必须保留真实 SSR 状态，且不能把成功空数据抛成错误。
- `returnTo` 若不限制为本地管理路径会形成开放重定向风险。
- logout 失败后 Cookie 可能仍有效，UI 不得清除或宣称 session 已失效。

# Verification plan

- TDD：纯函数测试覆盖 401／403／404／429／500／503、网络错误、登录提示和安全 `returnTo`。
- Component/static contract：公开列表、详情和主要后台列表必须消费 AsyncData error；认证 middleware/login/logout 使用同一分类。
- Integration/E2E：故障注入验证公开 SSR 的 200 空数据、404 和 5xx/503；验证 session 500 不跳登录、登录分型和 logout 失败留页。
- Quality：Web typecheck、Vitest、生产 build、相关 Playwright，然后完整 `npm run quality:release`。
- Harness：从 `harness/` 运行 `python -m tools.harness verify 20260809-failure-state-contracts`，通过后用确定性 close 命令关闭。
