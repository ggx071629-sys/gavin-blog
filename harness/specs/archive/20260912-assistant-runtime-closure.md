---
id: archive-20260912-assistant-runtime-closure
level: L2
summary: Q3-06 核验并发费用故障并封闭无结果供应商边界
load_when:
  - task:20260912-assistant-runtime-closure
task_id: 20260912-assistant-runtime-closure
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 明确无可观察结果仍为未知，保守结算且不得格式重试。
evidence_sha256: e2f486f0cb924553d5dd289c92e7bc1d0e1fcc4761a13bdcf3bff58f1d7fdd77
state_history:
---

# 20260912-assistant-runtime-closure

Deterministic compressed record. The original active spec remains in Git history.

## Goal

完成阶段三当前版本的并发、费用与故障回归，并将没有 raw 或 parsed 结果的调用按未知处理。

## Acceptance criteria

- AC-1: 无可观察结果的供应商调用只发送一次，保守结算为 unknown，幂等读取不重发；已收到格式错误仍走既有有界纠正。
- AC-2: 慢检索不阻塞会话、心跳和清理；取消和停机保留容量与资源顺序；迟到结果不恢复正文或重复扣费。
- AC-3: 并发费用预留不超售，成功/未知计量和结算保持一次性，恢复仍保持费用锁。
- AC-4: 文档明确本地故障验证和真实模型/生产未测边界。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-runtime-closure.json](../../verification/evidence/20260912-assistant-runtime-closure.json)

SHA-256: `e2f486f0cb924553d5dd289c92e7bc1d0e1fcc4761a13bdcf3bff58f1d7fdd77`

Closed at 2026-09-12T14:20:44.990328+00:00.
