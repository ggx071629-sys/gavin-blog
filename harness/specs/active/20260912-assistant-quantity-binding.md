---
id: spec-20260912-assistant-quantity-binding
level: L1
summary: 在完整陈述中规范化中文数值和明确单位换算
author: Codex
load_when:
  - task:20260912-assistant-quantity-binding
task_id: 20260912-assistant-quantity-binding
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明数值原位规范化、已支持单位和百分比范围，以及未支持的歧义单位/算术。
state_history:
---
# Context
G02 的集合包含校验会放行对象数值交换与中文数词变更；Q2-02 已要求完整陈述支持，本任务在保留语序与限定语的前提下统一数值表达。
# Goal
中文数词、阿拉伯数值及确定时间单位可等价匹配；对象、属性、时间、范围/上下限和分母错配被拒绝。
# Non-goals
不支持不确定日历单位换算、任意算术或未声明单位语义；不改变预算、不增加外部模型。
# Acceptance criteria
- AC-1: 数值在原陈述位置规范化，中文数词、60秒=1分钟、小数/毫秒、明确范围和百分比等正例可通过；对象交换、时间/上下限反转、数值和分母变化被拒绝。
- AC-2: 既有数字、事实、自述和引用支持保护继续通过；零分母不得作为有效等价换算，文档保留歧义/未知单位的限制。
# Risks
单位不能脱离对象和陈述结构；只规范化已知单位，不把月份折算为固定天数，不把相同数字集合当作事实依据。
# Verification plan
## Verification cases
- AC-1 => M09-QUANTITY-BINDING-01
- AC-2 => M09-GAP-NUMBERS-01, M09-CLAIM-CONTEXT-01, M09-GAP-CLAIMS-01, M08-DOCS-01
## Gates
- api-tests => AC-1, AC-2
- harness-integrity => AC-1, AC-2
