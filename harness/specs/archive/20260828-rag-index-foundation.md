---
id: archive-20260828-rag-index-foundation
level: L2
summary: 为公开内容问答建立可重建、修订绑定且可降级的 SQLite FTS5 与 Qdrant 混合检索索引基础
load_when:
  - task:20260828-rag-index-foundation
author: Gavin
task_id: 20260828-rag-index-foundation
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - harness/docs/architecture/boundaries.md
  - harness/docs/decisions/20260828-qdrant-rag-index.md
documentation_reason: 本任务新增派生向量存储、助手专用 FTS5、持久索引任务和独立 Worker，改变 API 侧依赖、进程、存储与降级边界；由于能力仍默认关闭且没有公开入口，本阶段不把它登记为已交付产品模块。
state_history:
---

# 20260828-rag-index-foundation

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在不开放任何新公开问答入口、也不改变现有 `/api/v1/search` 行为的前提下，为当前公开文章、项目、读书笔记和 Profile 建立默认关闭、可确定性测试的 RAG 索引基础：以 SQLite 保存规范切片、助手 FTS5、持久索引任务、generation 状态和 manifest，以 Qdrant 保存可从 SQLite 重建的稠密向量，通过单并发轻量 Worker 异步处理发布生命周期，并提供仅供后续问答图使用的内部 Hybrid Retriever。任一外部 Embedding 或 Qdrant 故障不得阻塞内容发布；旧修订和已删除内容不得因索引延迟继续冒充当前公开证据。

## Acceptance criteria

- AC-1: 在现有 Alembic head 之后新增前向迁移，为助手切片、切片级 FTS5、持久索引任务、索引 generation／manifest 和活动 generation 指针建立明确 schema；fresh database 与已升级到当前 head 的数据库均可完成 upgrade，迁移可执行 downgrade → upgrade 往返，旧迁移保持不变。迁移过程不连接 Qdrant、不调用 Embedding、也不启动 Worker；所有助手索引对象都标记为可重建派生数据，现有内容、发布修订、公开关系、认证和 `search_index` 数据及行为不被迁移或重写。
- AC-2: 单一规范 source projector 只读取已发布、未删除且带当前发布修订的文章、项目和读书笔记，以及严格复用现有 `default_profile`／`public_payload` 可见性语义的 Profile 公共投影；文章／项目／书摘的工作副本和旧修订、Profile 隐藏的城市或邮箱字段、回收站内容与后台字段不会进入切片。每个 source document 都携带可回查的类型、内容 ID、当前修订 ID 或 Profile version、标题、公开路径、内容哈希和 pipeline version；Nuxt About 静态文案不在本阶段语料中。
- AC-3: 内容先经过确定性的 Markdown 结构提取，再使用 LangChain 文档与文本切分边界按标题、段落、列表和代码块生成有界切片；模型确定前，大小和 overlap 由显式 pipeline 配置而非隐藏常数控制。相同 source 与 pipeline 必须产生相同顺序、heading path、chunk hash 和稳定 chunk ID；模型上下文所需正文得以保留，脚本、事件属性、隐藏 HTML 和纯模板噪声不会进入切片。
- AC-4: 文章、项目和书摘的首次发布与重新发布、文章 revision rollback、移入回收站、恢复和永久删除，Profile 公共投影变化，以及确实会改变索引公开文本的 taxonomy 更新，都在同一 SQLite 业务事务中写入或合并只含稳定标识与目标版本的索引任务；事务提交前不访问模型或 Qdrant。事务回滚时内容变更、现有公共 FTS5 与任务登记一起回滚；永久删除的 purge tombstone 不依赖随后会被删除或级联清理的内容外键。任务登记失败时业务事务整体失败，外部 Embedding 或 Qdrant 故障则只能让已提交任务等待重试，不能阻塞或撤销合法发布。
- AC-5: 新增 `apps/api` 所有的轻量 Worker 入口，以单消费者、单索引流水线处理租约、心跳、超时回收、有限退避、重试和终态错误；进程重启后继续未完成任务。任务执行按内容类型、内容 ID、目标修订或 Profile version、pipeline version 和 generation 幂等；重复任务、租约过期重放和旧版本晚完成都不能产生重复活动切片、覆盖新版本或把旧版本重新激活。错误与日志只保留安全摘要，不记录草稿正文、向量、API Key 或完整外部响应。
- AC-6: 全量重建在专用 staging Qdrant collection 和对应 SQLite generation 中完成，manifest 至少绑定 collection 名称、明确的 Embedding provider/model/version、向量维度、距离度量、pipeline version、有效 source revision-set 摘要、切片／向量计数、outbox high-water 和构建时间；测试替身使用显式测试标识，production 不接受空值或伪造占位。构建必须追平 high-water 之后的任务，并在短 SQLite 事务内确认没有漏事件后再切换；维度不符、数量不一致、未知 chunk、未完成构建、追平失败或探针失败均阻止活动指针切换。验证通过后以 SQLite 活动指针原子切换，仅保留 active 与 previous 两代；previous 只是恢复基线，未经重新追平和完整验证不得直接切回。增量任务只更新当前 active generation。
- AC-7: Qdrant point payload 使用字段 allowlist，仅保存 chunk ID、source type、source ID、source version／revision、generation 和 pipeline version 等稳定回查标识，不保存 `page_content`、完整正文、标题、公开 URL、任意 LangChain metadata 或其他可从 SQLite 恢复的内容；Qdrant 写入不得使用会隐式持久化正文的默认包装行为。LangChain 负责 `Document`、文本切分和 `Embeddings` 兼容边界，向量由受控适配层通过 Qdrant client 写入；删除全部 Qdrant collection 后可从 SQLite 当前公开投影全量重建。
- AC-8: 内部 Hybrid Retriever 分别执行助手 FTS5 与 Qdrant 稠密召回，使用确定性 RRF 融合并返回候选 chunk ID、来源分支、rank 和 `degraded` 状态；候选在交给任何后续消费者前必须回查 SQLite 当前公开投影，未知、旧修订、已删除或隐藏 Profile 数据被丢弃。Qdrant、Embedding query 或稠密分支不可用时只返回通过同一公开校验的 FTS5 候选并显式标记降级；FTS5 也不可用时返回空结果和稳定的 not-ready 状态，不回吐过期 dense 结果。现有 `/api/v1/search` 完全不参与该流程。
- AC-9: 内容发布后立即以 SQLite 当前公开指针作为授权真相，因此旧索引不得在五分钟异步窗口内冒充当前版本；移入回收站或永久删除后，即使 Qdrant point 或助手 FTS5 行尚未物理清理，也不能再被内部 Retriever 返回。使用受控时钟和确定性 Embedding 替身的集成测试证明本地正常任务调度满足目标五分钟窗口、旧任务竞态不会回滚新版本、永久删除后 tombstone 仍可完成外部清理、重建能追平并发发布、切换期间查询只看到完整 active generation，且失败重试不会破坏现有可用 generation；真实云端延迟与目标服务器资源验收仍留给发布准备 spec。
- AC-10: 引入的 LangChain、文本切分、Qdrant 客户端及相关依赖必须精确解析进 API lockfile；实现提供 LangChain `Embeddings` 兼容边界和无网络的确定性测试替身，但不捏造具体生产供应商。助手索引默认关闭，现有 API 在没有 Qdrant、provider 专用包和助手环境变量时保持可启动；显式启用 Worker 时若缺少 provider、model、dimension、endpoint、凭据或 Qdrant production 配置，readiness 必须失败关闭且不得生成伪向量。development/test 可使用 Qdrant 本地模式，production 只接受带认证的私有服务 URL，拒绝多进程共享嵌入式目录。索引测试不访问公网、不要求真实模型、不运行常驻后台服务，也不把数据库、向量或重日志写入仓库。
- AC-11: 本任务不新增公开或管理路由，不改变 OpenAPI 与 Web 类型，不改变现有全站搜索、文章／项目／书摘发布修订、Profile 公开字段、回收站和公开阅读行为；既有 API 在没有助手配置和 Qdrant 进程时保持启动、迁移与回归测试通过。长期 API 文档说明助手索引的默认关闭状态、Worker 所有权、配置失败语义和无真实 provider 的阶段边界；架构边界明确 SQLite 事实库、Qdrant 派生存储、浏览器不可直连和同机独立服务责任；新增持久决策记录选择 Qdrant + SQLite FTS5、generation／恢复约束、旧知识孵化不恢复、About 静态正文暂不摄入及重新评估触发器。长期文档不链接本 active spec，也不把未开放的问答助手登记成已交付产品。

## Result

Verified and closed by the harness close command.

## Evidence

[20260828-rag-index-foundation.json](../../verification/evidence/20260828-rag-index-foundation.json)

Closed at 2026-08-28T15:01:28.436504+00:00.
