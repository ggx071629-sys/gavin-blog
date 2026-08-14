---
id: spec-20260814-zvec-vector-index
level: L1
summary: 在保留现有知识孵化检索策略与契约的前提下，以可回滚的 Zvec Flat 后端替换在线 SQLite BLOB/NumPy 向量扫描
load_when:
  - task:20260814-zvec-vector-index
author: Gavin
task_id: 20260814-zvec-vector-index
status: active
verification_profile: release
verification_escalation: Zvec 与 Retrieval Service 将改动 API、Worker、契约和产品检索边界，必须用 release 证明全栈合同后才能考虑生产默认切换。
documentation_impact: required
documentation_targets:
  - harness/docs/product/knowledge-incubator.md
  - harness/docs/architecture/boundaries.md
  - harness/docs/decisions/20260814-zvec-derived-vector-index.md
documentation_reason: Zvec、单一 Retrieval Service 与派生 generation 改变了知识孵化的持久存储、进程所有权和部署边界，必须同步产品基线、架构边界并记录持久决策。
state_history:
---

# Context

当前知识孵化混合检索只覆盖当前已发布且未删除文章的活动发布修订：独立 SQLite FTS5 片段索引召回 Top 20，固定 revision 的 `intfloat/multilingual-e5-small` ONNX INT8 生成 384 维 L2 归一化向量，应用从 SQLite `article_embeddings.vector` BLOB 读取全部活动向量并由 NumPy 执行精确内积 Top 20，随后以 RRF `k = 60` 融合 Top 20，再由固定 revision 的多语言 Cross-Encoder 重排并按既有门槛聚合为最多 8 篇文章。全站公共搜索和孵化关键词召回都继续依赖 SQLite FTS5。

现有产品基线明确把独立向量数据库列为需要单独规格和人工确认的高危未来变化。用户现已明确确认引入嵌入式 Zvec，但不授权更换嵌入模型、FTS5、RRF、Cross-Encoder、候选数量、相关门槛、语料边界或公开搜索。Zvec 只承担 E5 向量的派生存储和 Flat 精确近邻查询；SQLite 继续是文章、发布修订、片段、任务、活动状态和可重建来源的唯一事实库。

API 当前同步执行检索，独立 Worker 串行执行文章索引任务。为避免 API 与 Worker 并发打开或写入同一个嵌入式 collection，也避免两个进程重复加载本地模型，本任务引入仅在私有网络可达的 Retrieval Service，统一持有 E5、Cross-Encoder、Zvec collection 和完整检索流水线。服务落在 `apps/api` 内，以 `scripts/run_retrieval_service.py` 作为与 API、Worker 并列的第三进程；不新建 `apps/retrieval`，也不创建 `infra/` 或 `deploy/`。现有浏览器仍只访问 `/api/v1`，Worker 仍通过 SQLite 持久任务承担租约、取消和重试编排。

目标部署是 2 vCPU／4 GB 云实例。两模型是否常驻不预先承诺：由 AC-10 在该规格机器上的 RSS 与延迟门槛决定；未达标时按需顺序加载并释放。

# Goal

在 2 vCPU／4 GB 单机部署边界内，引入精确锁版的 Zvec 和单一 Retrieval Service，以 384 维 FP32 Flat collection 替换完整检索在线路径中的 SQLite BLOB/NumPy语义扫描，同时保持现有 FTS5、E5、RRF、Cross-Encoder、发布相似性判断、降级语义和前端业务契约不变。Zvec generation 必须由 SQLite 可重建、经严格 manifest 与 NumPy 等价性校验后原子切换，并保留旧向量后端和 previous generation 作为可立即回滚路径。

# Non-goals

- 不更换或重新量化 `multilingual-e5-small` 与现有多语言 Cross-Encoder，不改变 tokenizer、512 Token 上限、切片 pipeline 或模型准备供应链。
- 不迁移或删除公共 `search_index`、孵化 `incubator_fts`、CJK 查询变换或任何 SQLite FTS5 能力。
- 不使用 Zvec 原生 FTS、BM25、RRF、WeightedReRanker、DefaultLocalReRanker 或远程模型 API。
- 不启用 HNSW、DiskANN、IVF、RaBitQ、向量 FP16／INT8／INT4 或其他近似、二次量化索引。
- 不改变 FTS／语义／融合／重排 TopK、RRF `k = 60`、最低重排门槛、文章聚合上限或发布相似性阈值。
- 不扩大语料到草稿、项目、读书笔记、已删除文章或非当前发布修订。
- 不在本任务删除 `article_embeddings.vector`、NumPy回退实现或相关迁移历史；旧后端最终退役需在稳定运行后另建短生命周期 spec。
- 不创建 `infra/`、`deploy/`，不引入容器编排、跨主机部署、公开向量服务、GPU、Redis、Celery或独立消息队列。
- 不改变浏览器认证、Session、CSRF或公共 API，不让浏览器直接访问 Retrieval Service。

# Acceptance criteria

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

# Risks

- Zvec是较新的pre-1.0嵌入式数据库；精确锁版、不可变generation、严格manifest和全量可重建只能降低而不能消除API或存储格式变化风险。
- Retrieval Service改变现有API／Worker直接加载模型的进程边界，增加内部协议、认证、启动顺序和服务可用性；若实现为跨公网服务将违反本规格。
- 迁移期同时保留SQLite BLOB、Zvec active、previous和临时generation，会增加磁盘占用；路径解析错误可能误删非索引数据，因此清理必须只针对校验后的专用generation目录。
- Flat检索保持质量等价但不会在当前小语料上产生可见加速；本任务价值是明确向量存储边界和未来扩展性，不得宣称提高E5或Cross-Encoder精度。
- 5万向量与2 vCPU／4 GB绝对性能受CPU、磁盘和虚拟化环境影响；自动化测试必须产生可比较的机器证据，但生产切换仍需在目标云实例执行同一验收程序，不能用开发机结果替代。
- 当前产品基线要求embedding与reranker按需顺序加载并释放，而共同确认方案允许由单一服务持有实例；实现必须以AC-10资源门槛决定是否常驻，文档不得在无证据时承诺更低内存。
- 本任务保留旧向量表和NumPy回退，因此不会立刻降低数据库磁盘占用；稳定后退役旧后端需要新的spec、Alembic迁移和独立回滚确认。

# Verification plan

- api-lint => AC-2, AC-3, AC-4, AC-5, AC-6, AC-8, AC-9, AC-10, AC-11
- api-tests => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11
- web-quality => AC-1, AC-9, AC-11
- e2e => AC-1, AC-7, AC-8, AC-9, AC-11
- harness-integrity => AC-12
- release => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12
