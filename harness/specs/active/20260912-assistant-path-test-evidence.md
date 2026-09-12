---
id: spec-20260912-assistant-path-test-evidence
level: L1
summary: 修复技术路径回归的事实支持前提并保留无据反例
load_when:
  - task:20260912-assistant-path-test-evidence
author: Codex
task_id: 20260912-assistant-path-test-evidence
status: active
verification_profile: focused
documentation_impact: none
documentation_reason: 只修复既有测试证据前提，不修改产品行为、契约或持久化。
state_history:
---

# Context

Q2-07选定33条API回归中技术路径保持测试失败；其来源不包含断言路径。对本轮前6ae87a4校验器复现相同grounding，不能通过放宽事实校验修测试。

# Goal

先断言无依据路径被拒绝，再以真实包含该技术路径的证据验证不会被当成来源地址替换。

# Non-goals

不改业务校验或删除路径保真断言，不引入模型调用。

# Acceptance criteria

- AC-1: 8种技术路径有证据时保持原样及引用，无对应事实来源时仍grounding；提示来源地址及历史边界继续断言。

# Risks

错误前提修复不得变成弱化断言；正反例同时保留。

# Verification plan

## Verification cases

- AC-1 => M09-ANSWER-PATHS-02

## Gates

- api-tests => AC-1
- harness-integrity => AC-1
