---
id: spec-20260912-assistant-expanded-input
level: L1
summary: 按最新指令扩至32000输入并保持200次2元累计边界
load_when:
  - task:20260912-assistant-expanded-input
author: Codex
task_id: 20260912-assistant-expanded-input
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - plan-build/assistant-gap-closure/evaluation/Q5-EVALUATION.md
documentation_reason: 记录32000配置、8000对照及累计预算不变，独立评测和生产资格不升级。
state_history:
---

# Context

用户最新明确允许扩张输入限额，覆盖此前保留8000的决定；8000对照运行与已验收的紧凑提示保留。新增文章并不要求自动增加输入，当前扩大是为已检索的完整片段提供空间。

# Goal

当前本地配置与固定题集运行器输入上限扩大到32000，输出512和上下文配置保持，累计200次/2元；签名账本继承历史，按实际完整提示估算预留费用。

# Non-goals

不更换供应商、不降低估算或事实校验、不修改题集原始期望、不签发上线资格，不承诺32000容纳任意全站内容。

# Acceptance criteria

- AC-1: 32000预算可容纳代表性多个完整来源，超过输入或上下文仍不准入；原8000边界测试继续有效。
- AC-2: 运行器拒绝不匹配的输入配置/旧授权，累计200次2元不重置，未知结果保守结算，prepare不发送Chat。
- AC-3: 8000与32000结果分开保存，成本/正确性/缺证据与未验证事项清楚记录；未通过的Q5和Q6不标为完成。

# Risks

输入更多会增加费用和延迟，也可能引入不相关证据；新结果只用于回归诊断，不能视作独立评估。

# Verification plan

## Verification cases

- AC-1 => M09-EXPANDED-INPUT-01, M09-CURRENT-PROMPT-01
- AC-2 => M09-CURRENT-BUDGET-01
- AC-3 => M08-DOCS-01

## Gates

- api-tests => AC-1, AC-2
- harness-integrity => AC-3
