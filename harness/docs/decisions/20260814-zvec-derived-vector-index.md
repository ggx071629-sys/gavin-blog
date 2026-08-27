---
id: decision-zvec-derived-vector-index
level: L2
summary: 已被退役决策取代的派生向量索引历史方案
load_when:
  - historical-architecture
  - task:20260814-zvec-vector-index
author: Gavin
---

# Decision: Zvec derived vector index

## Status

Superseded by [Decision: retire the knowledge incubator](20260826-retire-knowledge-incubator.md) on 2026-08-26. 本文只解释历史实现，不再约束当前运行时。

## Context

知识孵化混合检索已经固定 FTS5 Top 20、multilingual-e5-small、RRF `k = 60`、多语言 Cross-Encoder 与最多 8 篇文章聚合。在线语义扫描原先从 SQLite BLOB 读出全部活动向量并由 NumPy 做精确内积。产品基线曾把独立向量数据库列为高危未来变化。现已确认引入嵌入式 Zvec，但不授权更换检索策略、模型、语料或公开搜索。

## Decision

- Zvec 只保存当前活动或待切换 generation 的 384 维 L2 归一化 FP32 向量，使用 Flat 精确索引和与 NumPy 内积等价的 IP 度量。
- SQLite 仍是唯一事实库。删除全部 Zvec 文件后必须能从 SQLite 与固定模型 manifest 全量重建。
- `apps/api/scripts/run_retrieval_service.py` 是 E5、Cross-Encoder 和 Zvec 的唯一运行时所有者；API 与 Worker 不直接打开 collection，也不加载生产模型。服务只绑定 loopback 或私有网络，浏览器不访问它。
- 每个 generation 在专用目录构建并携带严格 manifest。只保留 active 与 previous；切换或重开失败回滚 previous。
- 查询后端开关为 `numpy|zvec`，迁移期双写。生产默认保持 `numpy`，直到目标 2 vCPU／4 GB 云实例上的等价性与资源门槛通过。
- 两模型是否常驻不预先承诺，由同一资源门槛决定。

## Re-evaluate when

- 有效片段持续超过 50,000，或 2 vCPU／4 GB 上 Zvec 查询 P95、端到端 P95 或 RSS 超过门槛。
- 锁定的 Zvec 版本无法证明存储格式兼容，必须构建新 generation 而不是原地打开。
- 准备退役 `article_embeddings.vector` 与 NumPy 回退；那需要新的短生命周期 spec 和独立回滚确认。

## Consequences

- 本地与部署需要 API、Worker 与 Retrieval Service 三个进程。
- 磁盘在迁移期同时保留 SQLite BLOB、Zvec active／previous 和临时 generation。
- 本决策不提高 E5 或 Cross-Encoder 精度，也不授权 HNSW、DiskANN 或其他近似索引。
