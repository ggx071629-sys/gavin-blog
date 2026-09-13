---
id: architecture-boundaries
level: L1
summary: 当前已确认的应用、配置、存储、契约和部署边界
load_when:
  - architecture
  - cross-stack-change
  - deployment
author: Gavin
---

# Architecture boundaries

- 2026-09-06 本地 E5 实施新增 API 所有的独立单 owner CPU 模型进程，API/Worker 共用内部鉴权 OpenAI-compatible Embeddings；两者只加载固定 tokenizer。制品、384 维表示与 token pipeline 绑定 generation，角色前缀仅客户端添加。当前仅 development；生产仍拒绝，需后续扩展五进程资格 profile 并测量资源。见 [本地 E5 决策](../decisions/20260906-local-e5-retrieval.md)。此决定替代旧冻结生产计划的云端 Embedding 假设，不改变既有 gate/fence/readiness 责任。

- [apps/web](../../../apps/web/README.md) 拥有浏览器交互与呈现。
- 关于页助手来源读取带显式资格的当前发布修订，主动发布/回滚与 outbox 同事务；草稿与默认 seed 排除，旧版本立即失去证据资格。初次重建、混合检索和公开/管理引用复用既有链路。简历同样已接入：首次/换址自动入队，同址显式刷新；内容SQLite保存可撤销PDF及正文，既有worker运行有界下载/解析子进程，公开引用只提供当前有效版本附件；无周期检查或年龄过期。维护边界见[来源接入决策](../decisions/20260911-assistant-source-ingestion.md)。
- [apps/api](../../../apps/api/README.md) 拥有业务规则、账号与会话管理、搜索、问答、持久化与媒体协调。内容库地址由配置选择；本机真实问答使用 `.env.e5`，不能假设等于普通 `.env` 的默认库。数据目录与启动入口见 API README。
- [packages/contracts](../../../packages/contracts/README.md) 只承载跨端契约。API 路由／schema 是来源，生成 OpenAPI 快照和 TypeScript 声明；Web 的账号与简历消费者也直接使用这些生成类型，不能只维护旧的手写类型。
- 配置必须外置，业务代码不得假设具体部署平台。
- 媒体访问通过适配器隔离本地文件系统与未来对象存储。
- 内容 SQLite 是内容、不可变发布修订、引用、公开关系、搜索与认证状态的事实库，通过 Alembic 演进；独立问答 runtime 另有 schema/provisioning 边界，不能把内容库迁移等同于整个 runtime 的初始化。
- 已提交的 Alembic revision 与持久化模型接受的只读历史枚举属于升级兼容边界，不等同于当前产品模块；删除或收窄必须通过数据迁移 spec 证明旧库升级和历史记录读取不受损。
- 浏览器受支持的运行边界只通过同源 `/api/v1` HTTP REST/SSE 契约访问数据；可配置的基址覆盖项不构成跨域部署支持，契约快照位于 `packages/contracts/openapi.json`。
- 认证状态由 API 端持久化 Session 掌管，Web 端不保存认证令牌。单管理员账号修改、验证码、恢复与会话撤销由 API 执行；前端路由保护不替代认证与 CSRF 校验。
- 文章自动保存使用版本号乐观锁；版本冲突由 API 明确返回 `409`。
- 助手混合索引是默认关闭的内部基础设施：SQLite 保存规范切片、助手 FTS5、outbox、generation 指针和 Worker 所有的 index-embedding 账本；Qdrant 只保存可重建的派生向量；浏览器不可直连 Qdrant；Worker 由 `apps/api` 所有，作为同机独立进程运行，且不得打开问答 runtime 文件。Qdrant 在生产中是同机独立单节点服务，不是嵌入式多进程共享目录。
- 匿名公开问答是默认关闭的 API 内核加可选 Web 消费层。短会话、Chat/query 账本和 LangGraph checkpoint 使用独立 `assistant_runtime` SQLite 与 pinned `AsyncSqliteSaver`，仅单 API 进程持有 owner lock。runner 捕获 session/epoch/turn/thread/token execution identity；normal mutation permit 精确验证 session、turn 与 session/IP/global 三条 lease。identity-aware Saver adapter 与 stage/terminal/history/publish/DELETE/expiry 共用 per-session async serialization boundary，不在等待 boundary 或 Saver await 时持有 control 事务；expiry 只在锁内短事务复检后 tombstone，checkpoint 删除在锁外由 Saver 自行取得 boundary。checkpoint 只保存 current question、内部 ID、generation/published-version/evidence descriptor 和必要非正文状态；历史问题增强 query、hydrated evidence、历史正文、query vector、provider raw/parsed 与 terminal answer 都只在节点内瞬时使用，不进入 State、checkpoint 或 writes。RAG query 完整保留 current question，只让最新历史占用剩余上限；恢复时仅在 query fingerprint 匹配时复用已付费向量，不匹配就立即清向量并以 lexical degraded 继续，不再次调用 Embedding。失去 fence 后只允许不含原文的 conservative settlement，不能产生 event、history、checkpoint 或 live delivery。
- Chat 输入、输出与总 context 分别由显式配置约束：input 与 output 保持费用预留语义，总 context 是 operator declaration，三者和 estimator version 共同绑定 readiness。保守 estimator 使用完整 UTF-8 byte 上界和有效 provider tokenizer 的较大值；dispatch 同时满足 input cap 与 output reserve，总 output cap 下发 provider。签发新 readiness receipt 要求 Saver checkpoint/writes 已无残留，以阻止补救前 State 被新版本继续接受；该本地一致性检查不验证供应商真实模型窗口。
- 运营准入由 runtime SQLite 中默认关闭、versioned 的 gate 掌管。它把 readiness/config/active generation 与 operational epoch 绑定到 admission、sending、body mutation、Saver 和 publish；安全停用压过 stale enable。runtime 与 content SQLite 没有分布式事务，dashboard 必须保留两侧 `observed_at` 并表达 partial/stale/unknown。Chat/query 分类账本在 runtime，index 分类账本与 Worker command/progress/fence 在 content。三个分类 cap 继续生效，同时 content 中的总预算策略与预留表是 API／Worker 共同的原子费用权威；在线 runtime 准入之前先提交总额预留，runtime 确定结算后再同步收据，缺失运行记录不释放预留。总预算初值与编辑上限取三个部署分类上限的最大值而非相加；索引付费批次为有界问答留额。具体故障与恢复语义见 [管理执行与预算决策](../decisions/20260910-assistant-management.md) 和 [总预算实现](../../../apps/api/app/assistant/total_budget.py)。普通公开关闭只撤销公开执行，管理员试问使用独立执行范围；紧急停止和索引切换撤销两者。
- Worker 每进程 owner identity 唯一，通过 content SQLite 单例 heartbeat、lease 与单调 fencing token 串行工作，外部 mutation 前后复核 task fence 与当前 source revision；revision-scoped point ID/delete 与 repair intent 使旧副作用不具备检索资格。重建优先处理 active outbox，staging 按 source revision 持久续跑。Worker 只能标记 `ready_to_switch`；单 API owner 以 runtime `switch_pending`、content `BEGIN IMMEDIATE` pointer switch 和 runtime reconciliation 显式 finalize，切换后 gate 保持 disabled并要求新 receipt。
- `runner_quiescent_at` 只表示执行停止；`checkpoint_deleted_at` 只在 awaited `adelete_thread` 及 `checkpoints`/`writes` 零残留复查后成立。Saver、FK、byte accounting 或 WAL 失败写 retry fact 并打开 cleanup breaker，不把 unknown 当 0 或伪造 marker。该 runtime 及 WAL/SHM 不进入长期备份。出现第二 API 进程、非 owner 打开 runtime、共享网络文件系统或清理失败时必须失败关闭并先迁移 saver；当前 SQLite saver 的修复只证明单 owner 语义，不改变生产优先 Postgres checkpointer 的建议。双开关责任：UI on + API off 必须稳定不可用；UI off + API on 仍由后端安全控制。
- 生产资格 profile 是部署控制合同，不是运行秘密：它固定单台 2 vCPU／4 GB 上的 Nuxt、恰好一个 API owner、一个 fenced Worker、独立单节点 Qdrant、最终 edge／provider、持久本地路径、阈值和治理选择。生产 API／Worker 读取绝对 profile path 并校验 digest，再把实际运行配置逐项绑定；profile 只引用 secret source，值不得进入文件。平台专属服务定义只能在管理员选定唯一平台后生成。
- 资格证据有两层且不可互换：仓库 release／E2E 证明代码和离线合同，目标 runner 的签名 manifest 证明一次真实目标测量。Qdrant 始终是可重建派生存储；内容 SQLite 与媒体通过共同写 fence 和版本化 manifest 形成恢复点；`assistant_runtime` 为普通重启持久卷但排除于长期备份，恢复后新 runtime 将 Chat／query 锁到下一北京时间零点。北京时间 Chat、query／index Embedding 分类 cap 与共同总预算由实际配置约束；历史本机 2.00 元 Chat cap 不是所有部署的固定值，应用预算也不是供应商总账单保证。
- 未列入产品模块表的其他后台进程、外部模型服务、第三方审计和派生存储不属于当前运行边界；新增此类能力必须通过独立 spec 明确进程、数据和接口所有权。首个模型适配边界是 OpenAI-compatible Chat Completions／Embeddings，不自动发现其他供应商。
- 在部署方案形成独立 spec 前，不创建 `infra/`、`deploy/` 或存储实现目录。
