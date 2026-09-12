---
id: spec-20260912-assistant-current-query
level: L1
summary: 让当前问题优先进入普通与 E5 检索的最终词法表达式
author: Codex
load_when:
  - task:20260912-assistant-current-query
task_id: 20260912-assistant-current-query
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录当前问题优先、最近历史后置、有限词项预算和未实现语义消解的边界。
state_history:
---
# Context
Q1-04 / G09：普通和 E5 查询都把历史放在当前问题之前，最终 FTS 只取前 12 词项。长历史可让当前 Redis 问题完全消失，即使 E5 查询未超长。
# Goal
让当前问题先占用检索预算，最近历史使用剩余空间，最终精确、宽松和旧式 MATCH 保留当前问题词项。
# Non-goals
不扩大字符、token 或 FTS 词项预算，不改变全站搜索，不增加语义指代模型；当前问题本身超过词项上限时仍受原有上限约束。
# Acceptance criteria
- AC-1: 普通与 E5 查询在长历史、换题和指代样例中，最终三种 MATCH 都保留当前问题的有效词项；短指代问题仍可保留最近主题，真实 FTS 表可命中当前术语。
- AC-2: 字符与 E5 token 限制、超长词法降级、向量指纹失效和历史 query 不进入 checkpoint 的保护继续通过；API 文档说明有限范围。
# Risks
查询顺序会改变向量指纹，因此只重用与新完整查询指纹相符的向量。历史 OR 回退仍可能召回旧主题，本任务不把词项存在声称为语义相关性已解决。
# Verification plan
## Verification cases
- AC-1 => M09-E5-QUERY-01
- AC-2 => M09-UNIT-ASSISTANT-RUNTIME-INTEGRITY-REMEDIATION-01, M08-DOCS-01
## Gates
- api-tests => AC-1, AC-2
- harness-integrity => AC-1, AC-2
