---
id: spec-20260912-assistant-g07-authorized-envelope
level: L1
summary: 绑定用户批准的G07累计100次2元授权
load_when:
  - task:20260912-assistant-g07-authorized-envelope
author: Codex
task_id: 20260912-assistant-g07-authorized-envelope
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - plan-build/assistant-gap-closure/evaluation/G07-EXECUTION.md
documentation_reason: 保存用户明确批准的累计上限和既有账本历史保留要求。
state_history:
---

# Context

用户明确批准累计上限100次、2元，替代待批准的51次、1元申请。运行器原固定27次上限须与新签名授权一致。

# Goal

仅更新运行器的授权ID与累计包络，保留固定24样例、模型身份、单次限额和失败停止；准备和断网验收通过后执行真实挑战。

# Non-goals

不清空历史、不自动重试、不修改生产资格或业务校验。子规格关闭不表示Q2-06真实质量通过。

# Acceptance criteria

- AC-1: 准备仍为24个预算内提示，授权合同与输出均为累计100次/2000000 micro-CNY，单次8000/512保持。
- AC-2: 未授权零调用、未知失败保守结算、身份不符停止、历史续跑不重复的离线回归通过，授权事实明确记录。

# Risks

累计上限不能误作新增次数；账本保留原27次和98766 micro-CNY。质量失败仍须独立审查。

# Verification plan

## Verification cases

- AC-1 => M09-G07-PREPARE-01
- AC-2 => M09-G07-RUNNER-01, M08-DOCS-01

## Gates

- api-tests => AC-1, AC-2
- harness-integrity => AC-2
