---
id: spec-20260913-assistant-answer-instructions
level: L1
summary: Q5-04当前内容误读和schema数据混淆的有限修复
load_when:
  - task:20260913-assistant-answer-instructions
author: Codex
task_id: 20260913-assistant-answer-instructions
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - plan-build/assistant-gap-closure/evaluation/Q5-EVALUATION.md
documentation_reason: 记录当前失败修复边界与真实复测，不把中间报告算收尾。
state_history:
---

# Context

Q5-04扩大输入后期望支持13/13进入提示，但E01把摘要当正文、E14复制schema关键字为额外数据字段；普通改写仍被有限grounding拒绝。按现有计划继续修复；Q6取消，不增加部署待办。

# Goal

明确投影中文章标题/摘要/分类与正文的区别，以及JSON数据实例和schema约束的区别；引导模型保留完整原文事实，校验器和预算约束保持。

# Non-goals

不放宽额外字段、逐块引用或事实校验，不增加模型裁判，不修改公开内容、来源版本或题集原始期望，不保证任意语义改写支持。

# Acceptance criteria

- AC-1: 结构示例仅有允许的数据字段，schema关键词不能成为结果字段；超预算和不完整JSON仍拒绝。
- AC-2: 提示说明文章投影的元数据与正文区别，原文事实和技术映射不增加主张；现有注入、来源及完整句规则继续通过。
- AC-3: 同一固定题集在200次2元累计授权内复测；原始失败不覆盖，Q5未验证范围继续留在计划。

# Risks

提示不能保证模型遵循；需要真实复测。不得因示例而接受伪造证据或以schema修复猜测被截断的输出。

# Verification plan

## Verification cases

- AC-1 => M09-ANSWER-INSTRUCTIONS-01, M09-GROUNDING-02
- AC-2 => M09-CURRENT-PROMPT-01, M09-GROUNDING-01
- AC-3 => M09-CURRENT-BUDGET-01, M08-DOCS-01

## Gates

- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-3
