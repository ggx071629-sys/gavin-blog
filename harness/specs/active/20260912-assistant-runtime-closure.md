---
id: spec-20260912-assistant-runtime-closure
level: L1
summary: Q3-06 核验并发费用故障并封闭无结果供应商边界
load_when:
  - task:20260912-assistant-runtime-closure
task_id: 20260912-assistant-runtime-closure
status: active
verification_profile: stack
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 明确无可观察结果仍为未知，保守结算且不得格式重试。
state_history:
---

# Context
Q3-05 已验收。阶段收尾重查新增阶段观测及反馈之后的并发与费用保护；返回空 envelope 不能被记录为成功响应。

# Goal
完成阶段三当前版本的并发、费用与故障回归，并将没有 raw 或 parsed 结果的调用按未知处理。

# Non-goals
不增加付费调用、不改变预算、并发、TTL 或部署资格；不宣称生产延迟或吞吐。

# Acceptance criteria
- AC-1: 无可观察结果的供应商调用只发送一次，保守结算为 unknown，幂等读取不重发；已收到格式错误仍走既有有界纠正。
- AC-2: 慢检索不阻塞会话、心跳和清理；取消和停机保留容量与资源顺序；迟到结果不恢复正文或重复扣费。
- AC-3: 并发费用预留不超售，成功/未知计量和结算保持一次性，恢复仍保持费用锁。
- AC-4: 文档明确本地故障验证和真实模型/生产未测边界。

# Risks
本地故障注入不能证明实际供应商可用性或生产性能。

# Verification plan
## Verification cases
- AC-1 => M09-RUNTIME-CLOSURE-01, M09-RETRY-FEEDBACK-01, M09-RETRY-FAILURE-01
- AC-2 => M09-RETRIEVAL-IO-01, M09-RETRIEVAL-IO-02, M09-RETRIEVAL-IO-03
- AC-3 => M10-TOTAL-BUDGET-01, M09-METERED-LATENCY-01
- AC-4 => M08-DOCS-01
## Gates
- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-4
