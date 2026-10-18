---
id: archive-20260803-incubator-retrieval-index
level: L2
summary: 为已发布文章建立不可变发布版本、本地混合检索索引与可验证的模型准备闭环
load_when:
  - task:20260803-incubator-retrieval-index
author: Gavin
task_id: 20260803-incubator-retrieval-index
status: compressed
restoration_source: "f2f785e79fa7cc7c04b8b669775fed16a0f9496f:harness/specs/active/20260803-incubator-retrieval-index.md"
restored_at: 2026-08-11
---

# 20260803-incubator-retrieval-index

Deterministic compressed record. The original active spec remains in Git history.

## Goal

每次普通文章发布都创建不可变、单调编号的发布修订；自动保存只更新工作副本，公开页面和公共搜索继续读取最近一次正式发布快照。文章发布事务同时登记待索引任务，独立 Worker 对当前已发布且未删除文章执行结构化切片、FTS5 关键词索引和 384 维本地嵌入，在完整成功后原子切换当前索引。管理员可以观察模型与索引健康度、重建索引，并对待处理资料执行不调用第三方服务的混合检索预览。只有模型、全量索引和检索质量门槛均就绪时，系统才声明可供后续正常审计使用。

## Acceptance criteria

## 1. 全局文章发布修订

- Alembic 增加文章发布修订及其索引状态实体，并让文章显式指向当前正式发布修订。发布修订按文章从 1 单调递增且不可更新或删除，现有 `articles.version` 继续只承担工作副本的编辑乐观锁。
- 每个发布修订完整保存标题、slug、摘要、Markdown 正文、首次发布时间、该次发布发生时间、栏目 ID 与名称／slug 快照、标签 ID 与名称／slug 有序快照、变更来源和规范内容 SHA-256。普通编辑器发布的来源为 `editor`；后续预留的孵化与回滚来源本段不产生。
- 迁移为所有 `status = 'published'` 且存在 `published_at` 的存量文章按当前内容创建唯一基线修订 1，不伪造更早历史；草稿不创建发布修订。软删除的已发布文章保留基线历史但不进入有效索引语料。
- 首次发布创建修订 1；后续每次明确点击发布都创建新修订，即使内容校验值与上一版相同也保留这次人工发布事实。修订创建、文章当前发布指针更新、公共 FTS5 同步、索引状态和幂等索引任务登记处于同一 SQLite 事务；事务失败不留下半个版本或孤立任务。
- 已发布文章的 PATCH／自动保存只改变工作副本并增加 `articles.version`，不创建发布修订、不更新当前发布指针、不改变公开 API／页面、RSS、站点地图或公共 `search_index`。管理响应增加当前发布修订号和 `has_unpublished_changes`，让编辑器明确显示未发布修改。
- 公开文章读取、公开列表和公共搜索的标题、摘要、正文、slug 与文章分类关联均来自当前发布修订；分类 ID 在公开展示时解析当前仍存在的栏目／标签名称，修订内名称／slug 快照只用于历史、校验和未来回滚。栏目／标签自身的管理修改继续按既有规则即时生效。
- 软删除立即从公开读取、公共搜索与孵化语料中移除，但不删除发布修订、切片或嵌入历史。恢复已发布文章时，公开内容恢复到当前正式发布修订；只有相同 pipeline 与模型 manifest 的该修订索引仍完整时才可原子重新启用，否则登记幂等重建任务并保持检索为 stale。

## 2. 索引数据与持久任务

- 数据层职责至少覆盖文章发布修订、文章片段、文章嵌入、修订索引状态和当前活动索引指针。片段与嵌入属于一个明确的发布修订和 `pipeline_version`，不能只绑定可变 `articles` 行。
- `incubator_jobs` 保留现有摄入任务兼容性，并允许索引任务以数据库外键绑定文章发布修订；摄入事件和文章修订归属二选一，数据库 CHECK 保证恰有一个归属。现有摄入任务、租约、取消、重试和 Worker 健康语义不得回退。
- 索引任务类型固定为 `article_index`，幂等键由文章 ID、发布修订号、pipeline version、嵌入模型 revision 和 manifest checksum 共同决定。重放、租约过期或并发领取不能创建重复片段、FTS 行、嵌入或活动指针切换。
- 索引状态至少覆盖 `pending`、`processing`、`ready`、`failed`、`stale`，记录进度、片段数、模型与 pipeline 版本、manifest checksum、最后错误和完成时间。任务失败映射稳定错误码并允许管理员重试，不回滚已经公开的文章版本。
- 存量迁移只写入基线修订、待索引状态和幂等任务，不加载模型、不执行切片或向量计算。Worker 启动后串行消费；模型相关任务并发始终为 1。

## 3. 确定性文章切片

- 切片输入只使用当前发布修订快照。切片器有显式 `pipeline_version`，以嵌入模型 tokenizer 计数；同一发布修订、pipeline 和 tokenizer manifest 必须生成相同片段序号、标题路径、正文快照、Token 数与片段 SHA-256。
- 优先按 Markdown H2／H3 及其完整层级路径切片；目标为 320–400 Token，相邻正文窗口约 50 Token 重叠。列表、表格、引用和围栏代码块尽量保持完整；超长代码块按行拆分，单行仍超出硬上限时才按 Token 安全拆分。
- 每次模型输入包含标题与标题层级开销且不得超过模型 512 Token 上限。空文章不会发布；只含短正文的文章允许产生一个少于 320 Token 的片段，不通过填充或复制达到目标。
- 片段保存文章 ID、发布修订 ID／号、片段序号、标题和完整标题路径、正文快照、Token 数、pipeline version 和校验值。384 维 L2 归一化向量以固定 little-endian float32 BLOB 保存，长度必须严格为 1536 bytes，不保存为 JSON。

## 4. 模型准备、完整性与运行时

- 提供独立 `apps/api/scripts/prepare_retrieval_models.py`。只有该显式部署命令允许联网：它从本规格固定的两个官方仓库与 revision 下载必要的源 ONNX、tokenizer、config 和许可证文件，逐项校验版本化 source manifest 后，在临时目录生成通用 QInt8 模型，验证推理结果和维度，再原子发布完整 runtime manifest。
- runtime manifest 至少记录仓库、完整 revision、所有源与生成文件 SHA-256、量化工具及版本、ONNX opset、CPU execution provider、tokenizer 配置、最大 Token、嵌入维度、准备时间和 pipeline version。任一文件缺失、额外、校验失败或模型输出不符时准备命令失败且不替换已有可用 manifest。
- 模型根目录由 `GAVIN_RETRIEVAL_MODEL_ROOT` 外置配置，默认位于本地 `./data/models`；模型目录和二进制明确加入 Git 忽略。API 与 Worker 启动及运行时禁止访问模型仓库或自动下载，只从本地 manifest 加载。
- 运行依赖使用有边界的 NumPy、ONNX Runtime CPU 与 tokenizer 库，不引入 PyTorch、独立模型服务或 GPU 假设。嵌入与重排序 session 按需顺序加载，阶段完成后释放；不得长期同时常驻。测试证明 2 vCPU／4 GB 基线无 OOM。
- 嵌入输入遵守模型卡的 `query:`／`passage:` 前缀并执行 L2 归一化。重排序输入是 `(query, passage)` 对。所有 tokenizer 截断必须显式且可观察，不能依赖库默认值静默改变结果。
- `GET /api/v1/admin/incubator/retrieval/health` 在未配置、文件缺失、校验失败、模型不可执行、索引 stale 和 ready 之间给出稳定状态与中文说明，不返回本地绝对路径。未就绪时完整检索返回 `LOCAL_MODEL_NOT_READY` 或 `ARTICLE_INDEX_STALE`。

## 5. FTS5、向量与原子索引一致性

- 为孵化语料建立独立 FTS5 片段索引，不复用覆盖项目和读书笔记的公共 `search_index`。FTS 行只能来自当前已发布且未删除文章的发布修订，并携带可回查的片段 ID；适合中文与中英混合的 tokenizer／查询构造必须由基准验证。
- 发布事务只登记索引状态与任务，不加载本地模型。Worker 在非活动 staging 集合中完成切片、FTS 行和全部嵌入；全部数量、校验和维度通过后，使用一个短事务把文章活动索引指针切换到新发布修订，再清理旧修订的可再生成索引数据。
- 新修订索引失败时旧索引数据可以保留，但不得冒充最新语料。只要任一当前已发布且未删除文章的当前发布修订没有 `ready` 活动索引，完整语料全局状态就是 stale，后续正常审计必须暂停并显示已完成／总数和失败项。
- 文章在索引期间再次发布时，旧任务可以安全结束但不能切换活动指针；最新发布修订拥有唯一切换资格。删除文章时活动语料指针在事务内失效；恢复规则遵守第 1 节。
- 更换嵌入模型 revision、manifest checksum、tokenizer 或切片 pipeline 必须把全部有效文章标为 stale 并重建向量；只更换 reranker 不重建向量，但完整检索保持未就绪直到重新通过质量基准。
- 有效片段不超过 50,000 时，应用通过 NumPy 对 SQLite 读出的归一化向量批量计算余弦相似度。超过 50,000 或实测延迟不达标只产生可观察评估提示，不自动引入新存储或服务。

## 6. 混合检索服务

- 提供只接受 `incubator_revisions.id` 的内部检索服务和受 Session／CSRF 保护的 `POST /api/v1/admin/incubator/retrieval/preview`。预览只执行本地确定性处理，不调用第三方服务、不改变资料状态、不创建审计报告。
- 检索输入构造器有显式版本，从当前资料修订的标题、H2／H3 路径和正文生成有界查询窗口；每次模型调用不超过 512 Token。窗口数量、合并权重和截断统计进入版本化配置与响应元数据，并在质量基准通过前不得宣称 ready。
- FTS5 关键词召回 Top 20 片段，`multilingual-e5-small` 语义召回 Top 20 片段；以 RRF（`k = 60`）合并去重后保留 Top 20 片段，交给选定 L12 cross-encoder 重排。
- 重排后按版本化最低相关门槛过滤，再按文章聚合：最多返回 8 篇文章，每篇只返回最相关的 1–3 个片段。低于门槛的候选不用于凑数，结果可以少于 5 篇或为空。
- 每个结果包含文章 ID、当前发布修订 ID／号、标题、摘要、片段稳定 ID／序号、标题路径、文本快照、FTS／语义／融合／重排分数、模型 revision、pipeline version、候选数量和截断统计；不返回文章工作副本或其他内容类型。
- 版本化相关门槛、查询窗口参数和必要的融合权重必须由第 8 节真实基准选择并提交为小型配置，不能凭单个示例任意设定。参数变化使既有质量报告失效。
- 服务提供显式 `fts_only` 降级模式，跳过嵌入与重排并在每个结果和响应顶层标记 `degraded = true`。本段只用于预览和后续应急路径准备；降级结果不能被后续阶段授予批量确认资格。

## 7. 管理 API 与界面

- `GET /api/v1/admin/incubator/retrieval/health` 返回两个模型的配置／校验／可执行状态、pipeline version、有效文章数、ready／pending／processing／failed／stale 数、片段总数、活动 manifest 标识、最后完成时间和重建进度。
- `POST /api/v1/admin/incubator/indexes/rebuild` 接受 `scope = missing|all` 并返回 `202` 与新建／复用的任务摘要；`missing` 只补当前发布修订的缺失或失败索引，`all` 需要前端二次确认并为全部有效文章创建新 pipeline staging。重复请求通过幂等键复用未结束工作。
- `POST /api/v1/admin/incubator/retrieval/preview` 接受 `source_revision_id` 和 `mode = full|fts_only`；完整模式在模型或索引未就绪时不创建后台任务、不执行部分模型调用并返回稳定错误，降级模式始终显式标注。
- 现有 `/api/v1/admin/incubator/overview` 增加检索模型和索引摘要；`/admin/incubator` 显示未配置、准备中、建索引中、stale、失败和 ready，提供重建操作与进度。绝不在浏览器显示模型根绝对路径或下载凭据。
- `/admin/incubator/inbox/{source_id}` 在本地索引可用时提供“检索预览”，展示候选文章、版本、章节片段、各阶段分数和降级标记；预览不会出现审计、确认或生成按钮。刷新页面不会自动重新执行重模型调用，只有管理员显式触发。
- OpenAPI 继续作为跨端契约来源并同步 `packages/contracts/openapi.json` 与 Web 类型。所有新读取要求管理员 Session，重建与预览 POST 同时要求 CSRF；前端通过稳定错误码映射中文说明。

## 8. 质量基准与验收门槛

- 提供可重复的本地检索评测命令，读取当前已发布文章数据库和至少 30 条轻量标注案例；案例只提交查询、期望文章稳定标识、语言类别和必要标签，不复制整篇文章正文。覆盖中文、中文夹英文术语、英文错误信息和同义改写。
- 基准明确区分召回与重排：FTS＋语义合并的 `Recall@20 >= 95%`，重排聚合后的 `Recall@8 >= 90%`；中英混合集合任一指标不得比整体低超过 5 个百分点。低于门槛时模型／索引健康不能为 ready。
- 在受控 2 vCPU／4 GB 环境记录峰值 RSS 和端到端本地检索时间；无 OOM且单条完整召回与重排序在 60 秒内完成。紧凑 evidence 只保存命令、环境摘要、指标、阈值、参数版本和通过／失败，不提交原始向量、模型、数据库或重日志。
- Pytest 覆盖发布快照隔离、存量基线、事务回滚、工作副本不公开、任务归属约束、切片边界、向量格式、模型 manifest、防运行时下载、索引重放／竞态／失败／恢复、语料边界、融合排序、门槛过滤和降级标记。
- Vitest 覆盖发布脏状态、健康状态／错误映射、重建确认、进度和检索预览；Playwright 使用小型确定性 ONNX 或同契约本地测试替身覆盖“编辑已发布文章但公开内容不变 → 发布新修订 → 索引 stale → Worker 完成 → ready → 资料检索预览”的代表性闭环，不访问互联网。

## Result

Verified and closed by the harness close command.

## Evidence

[20260803-incubator-retrieval-index.json](../../verification/evidence/20260803-incubator-retrieval-index.json)

Closed at 2026-08-03T17:07:59.036559+00:00.
