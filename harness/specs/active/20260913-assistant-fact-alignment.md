---
id: spec-20260913-assistant-fact-alignment
level: L1
summary: Q5起句语言和结构化来源事实对齐修复及保留反例
load_when:
  - task:20260913-assistant-fact-alignment
author: Codex
task_id: 20260913-assistant-fact-alignment
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - plan-build/assistant-gap-closure/evaluation/Q5-EVALUATION.md
documentation_reason: 记录有限格式对齐与语言约束边界，不将真实质量或人工项目提前通过。
state_history:
---

# Context

Q5已见题中正文起句混为标题，英文According to问句未命中语言规则；映射合句、Markdown表格和PDF换行造成完整事实误拒，部分简历回答确有截句。历史144次1.252998元保留。

# Goal

按完整事实对齐映射、表格单行与简历展示包装；明确正文起句与标题区别、英语问句语言。先离线保留数字、否定、主体、限定与撤回反例，再在既有授权内独立记录真实回归和新题结果。

# Non-goals

不实现任意语义判官、不新增门槛或重试、不扩充公开语料，不恢复Q6。人工题集、实体手机、读屏无实际执行不记通过。

# Acceptance criteria

- AC-1: 完整映射合句及表格/简历展示等价通过，数字、主体、否定、限定与撤回错配继续拒绝，原始引文仍精确。
- AC-2: 正文起句提示区分标题、语言识别覆盖According to英文问题，事实引用与既有安全回归保留。

# Risks

格式规范化可能隐藏限定和改变代码；仅有限完整结构等价，真实语言遵循性和正确性另行测量。

# Verification plan

## Verification cases

- AC-1 => M09-FACT-ALIGNMENT-01, M09-CODE-PRESENTATION-01, M09-GROUNDING-01, M09-CONTEXT-CROSS-01
- AC-2 => M09-FACT-ALIGNMENT-02, M09-GROUNDING-02, M08-DOCS-01

## Gates

- api-tests => AC-1, AC-2
- harness-integrity => AC-2
