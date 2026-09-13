---
id: decision-public-qa-online-core
level: L1
summary: 以默认关闭的 LangGraph 匿名问答 API 作为后续悬浮气泡的后端内核，并把短会话 SQLite 排除出长期备份
load_when:
  - architecture-decision
  - assistant-online
  - public-qa
author: Gavin
---

# Decision: default-off public Q&A online core

## Status

Accepted.

## Context

混合检索索引已经存在，但没有匿名会话、公开问答路由、云端 Chat／Embedding、费用账本或注入防护。目标用户是低流量招聘访客，助手只解释本站已索引的公开内容和公开 Profile。生产部署仍是 No-Go。About 模板静态文案仍未进入语料。

## Decision

- 公开问答是默认关闭的后端内核，不是已交付的 Web 产品。没有 Nuxt 气泡、管理配置页或费用看板。
- 在线编排使用有限 `StateGraph`、LangChain 结构化输出和既有 Hybrid Retriever。没有 Deep Agents、自由工具、联网搜索或模型式 query rewrite。
- 首个供应商边界是显式的 OpenAI-compatible Chat Completions／Embeddings。`ChatOpenAI` 固定 `use_responses_api=False`、`streaming=False`、`max_retries=0`。
- 匿名会话、幂等、Chat／query 费用账本、SSE journal 和 LangGraph checkpoint 放在独立 `assistant_runtime` SQLite。该文件只有单个 API 进程以 owner lock 打开，明确不进入长期备份。官方生产建议仍是 Postgres checkpointer；本例外只在单进程、低并发、本地磁盘且实测通过时成立。
- 索引 Embedding 账本放在已备份的内容事实库，由独立 Worker 所有。Worker 不得打开 `assistant_runtime`。
- 北京时间每日 2.00 元人民币只约束按配置价格计算的公开 Chat 新调用准入／预留，不是结算或供应商账单保证。
- HTTP/in-memory preflight 在任何原文落库或 graph 启动之前拒绝高置信注入与越权请求。

## Consequences

- API 增加可选在线路由、显式 readiness 命令和 runtime provisioning 命令；未启用时现有服务不要求模型、Qdrant 或 runtime 文件。
- 灾难恢复会丢弃短会话，并至少锁到下一个北京时间零点才允许公共 Chat／query。
- 真实供应商质量、反向代理 SSE 和 2 vCPU／4 GB 容量仍是后续生产放行条件。

## Re-evaluate when

- 需要第二个 API 进程、共享存储或多主机。
- 需要 Postgres checkpointer 或跨会话记忆。
- About 静态正文有了规范来源并完成重新索引。
- 准备开放 Web 气泡或生产流量。
