---
id: spec-20260829-public-qa-runtime-integrity-remediation
level: L1
summary: 修复第四阶段遗漏的 checkpoint 正文、expiry/Saver 竞态与保守 Token 预算语义
load_when:
  - task:20260829-public-qa-runtime-integrity-remediation
author: Gavin
task_id: 20260829-public-qa-runtime-integrity-remediation
status: active
verification_profile: release
verification_escalation: 第四阶段补救同时触及持久化、并发 fencing、模型调用预算与默认关闭的公开问答路径，完成前重新执行完整 release bundle。
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - harness/docs/product/brief.md
  - harness/docs/architecture/boundaries.md
  - harness/docs/operations/release-readiness.md
  - harness/docs/decisions/20260829-public-qa-runtime-integrity-remediation.md
documentation_reason: 本任务纠正第四阶段已记录但未被实现和测试充分证明的 descriptor-only checkpoint、expiry serialization 与保守模型预算边界，必须同步 API、产品路线、架构、运维并以独立补救决策保留历史层次。
state_history:
---

# Context

`20260829-public-qa-runtime-integrity` 已由 Harness 形式关闭，原 archive 与 evidence 必须保持历史原样。关闭后的语义复核发现三个未被现有断言捕获的缺口：历史问题拼接后的 `retrieval_query` 进入 LangGraph State，因而会同时写入 checkpoint 和 node writes；expiry sweep 未取得 identity-aware Saver 共用的 per-session serialization boundary；Token estimator 把 UTF-8 byte length 除以四、tokenizer 失败时退为零，且 output reserve 被恒等式抵消、真实 Chat adapter 未应用配置的输出上限。这些缺口直接违反第四阶段 AC-4、AC-11 与 AC-12，不能留给第五阶段。

# Goal

在不改写第四阶段 archive/evidence、不改变公开 API、LangGraph 拓扑、RAG 索引身份、费用额度和单 API owner 边界的前提下，使历史正文只在检索与生成节点内瞬时加载，expiry 与 Saver 写入服从同一 session 顺序，并让模型调用只有在保守输入估算加输出预留可证明落入配置上下文上限时才发生。修复由离线确定性测试和新的 release evidence 证明，随后关闭本补救 Spec 并停止，不进入第五阶段。

# Non-goals

- 不设计或实现第五阶段的管理员启停、健康、索引队列、费用看板或其他运营控制面。
- 不修改既有 `20260829-public-qa-runtime-integrity` archive、evidence 或 close event，不把历史证据追溯改写为已覆盖本补救。
- 不改变公开 Web/API/Contracts 形状、问答次数、每日 2.00 元额度、历史最多四轮、900 秒保留期或 prompt-injection 产品范围。
- 不迁移 SQLite Saver、Qdrant、内容库或 schema，不增加第二 API owner、外部服务、部署结构或真实供应商资格声明。
- 不以 provider 在线调用、非确定性等待或人工日志作为验收证据。

# Acceptance criteria

- AC-1: `AssistantState`、checkpoint 与 `checkpoint_writes` 不含历史派生 query 或任何上一轮 question/answer 正文；RAG retrieve 节点必须在执行时从同一 active session 临时加载允许的历史问题，与 current question 生成局部 query，并把该局部值直接交给 query Embedding 与 Hybrid Retriever，不能作为节点输出或 State 字段返回。带唯一上一轮 question/answer sentinel 的确定性测试同时证明 sentinel 不出现在 checkpoint/writes，而 query Embedding 捕获值仍包含允许的上一轮问题；当前 question 与 descriptor-only 恢复语义保持不变。
- AC-2: expiry sweep 先只读取候选 session ID，再逐 session 取得与 identity-aware Saver、DELETE、stage 和 terminal 相同的 async serialization boundary；取得后必须在一个短 control 事务内重新验证未 tombstone 且 idle/absolute expiry 已到，再完成 tombstone、安全 recovery terminal 与 lease release，并在释放 boundary 前关闭对应 live hub。不得在等待 session boundary 或任何 Saver `await` 时持有 control 事务；checkpoint 删除继续由锁外的 identity-aware Saver 自行取得 boundary，禁止非重入。确定性 barrier 必须证明活动 Saver 临界区未释放前 expiry 不能 tombstone，释放后 expiry 才可提交，并且 tombstone 之后旧 identity 的 Saver write 仍被拒绝。
- AC-3: estimator version 递增；新增部署必填的 operator-declared `assistant_chat_context_window_tokens`，保留既有 `assistant_chat_max_input_tokens` 为最大完整输入、`assistant_chat_max_output_tokens` 为最大生成与费用预留的语义，三项限制与 estimator version 一同进入 readiness fingerprint。输入估算取完整 serialized system、structured-output schema、current question、evidence、完整 history 与固定 message 开销的 UTF-8 byte length 保守上界和 provider tokenizer 正整数结果的较大值；tokenizer 缺失、返回零/负值或抛错都不能降低 byte bound。在线配置必须 fail closed 于 `max_input + max_output > context_window`；dispatch 同时满足 `estimated_input <= max_input` 与 `estimated_input + max_output <= context_window`，OpenAI-compatible adapter 必须把 output cap 作为实际最大生成 token 数传给 `ChatOpenAI`。预算不足时先从最旧完整 history pair 裁剪，零历史仍不 fit 时 Chat provider call count 为零；本地声明不声称已验证供应商真实 context window。
- AC-4: 离线 API 测试明确覆盖上一轮正文 checkpoint/writes 反向断言与 transient RAG 正向断言、expiry-vs-Saver 顺序、tokenizer 高值/零值/负值/异常、最旧历史裁剪、无历史仍超预算的 zero-dispatch、三项 context 配置校验、estimator/readiness 版本绑定及 Chat adapter 输出上限；部署配置示例同步新增必填 context window。不得使用固定 sleep、恒真断言、网络供应商或只检查最终状态而不检查顺序和调用次数。
- AC-5: 长期文档明确说明第四阶段原 archive/evidence/决策仍是历史事实，本补救只闭合其后发现的三个实现/证据缺口；新决策记录 transient history query、expiry serialization、operator-declared context window 与实际 output cap 的边界，并继续保持默认关闭、单 owner、SQLite Saver 多进程限制和 production No-Go。第五阶段保持未开始。

# Risks

- 从 State 移除历史 query 后，resume 会重新读取当前仍允许的历史；节点必须保持幂等，且只使用未 tombstone、未 purge 的同 session 成功历史。
- expiry 与 Saver 共用 session 锁会改变锁等待顺序；若在等待锁时持有 control 事务或在锁内调用会重入同一锁的路径，会造成数据库阻塞或死锁。
- byte-per-token 上界会显著保守，可能减少可用 evidence/history；这是宁可拒绝付费调用也不在未知 tokenizer 下超 context 的预期取舍。新增 context window 由部署者按供应商文档声明，本地只验证配置内部一致性。
- estimator version 变化会使旧 readiness receipt 失效；启用前必须重新签发，不能静默复用旧 receipt。

# Verification plan

- api-lint => AC-1, AC-2, AC-3, AC-4
- api-tests => AC-1, AC-2, AC-3, AC-4
- harness-integrity => AC-5
- release => AC-1, AC-2, AC-3, AC-4, AC-5
