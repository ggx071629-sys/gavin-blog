---
id: archive-20260912-assistant-g07-authorized-envelope
level: L2
summary: 绑定用户批准的G07累计100次2元授权
load_when:
  - task:20260912-assistant-g07-authorized-envelope
author: Codex
task_id: 20260912-assistant-g07-authorized-envelope
status: compressed
documentation_impact: required
documentation_targets:
  - plan-build/assistant-gap-closure/evaluation/G07-EXECUTION.md
documentation_reason: 保存用户明确批准的累计上限和既有账本历史保留要求。
evidence_sha256: ca3c23de0c61298e91571257575e8c608e67c5f641434b0b972c7216d1782335
state_history:
---

# 20260912-assistant-g07-authorized-envelope

Deterministic compressed record. The original active spec remains in Git history.

## Goal

仅更新运行器的授权ID与累计包络，保留固定24样例、模型身份、单次限额和失败停止；准备和断网验收通过后执行真实挑战。

## Acceptance criteria

- AC-1: 准备仍为24个预算内提示，授权合同与输出均为累计100次/2000000 micro-CNY，单次8000/512保持。
- AC-2: 未授权零调用、未知失败保守结算、身份不符停止、历史续跑不重复的离线回归通过，授权事实明确记录。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-g07-authorized-envelope.json](../../verification/evidence/20260912-assistant-g07-authorized-envelope.json)

SHA-256: `ca3c23de0c61298e91571257575e8c608e67c5f641434b0b972c7216d1782335`

Closed at 2026-09-12T11:47:27.115634+00:00.
