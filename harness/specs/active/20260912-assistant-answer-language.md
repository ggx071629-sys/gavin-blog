---
id: spec-20260912-assistant-answer-language
level: L1
summary: 明确英文问句的回答语言并保留教程方式转述
load_when:
  - task:20260912-assistant-answer-language
author: Codex
task_id: 20260912-assistant-answer-language
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录有限英文问句识别、引用原文语言与教程方式转述边界。
state_history:
---

# Context

当前问题末置后6对照4通过，无空答；一条中文“方式是”转述误拒，英文问句仍回答中文。

# Goal

对明确英文问句增加固定可信英文语言提示；正常教程“方式是”保留完整内容关系。其他语言继续遵循原有按问题语言回答政策。

# Non-goals

不让用户输入拼接成系统指令；不删除否定、条件或未知事实；不承诺通用语言识别或实际质量通过。

# Acceptance criteria

- AC-1: 明确英文问句得到固定English语言约束、quote保持原文；中文及未知语言不被强制英语，24提示预算与历史安全通过。
- AC-2: 真实“方式是”完整转述通过，改变事实、否定及限定仍拒绝；数值、语境和讨论边界回归通过。

# Risks

识别只覆盖明确英语疑问句开头，未知语言不猜测；模型语言遵循性必须真实复验。

# Verification plan

## Verification cases

- AC-1 => M09-G07-PREPARE-01, M09-DEFENSE-01
- AC-2 => M09-G07-REPLAY-01, M09-CLAIM-CONTEXT-01, M09-QUANTITY-BINDING-01, M09-DISCUSSION-CONTEXT-01, M09-G07-RUNNER-01, M08-DOCS-01

## Gates

- api-tests => AC-1, AC-2
- harness-integrity => AC-2
