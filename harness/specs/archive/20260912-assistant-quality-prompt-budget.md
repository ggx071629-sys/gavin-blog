---
id: archive-20260912-assistant-quality-prompt-budget
level: L2
summary: Q5 首批失败后的提示预算修复和累计200次授权衔接
load_when:
  - task:20260912-assistant-quality-prompt-budget
author: Codex
task_id: 20260912-assistant-quality-prompt-budget
status: compressed
documentation_impact: required
documentation_targets:
  - plan-build/assistant-gap-closure/evaluation/Q5-EVALUATION.md
documentation_reason: 保留首次真实评测失败，记录提示修复、累计额度及复测非独立限制。
evidence_sha256: 7b32f95092e5fa2f9f0fcfba3d1897784ce87ae5c6ea95e8653190f835d77cac
state_history:
---

# 20260912-assistant-quality-prompt-budget

Deterministic compressed record. The original active spec remains in Git history.

## Goal

压缩重复系统指令，为完整原始证据释放空间；引导模型使用完整原文事实条款，保留校验器、注入、版本和预算保护。衔接同一本地累计账本的新授权，不重置历史。

## Acceptance criteria

- AC-1: 紧凑提示可容纳代表性中文事实片段；用户了解每次只发送相关片段后确认保留输入限额，故继续8000输入上限，并保持完整正文、注入隔离及过小上下文拒绝。
- AC-2: 运行器使用累计200次/2元授权，历史调用费用不归零，逐次按实际完整提示的保守输入估算和输出上限预留；prepare不发起Chat，未知结果仍保守结算后停止。
- AC-3: 现有成对事实、数值、否定、归因和恶意输出检查保持通过，不为本题集放宽校验器；管理试问恢复只返回其既有契约字段，排除公开会话新增的feedback字段，旧失败码断言与当前已实现行为一致。
- AC-4: 首次失败与复测分开记录，人工标注/设备、精确模型版本与实际完整E2E未验证不归档为通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-quality-prompt-budget.json](../../verification/evidence/20260912-assistant-quality-prompt-budget.json)

SHA-256: `7b32f95092e5fa2f9f0fcfba3d1897784ce87ae5c6ea95e8653190f835d77cac`

Closed at 2026-09-12T15:48:14.831580+00:00.
