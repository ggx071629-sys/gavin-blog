---
id: spec-20260913-assistant-q5-review-materials
level: L1
summary: 冻结未调试题集并允许未知调用期间只读准备和记录缺失测量
load_when:
  - task:20260913-assistant-q5-review-materials
author: Codex
task_id: 20260913-assistant-q5-review-materials
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - plan-build/assistant-gap-closure/evaluation/Q5-EVALUATION.md
documentation_reason: 记录新题隔离、人工验收步骤、未知调用和未验证链路的恢复边界。
state_history:
---

# Context

真实回归首题连接错误，账本已有未知调用并阻止外发。现有prepare虽不外发也被账本阻止，运行器没有新题文件选项，异常未记录耗时。已有题目的输出均已参与调试。

# Goal

冻结同一已授权来源上的新题，提供固定文件选择与只读准备；未知调用继续阻止run且不重试、不恢复账本。补充未来异常的耗时记录和独立人工/手机/读屏/完整链路验收材料。

# Non-goals

不发送新的付费调用、不清除未知调用、不新增门槛、不恢复Q6，不把材料或模拟验收当作人工或真实模型通过。

# Acceptance criteria

- AC-1: 新题文件固定来源和期望、与已见回归分开；prepare在未知调用时仍只读，run仍在发送前拒绝。
- AC-2: 异常耗时只记录实际测得的值，不为旧异常补造数值；预算、原失败和未验证项保留。

# Risks

新题由同一助手选择，未参与输出调试但不是独立人工抽样；未知调用不得被新文件选择绕过。

# Verification plan

## Verification cases

- AC-1 => M09-Q5-REVIEW-01, M09-CURRENT-DATASET-01, M09-CURRENT-BUDGET-01
- AC-2 => M09-Q5-REVIEW-02, M08-DOCS-01

## Gates

- api-tests => AC-1, AC-2
- harness-integrity => AC-2
