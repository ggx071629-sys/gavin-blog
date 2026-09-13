---
id: decision-public-qa-runtime-integrity-remediation
level: L1
summary: 以瞬时历史查询、expiry/Saver 共锁和显式 context window 补救公开问答第四阶段完整性缺口
load_when:
  - architecture-decision
  - assistant-online
  - public-qa
author: Gavin
---

# Public Q&A runtime integrity remediation

## Context

第四阶段 `20260829-public-qa-runtime-integrity` 已按当时 Harness 契约关闭，archive、evidence、close event 与原 durable decision 保持历史原样。关闭后语义复核发现：历史问题拼接后的 retrieval query 曾成为 LangGraph State；expiry sweep 曾绕过 identity-aware Saver 共用的 session boundary；Token byte fallback 和 output reserve 曾不足以证明调用落入声明的模型 envelope。

## Decision

- 保持既有 LangGraph 节点和边拓扑。`AssistantState` 不再包含历史派生 query；retrieve 节点从仍 active 的同 session 未 purge 成功历史只读取问题，在完整保留当前问题后用最新历史填充剩余 query 上限，并直接交给 query Embedding 和 Hybrid Retriever。历史答案只在 generate 节点构造不可信 prompt，历史 query、历史正文和 hydrated evidence 都不成为 node output、checkpoint 或 writes。恢复时只有 query fingerprint 精确匹配才复用已付费向量；历史变化或旧 fingerprint 不匹配时清除 transient vector、走 lexical degraded，不产生第二次付费调用。
- expiry sweep 先读取候选 session ID，再逐 ID 获取 Saver、DELETE、stage、terminal 共用的 per-session async boundary。取得后用短 control 事务复检 expiry/tombstone，再 tombstone、安全终结并释放 lease；事务提交后、释放锁前关闭 live hub。等待 boundary 和 Saver await 都不持有 control 事务，checkpoint 删除在锁外继续由 identity-aware Saver 取得锁。
- 保留 `assistant_chat_max_input_tokens` 的最大完整输入与费用语义，保留 `assistant_chat_max_output_tokens` 的最大生成与费用预留语义，新增部署必填的 operator-declared `assistant_chat_context_window_tokens`。配置必须满足 input cap 加 output cap 不超过总窗口；dispatch 同时验证实际保守 input estimate 与 output reserve，output cap 作为 `max_completion_tokens` 下发。
- estimator 版本递增；完整 system/schema/question/evidence/history serialization 采用 UTF-8 byte 数加固定结构开销的上界，并与有效 provider tokenizer 取较大值。tokenizer 缺失、零值、负值或异常不能降低 byte bound；预算不足按完整 pair 从最旧历史裁剪，仍不 fit 时零 Chat 调用。三项 token 限制与 estimator version 共同进入 readiness fingerprint；新 receipt 仅可在 `checkpoints`/`writes` 零残留时签发，补救前 checkpoint 不能被新版本默许。

## Consequences

- estimator 或 token envelope 变化会使旧 readiness receipt 失效；启用前必须重新签发。
- byte 上界会主动牺牲部分 history/evidence 容量以换取 fail-closed；operator declaration 只验证配置内部一致性，不证明供应商真实 context window。
- 本补救不改变公开 API、每日 2.00 元额度、历史四轮上限、900 秒正文保留期、Qdrant/RAG 身份或单 API owner 边界。

## Status and production boundary

本决策只闭合第四阶段关闭后发现的三个缺口，不追溯改写原 archive/evidence/decision，也不表示项目已上线或 production-ready。第五阶段管理员运营控制面保持未开始；真实供应商、代理 SSE、备份恢复、目标服务器资源与公网安全仍是 production No-Go。

上句“第五阶段保持未开始”记录本决策作出时的状态，不是当前状态。后续 [公开问答运营控制面决策](20260829-public-qa-admin-operations.md) 已交付默认关闭的 `/admin/assistant`；该后续交付不改变本决策的完整性补救内容，也不解除 production No-Go。
