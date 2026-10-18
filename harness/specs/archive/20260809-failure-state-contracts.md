---
id: archive-20260809-failure-state-contracts
level: L2
summary: 让公开页面与管理认证准确区分空数据、404、未登录、限流和上游故障
load_when:
  - task:20260809-failure-state-contracts
author: Codex
task_id: 20260809-failure-state-contracts
status: compressed
restoration_source: "92ca7527b78ac13e51d27adf298289eed9892b13:harness/specs/active/20260809-failure-state-contracts.md"
restored_at: 2026-08-11
---

# 20260809-failure-state-contracts

Deterministic compressed record. The original active spec remains in Git history.

## Goal

建立 Web 端共享的失败分类，使公开 SSR、客户端页面和管理认证只根据可证明的上游状态呈现空数据、404、登录、限流或服务故障，并为用户提供真实的恢复信息。

## Acceptance criteria

1. 公开首页、文章／项目／书摘／归档列表在上游网络故障或 5xx 时不显示空态；SSR 返回对应 5xx，无法取得 HTTP 状态的连接故障返回 503。
2. 文章、项目和书摘详情只有明确的 API 404 映射为页面 404；网络、超时、429、403 和 5xx 不得伪装成资源不存在。
3. 成功的空数组仍返回 200 并显示现有空态，不与故障状态混淆。
4. 管理路由 session 检查仅在 401 时转到登录页，并保留站内 `returnTo`；403、429、5xx 和网络故障显示相应错误，不伪装成未登录。
5. 登录明确区分错误凭据 401、安全校验 403、限流 429、服务端 5xx 与网络故障；只有成功后才按安全的管理端 `returnTo` 跳转。
6. logout 只有成功或服务端已确认无有效 session 时才进入登录页；403、5xx 或网络失败时留在当前页面并显示可访问的错误提示。
7. 主要后台内容列表在数据加载失败时不显示“还没有内容”的空态。
8. README 记录共享失败语义；不改变 OpenAPI snapshot。

## Result

Verified and closed by the harness close command.

## Evidence

[20260809-failure-state-contracts.json](../../verification/evidence/20260809-failure-state-contracts.json)

Closed at 2026-08-10T12:38:12.112237+00:00.
