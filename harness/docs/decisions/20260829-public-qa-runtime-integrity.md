---
id: decision-public-qa-runtime-integrity
level: L1
summary: 以统一 execution identity、identity-aware Saver 与浏览器 generation fence 闭合公开问答删除和迟到写入语义
load_when:
  - architecture-decision
  - assistant-online
  - public-qa
author: Gavin
---

# Public Q&A runtime integrity

## Decision

匿名公开问答继续保持默认关闭、单 API owner、独立 runtime SQLite、pinned `AsyncSqliteSaver` 与既有 LangGraph 图拓扑。每次正常或 prepared recovery runner 必须捕获不可变的 session ID、准入 fencing epoch、turn ID、thread ID 与三条 lease 共用 token；provider dispatch、应用写入、Saver 写入和 live publish 均消费该 identity。DELETE、expiry 或 lease loss 先赢后，旧 runner 只可结算已发送且结果未知的无原文费用事实。

Saver 由应用级 identity-aware adapter 包裹。adapter 与 stage、terminal、history、publish、DELETE 使用同一 per-session async serialization boundary，control fence check 保持短事务，Saver await 不持有 control transaction。checkpoint 只保存 descriptor 与必要非正文恢复状态；evidence/history 在调用前临时 hydration。`checkpoint_deleted_at` 是 awaited 删除加零残留复查的事实，不是调度意图；失败写 retry fact 并打开 breaker。

浏览器对 bootstrap、stream、status、polling 与 DELETE 使用同一单调 generation。确认删除先 advance generation、停止 timer、abort 旧请求并清除原始内存。响应最终 URL 必须与固定同源 endpoint 精确相等；GET hydration 必须先完成答案引用/path 闭包。小于 1280px 的导航与助手共享唯一 overlay owner。

## Consequences

- 最近最多 4 个完整且未清理的成功 pair 会作为明确分区、转义后的不可信历史进入生成 prompt；版本化保守 estimator 纳入 readiness fingerprint。
- questions 的 request-shape 错误稳定返回 400 `invalid_request`，只从该 operation 删除默认 422。
- 900 秒是公开可读正文硬上限；物理清理失败不能使正文重新可读，也不能伪造 marker。
- SQLite saver 仍只适用于当前单 owner 边界；多 API 进程或共享存储需要新的持久化迁移决策。

## Status and production boundary

第三阶段 archive 与 evidence 保留为历史事实；本决策记录其后审计发现并修复的语义缺口，不改写历史证据。管理员启停、健康、索引队列与费用控制面顺延为下一独立阶段。真实供应商、代理 SSE、备份恢复、目标服务器资源与公网安全仍是 production No-Go；本地 release gate 或本任务 evidence 不表示已上线、已合并或 production-ready。
