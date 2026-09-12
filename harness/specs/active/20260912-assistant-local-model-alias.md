---
id: spec-20260912-assistant-local-model-alias
level: L1
summary: 接受用户确认的本机DeepSeek调用别名并保留身份与累计预算保护
author: Codex
load_when:
  - task:20260912-assistant-local-model-alias
task_id: 20260912-assistant-local-model-alias
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录新别名的本机适用范围和版本声明限制。
state_history:
---
# Context
Q2-06 首次调用的精确身份核对失败。用户明确确认 deepseek-flash 并要求修改 .env 调用。既有授权累计27次/1元，已用4次，历史和失败费用须保留。
# Goal
本机配置合同接受用户确认的 deepseek-flash，保留旧名兼容、未知名称拒绝和新配置绑定；新别名的版本依据只作为操作者声明，不伪装供应商版本证明。
# Non-goals
不放宽生产资格、费用/次数上限、凭据绑定，不重置账本；不将别名确认等同生产发布或准确率保证。
# Acceptance criteria
- AC-1: 旧别名仍兼容，新别名在本机development合同中可用且标记声明来源；实际响应模型名称仍须与请求一致；探测正常样例与既有结构化输出 supports 协议一致。
- AC-2: 未批准名称/环境拒绝，新模型改变配置摘要；已有授权不可静默改绑，累计预算与失败恢复保护不回退。
# Risks
供应商版本映射尚无独立证据，实际质量结果必须注明声明版本而非响应证明。旧probe/readiness不能自动冒充新模型资格。
# Verification plan
## Verification cases
- AC-1 => M09-LOCAL-MODEL-ALIAS-01, M09-G07-RUNNER-01, M08-DOCS-01
- AC-2 => M09-REVALIDATION-COMPAT-01, M09-REVALIDATION-BUDGET-01, M09-REVALIDATION-RECOVERY-01
## Gates
- api-tests => AC-1, AC-2
- harness-integrity => AC-1, AC-2
