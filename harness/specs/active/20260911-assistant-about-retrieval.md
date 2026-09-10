---
id: spec-20260911-assistant-about-retrieval
level: L1
summary: Q2-03 将关于页加入初次重建与有界混合检索
load_when:
  - task:20260911-assistant-about-retrieval
task_id: 20260911-assistant-about-retrieval
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录关于页初次重建和预算内检索行为。
state_history:
---
# Context
Q2-01/02 已关闭；关于页投影和 outbox 已存在，初次公开来源枚举仍缺 about。
# Goal
让合格关于页通过现有 worker 初次构建和关键词/向量混合检索，复用证据预算与版本复检。
# Non-goals
不修改 embedding、tokenizer、checkpoint、预算、生产资格或引用前端。
# Acceptance criteria
- AC-1: 自动 seed 不加入重建，主动修订生成可检索切片；FTS/向量可召回且证据满足预算；更新等待时旧 evidence 被拒绝，其他有效来源仍可用。
# Risks
初次枚举必须调用同一投影资格判断，不能读取工作副本或绕过版本 fence。
# Verification plan
## Verification cases
- AC-1 => M09-ABOUT-RETRIEVAL-01
## Gates
- api-tests => AC-1
- harness-integrity => AC-1
