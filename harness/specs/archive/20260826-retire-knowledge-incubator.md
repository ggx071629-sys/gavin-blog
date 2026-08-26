---
id: archive-20260826-retire-knowledge-incubator
level: L2
summary: 在可恢复归档知识孵化实现与数据后，从博客主项目退役其摄入、检索、审计、生成和发布工作台运行面
load_when:
  - task:20260826-retire-knowledge-incubator
author: Gavin
task_id: 20260826-retire-knowledge-incubator
status: compressed
documentation_impact: required
documentation_targets:
  - README.md
  - apps/web/README.md
  - apps/api/README.md
  - packages/contracts/README.md
  - harness/docs/product/brief.md
  - harness/docs/product/knowledge-incubator.md
  - harness/docs/architecture/boundaries.md
  - harness/docs/decisions/20260814-zvec-derived-vector-index.md
  - harness/docs/decisions/20260826-retire-knowledge-incubator.md
documentation_reason: 退役知识孵化会改变已交付产品范围、API 与进程拓扑、持久化和依赖边界，并取代现有 Zvec/Retrieval Service 决策，必须同步长期产品、应用、契约和架构文档。
state_history:
---

# 20260826-retire-knowledge-incubator

Deterministic compressed record. The original active spec remains in Git history.

## Goal

建立可独立克隆和恢复的知识孵化最终归档，保存退役前的完整 Git 实现、运行说明和一致性数据备份；随后从博客主项目移除知识孵化的用户入口、API、Worker、Retrieval Service、LLM/检索配置、专属数据库对象、依赖与质量负担，同时完整保留普通内容的不可变发布修订、修订差异与回滚、公开参考资料、wikilink/反链、公开搜索和 taxonomy 语义。

## Acceptance criteria

- AC-1: 创建私有独立归档仓库并保存带标签的退役前完整 Git 快照；归档记录源仓库、源 commit、标签、依赖与恢复步骤，能够重新克隆并校验同一 commit，且 Git 历史不含 `.env`、真实数据库、模型二进制或日志。当前 SQLite 通过停写后的 backup API 生成独立加密备份并记录表计数与 SHA-256，恢复说明明确其与 Git 归档分离。
- AC-2: Web 不再提供知识孵化导航、页面、组件或轮询入口；OpenAPI 不再暴露 `/api/v1/admin/incubator*` 路径，删除的管理 URL 返回不存在且公开站与普通写作台保持可用。
- AC-3: 普通文章发布、删除、恢复与修订回滚不再创建或依赖孵化 Job、文章检索索引、审计失效或 Retrieval Service；`ArticleRevision`、revision tags、`current_revision_id`、公开引用快照、修订列表/详情/差异/回滚、wikilink/反链、公开搜索和 taxonomy 行为保持不变。
- AC-4: 在现有迁移 head 之后新增前向收缩迁移，只删除孵化 source/audit/draft/publish/job/token、`article_index_*`、embedding、Zvec generation 与 `incubator_fts` 等专属对象；旧 migration 文件和核心 revision/public-reference 对象保留。空库与含现有孵化关系数据的数据库副本均可升级，升级前后的普通内容、发布 revision、公开引用和链接计数及内容哈希一致。
- AC-5: 主 API、E2E runner 与生产配置不再要求或启动 Worker、Retrieval Service、URL 摄入、LLM 审计、模型或 Zvec；移除仅由孵化使用的 NumPy、ONNX Runtime、Tokenizers、Zvec 与部署 ONNX 依赖并重新锁定依赖，主 API 在没有任何孵化环境变量时通过运行时校验和健康检查。
- AC-6: 删除或改写孵化专属 API/Web 单元、集成与 E2E 测试，同时保留并增强普通发布 revision、回滚、迁移、搜索、taxonomy 与公开引用测试；发布总门禁不再执行孵化旅程，OpenAPI、Web 类型和质量门禁与退役后的产品边界一致。
- AC-7: 长期产品、Web/API、契约和架构文档明确知识孵化已退役；Zvec 决策标记为被退役决策取代。两个冻结 GitHub 摄入规格保持冻结核心摘要不变，但追加明确的退役处置说明，禁止后续静默恢复到已移除的主项目摄入边界。
- AC-8: 回滚边界经过验证：删表前应用可通过重新启用归档 commit 回滚；执行前向收缩迁移后只能通过已校验的一致性 SQLite 备份或结构化反向导入恢复孵化数据，不能依赖会删除核心 revision 的历史 downgrade，也不能只复制带 WAL 的主数据库文件。

## Result

Verified and closed by the harness close command.

## Evidence

[20260826-retire-knowledge-incubator.json](../../verification/evidence/20260826-retire-knowledge-incubator.json)

Closed at 2026-08-26T15:42:55.088417+00:00.
