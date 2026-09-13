---
id: decision-public-qa-web-delivery
level: L1
summary: 以默认关闭的同源悬浮 Web 层消费已有匿名问答内核，并补齐 session 生命周期 fence
load_when:
  - architecture-decision
  - assistant-online
  - public-qa
author: Gavin
---

# Decision: default-off public Q&A web delivery

本文保留首次 Web 交付决策。当前入口还消费服务端可用性，行为见 [管理执行与预算决策](20260910-assistant-management.md)；来源范围见 [About／简历接入决策](20260911-assistant-source-ingestion.md)。旧的单独 Web flag 条件不是当前完整可见性合同。

## Context

阶段二交付了默认关闭的匿名问答 API 内核，但没有公开 Web 消费者，浏览器刷新也无法安全恢复仍在运行的 turn。Phase 2 通过的测试不能证明 tombstone fencing、runner 异常终结和公开 wire 投影已经成立。

## Decision

- 公开入口是默认关闭的「问 Gavin」悬浮层，不是聊天机器人皮肤。Web flag 只有严格 `true` 才渲染；API 开关仍是访问控制。
- 浏览器不持久化问题、答案、幂等 key 或 payload。断线最多两次同 key 重连，整页刷新只通过 GET `active_turn` 轮询。
- 对外 API 只做 additive session view／policy／公开 SSE 投影。内部必须先线性化 tombstone、prepared→sending、heartbeat 与 48h billing tombstone，才能打开 Web enabled-state。
- CSRF 是 session-bound deterministic token，bootstrap 重签且不刷新 idle TTL。DELETE 204／202 都撤销两个助手 Cookie。
- About 模板静态文案仍不是 RAG 语料。本决策不构成生产 Go。

## Consequences

- 必须同时验收 UI off 零请求基线与 UI on 的无障碍／同源 SSE。
- Nitro 只能证明应用层逐段转发；公网反向代理缓冲仍是生产阻断项。
- 本站 DELETE 只清理本地可读正文，不能撤回已外发供应商数据。
