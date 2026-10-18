---
id: archive-20260814-zvec-vector-index
level: L2
summary: 在保留现有知识孵化检索策略与契约的前提下，以可回滚的 Zvec Flat 后端替换在线 SQLite BLOB/NumPy 向量扫描
load_when:
  - task:20260814-zvec-vector-index
author: Gavin
task_id: 20260814-zvec-vector-index
status: compressed
documentation_impact: required
documentation_targets:
  - harness/docs/product/knowledge-incubator.md
  - harness/docs/architecture/boundaries.md
  - harness/docs/decisions/20260814-zvec-derived-vector-index.md
documentation_reason: Zvec、单一 Retrieval Service 与派生 generation 改变了知识孵化的持久存储、进程所有权和部署边界，必须同步产品基线、架构边界并记录持久决策。
state_history:
---

# 20260814-zvec-vector-index

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在 2 vCPU／4 GB 单机部署边界内，引入精确锁版的 Zvec 和单一 Retrieval Service，以 384 维 FP32 Flat collection 替换完整检索在线路径中的 SQLite BLOB/NumPy语义扫描，同时保持现有 FTS5、E5、RRF、Cross-Encoder、发布相似性判断、降级语义和前端业务契约不变。Zvec generation 必须由 SQLite 可重建、经严格 manifest 与 NumPy 等价性校验后原子切换，并保留旧向量后端和 previous generation 作为可立即回滚路径。

## Acceptance criteria

- AC-1: 完整检索继续执行 `incubator_fts Top 20 + multilingual-e5-small Top 20 -> RRF(k=60) Top 20 -> 现有 Cross-Encoder -> 既有门槛与最多 Top 8 文章聚合`；模型 revision、查询／文档前缀、分数语义、候选统计、发布相似性判断和现有 preview 响应字段保持兼容，全站 FTS5 搜索不受影响。
- AC-2: Zvec 后端只保存活动或待切换 generation 的 384 维 L2 归一化 FP32 向量，使用 Flat 精确索引与和当前 NumPy 内积排序等价的度量；Zvec 中的文章、修订和片段标识都可回查 SQLite，SQLite 仍是唯一事实来源，删除全部 Zvec 文件后可以从 SQLite 与固定模型 manifest 全量重建。
- AC-3: 新增单一 Retrieval Service 作为 E5、Cross-Encoder 和 Zvec 的唯一运行时所有者，入口为 `apps/api/scripts/run_retrieval_service.py`；FastAPI 通过私有内部接口请求完整检索，Worker 通过带内部认证的幂等管理接口请求索引、重建和 generation 切换，API 与 Worker 不直接打开 Zvec collection，也不各自加载生产模型。服务默认只绑定 loopback 或私有容器网络，生产配置拒绝公开监听和测试替身。
- AC-4: Retrieval Service 对模型推理和 Zvec 写入实行单流水线资源纪律：E5实例、Cross-Encoder实例、在线完整检索和索引写入并发各为 1，发布相似性检查和在线预览优先于增量索引与全量重建；索引构建不得阻塞 FastAPI 事件循环，模型与日志不得运行时联网。
- AC-5: 每个不可变 Zvec generation 在专用目录构建并携带严格 manifest，记录 generation ID、精确 Zvec 版本、E5与tokenizer revision／checksum、维度、数据类型、归一化、距离度量、pipeline版本、有效修订摘要、片段／向量数量和完成时间；不兼容或不完整 generation 拒绝加载。校验成功后原子切换 active，始终只保留 active 与 previous 两个完整 generation，切换正确性失败自动回滚 previous。
- AC-6: 索引与切换管理请求包含稳定 `job_id`、目标 generation、文章与发布 revision、pipeline version、embedding revision和manifest checksum；任务重放、租约过期、旧revision晚完成、重复切换或服务重启均不产生重复向量，不允许旧revision覆盖新revision，也不允许未完成 generation 成为 active。
- AC-7: 提供 `numpy|zvec` 向量后端开关和迁移期双写，初始数据库可无损构建 Zvec；切换硬门槛要求固定查询集在相同活动语料上满足 Top20候选集合与Top1一致、非并列候选顺序一致、语义分数绝对误差不超过 `1e-5`，并且经过既有RRF与Cross-Encoder后的最终文章／片段顺序一致。任一差异、维度错误或未知segment ID都会阻止切换，旧NumPy后端可立即恢复而无需重新嵌入。
- AC-8: 普通预览在Zvec、E5或Cross-Encoder局部故障时只能按既有显式降级契约返回可用的FTS5或RRF候选并标记 `degraded = true`；发布前相似性检查和正常审计不得静默降级，缺少完整语义召回或重排时失败关闭。数据正确性、manifest、探针或active重开失败触发自动generation回滚，单次延迟或内存抖动只告警并保留人工后端回滚。
- AC-9: 检索健康状态在保持现有消费者兼容的同时报告 `vector_backend`、精确Zvec版本、active generation、collection状态、回退可用性、队列长度和分阶段耗时；ready必须同时要求模型校验、manifest兼容、数量一致、collection可打开和固定探针成功。响应与日志不暴露绝对路径、内部令牌、原始查询、草稿正文、向量或Cross-Encoder输入，默认只记录request ID、query hash、segment ID、分数、耗时和错误码。
- AC-10: 依赖解析精确固定经验证的Zvec版本，升级被视为索引迁移；无法证明存储格式兼容时必须构建新generation而不是原地打开。可重复的检索基准与压力测试覆盖至少5万条384维测试向量、连续查询与generation切换，输出NumPy／Zvec等价性、P50／P95、进程RSS和资源增长；测试逻辑明确判定2 vCPU／4 GB目标门槛（常态RSS不超过3.0GB、峰值不超过3.4GB、Zvec查询P95不超过100ms、端到端P95不超过1秒、无持续内存／线程／句柄增长），未满足时阻止生产默认切换。
- AC-11: 现有API与Worker测试替身在无真实模型、无外网环境下仍可确定性覆盖完整流水线；测试覆盖Zvec损坏、构建中断、重复任务、旧revision竞态、active切换、自动回滚、普通预览降级、发布失败关闭、私有网络配置和NumPy功能开关，OpenAPI快照与Web类型仅发生向后兼容的健康字段扩展。
- AC-12: 同步更新知识孵化产品基线和架构边界，删除“本任务仍禁止独立向量数据库”的过期断言但保留SQLite事实库、FTS5和2 vCPU／4 GB约束；新增持久决策文档说明选择Zvec而非替换检索策略、单一服务所有权、generation／回滚边界及重新评估触发器，长期文档不链接本active spec。

## Result

Verified and closed by the harness close command.

## Evidence

[20260814-zvec-vector-index.json](../../verification/evidence/20260814-zvec-vector-index.json)

Closed at 2026-08-15T14:51:30.622026+00:00.
