---
id: spec-20260912-assistant-stage-diagnostics
level: L1
summary: Q3-04 关联无正文阶段诊断与实际调用耗时
load_when:
  - task:20260912-assistant-stage-diagnostics
task_id: 20260912-assistant-stage-diagnostics
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 明确阶段耗时、候选数量、版本与费用关联记录的位置和局限。
state_history:
---

# Context
G18 尚无有效阶段耗时，query Embedding 使用发送前快照结算可能漏记 metered event。

# Goal
关联同一 turn 的检索、生成、校验、重试和终态无正文诊断，持久化已观察调用耗时。

# Non-goals
不提高预算、不外发追踪、不增加正文留存；本项不宣称生产百分位性能。

# Acceptance criteria
- AC-1: 检索候选/过滤/选中数量、代次与策略版本、各阶段及重试和终态可按 turn 关联，记录不含问答、引文、标题或异常正文。
- AC-2: Chat/query Embedding 成功及失败耗时被记录；query 发送态费用事件不遗漏，重放结算不重复；未知仍保守结算。
- AC-3: 文档区分持久化事件和结构化日志、已观察耗时与未测生产 P95。

# Risks
同步调用取消后仍可能迟到；阶段取消和实际供应商耗时不同，不能混为性能保证。

# Verification plan
## Verification cases
- AC-1 => M09-STAGE-DIAGNOSTICS-01, M09-RETRIEVAL-IO-02, M09-RETRIEVAL-IO-03, M09-RETRY-FEEDBACK-01, M09-RETRY-FAILURE-01
- AC-2 => M09-METERED-LATENCY-01
- AC-3 => M08-DOCS-01
## Gates
- api-tests => AC-1, AC-2
- harness-integrity => AC-3
