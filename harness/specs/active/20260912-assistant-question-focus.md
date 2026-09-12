---
id: spec-20260912-assistant-question-focus
level: L1
summary: 让当前问题在提示末尾明确回答范围和语言
load_when:
  - task:20260912-assistant-question-focus
author: Codex
task_id: 20260912-assistant-question-focus
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录提示关注当前问题和有限英文通知关系的边界。
state_history:
---

# Context

英文对照单次复验不再空答但改用中文、添加无关风险解释，仍失败。当前问题在用户消息最前，长资料结束后没有明确回到问题。

# Goal

历史和证据之后呈现当前问题，明确不回答无关资料；在完整邮件通知关系保持一致时允许有限英文表达，仍要求原文quote。

# Non-goals

不赋予用户或资料额外权限；不承诺通用语义/翻译；不自动执行模型或把原失败改写成成功。

# Acceptance criteria

- AC-1: 当前问题最后呈现，资料和历史仍为隔离的不可信数据，24个提示在原预算内；原有历史裁剪检查通过。
- AC-2: 有据邮件通知英文关系可用，错误协议、主体、条件、否定仍拒绝；事实、数值及讨论保护通过。

# Risks

提示顺序的实际效果须真实复验；翻译只接受完整的有限关系，未知英文继续拒绝。

# Verification plan

## Verification cases

- AC-1 => M09-G07-PREPARE-01, M09-DEFENSE-01
- AC-2 => M09-G07-REPLAY-01, M09-CLAIM-CONTEXT-01, M09-QUANTITY-BINDING-01, M09-DISCUSSION-CONTEXT-01, M09-G07-RUNNER-01, M08-DOCS-01

## Gates

- api-tests => AC-1, AC-2
- harness-integrity => AC-2
