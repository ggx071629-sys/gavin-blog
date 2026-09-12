---
id: spec-20260912-assistant-quality-prompt-budget
level: L1
summary: Q5 首批失败后的提示预算修复和累计200次授权衔接
load_when:
  - task:20260912-assistant-quality-prompt-budget
author: Codex
task_id: 20260912-assistant-quality-prompt-budget
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - plan-build/assistant-gap-closure/evaluation/Q5-EVALUATION.md
documentation_reason: 保留首次真实评测失败，记录提示修复、累计额度及复测非独立限制。
state_history:
---

# Context

首次固定题集实际调用14次均未被校验器接受；多数问题的必要正文因保守8000输入预算被排除，部分正确改写不在有限校验器支持范围。用户已明确批准固定公开语料发送给DeepSeek，并将累计调用上限从100扩至200、2元不变。

# Goal

压缩重复系统指令，为完整原始证据释放空间；引导模型使用完整原文事实条款，保留校验器、注入、版本和预算保护。衔接同一本地累计账本的新授权，不重置历史。

# Non-goals

不降低估算器、事实校验或安全门槛，不引入语义模型裁判，不改变正文切块，不保证任意题目通过，不签发Q6生产资格。

# Acceptance criteria

- AC-1: 紧凑提示可容纳代表性中文事实片段；按用户追加指令，当前评测取消人为8000输入上限，使用已配置上下文扣除输出预留，仍保持完整正文、注入隔离及过小上下文拒绝。
- AC-2: 运行器使用累计200次/2元授权，历史调用费用不归零，逐次按实际完整提示的保守输入估算和输出上限预留；prepare不发起Chat，未知结果仍保守结算后停止。
- AC-3: 现有成对事实、数值、否定、归因和恶意输出检查保持通过，不为本题集放宽校验器；管理试问恢复只返回其既有契约字段，排除公开会话新增的feedback字段，旧失败码断言与当前已实现行为一致。
- AC-4: 首次失败与复测分开记录，人工标注/设备、精确模型版本与实际完整E2E未验证不归档为通过。

# Risks

压缩提示可能降低模型遵循率，必须真实有界复测；全部输入已被观察，后续结果只能是回归诊断，不能冒充新的独立评估。剩余费用可能先于200次耗尽，两者都强制执行。

# Verification plan

## Verification cases

- AC-1 => M09-CURRENT-PROMPT-01
- AC-2 => M09-CURRENT-BUDGET-01, M10-TOTAL-BUDGET-01
- AC-3 => M09-GROUNDING-01, M09-GROUNDING-02, M09-GROUNDING-03
- AC-4 => M08-DOCS-01

## Gates

- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-4
