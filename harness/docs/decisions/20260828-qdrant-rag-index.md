---
id: decision-qdrant-rag-index
level: L1
summary: 以 SQLite 为事实库、Qdrant 为可重建派生存储，建立默认关闭的助手混合检索索引
load_when:
  - architecture-decision
  - retrieval-index
  - assistant-index
author: Gavin
---

# Decision: Qdrant plus SQLite FTS5 assistant index

本文保留初始索引决策。当前本机 Embedding 方案见 [本地 E5 决策](20260906-local-e5-retrieval.md)，来源范围由 [About／简历接入决策](20260911-assistant-source-ingestion.md) 扩展；旧文中的云端供应商待选与初始来源枚举仅描述当时状态。

## Status

Accepted.

## Context

公开搜索已经使用文档级 SQLite FTS5 `search_index`，并且只投影当前发布修订。后续公开助手需要 Hybrid RAG，但不能恢复 2026-08-26 退役的知识孵化运行面，也不能把向量库提升为第二事实库。云端 Embedding 供应商尚未选定。生产目标仍是单台小规格服务器上的同机独立 Qdrant 进程。

## Decision

- 关键词召回使用助手专用 SQLite FTS5；稠密召回使用 Qdrant。融合、授权校验和降级由 API 内部 Retriever 完成，不使用 Qdrant 原生 sparse / hybrid / rerank。
- SQLite 拥有规范切片、切片哈希、outbox 任务、generation 清单和活动指针。Qdrant 只保存 allowlist payload 的派生向量，删除全部 collection 后必须能从当前公开投影重建。
- 发布事务只登记稳定标识和目标版本，不调用 Embedding 或 Qdrant。Worker 单消费者异步处理；外部故障不得阻塞或回滚已经合法的内容发布。
- 查询授权以 SQLite 当前公开指针为准。旧修订、回收站和已删除内容即使仍留在 Qdrant 或助手 FTS5 中也不得返回。
- generation 切换只保留 active 与 previous 两代。previous 只是恢复基线，未经重新追平和完整验证不得直接切回。
- 能力默认关闭，没有公开问答入口。`test` Embedding 替身不得冒充生产供应商。About 页仍有一部分只存在于 Nuxt 模板的静态文案，本阶段不摄入。
- 不恢复知识孵化旧路由、旧表、旧 Worker 或 Retrieval Service。

## Consequences

- API 增加可选 Worker 进程和 Qdrant 运维责任，但默认安装和启动路径保持两应用边界。
- 现有 `/api/v1/search` 继续独立于助手索引。
- 真实召回质量、费用、延迟和 2 vCPU／4 GB 资源验收仍取决于后续 provider 接入与发布准备。

## Re-evaluate when

- 选定并接入真实云端 Embedding 供应商和维度。
- 需要开放公开问答 API、会话或管理控制面。
- About 静态正文有了单一规范来源。
- Qdrant 运维成本或同机部署假设不再成立。
