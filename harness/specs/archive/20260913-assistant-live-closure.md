---
id: archive-20260913-assistant-live-closure
level: L2
summary: 修复剩余回答表达并以同一签名预算跑通本地真实问答链路
load_when:
  - task:20260913-assistant-live-closure
author: Codex
task_id: 20260913-assistant-live-closure
status: compressed
documentation_impact: required
documentation_targets:
  - plan-build/assistant-gap-closure/evaluation/Q5-EVALUATION.md
documentation_reason: 记录本地真实调用计账边界与实际链路结果，不恢复取消范围。
evidence_sha256: 48d6c08648941a473125c808a3b57612cc892427ec90c3d629e673bbe960e2b4
state_history:
---

# 20260913-assistant-live-closure

Deterministic compressed record. The original active spec remains in Git history.

## Goal

本地真实调用逐次纳入同一签名账本，正常在线预算继续生效；针对原始引文、简历完整事实与语言失败进行必要修复，并真实运行问答、追问、换题和恢复。用户随后明确将累计上限扩充为250次4元，原176次1.922580元及历史保留。

## Acceptance criteria

- AC-1: 本地专用预算包装在每次实际请求前预留、已知响应结算、未知保守结算并阻止后续请求，取消不释放已发请求预算；生产及默认调用不受影响。
- AC-2: 回答提示鼓励精确连续引文与完整简历事实，映射、数字、否定、主体和限定反例保留；真实回归及页面结果如实记录。
- AC-3: 本地模型可选择服务端原文片段编号，由请求内映射恢复精确quote后仍执行原始校验；拒绝不存在或跨别名的编号，用户文本不能提供映射，不改公开API或会话schema。

## Result

Verified and closed by the harness close command.

## Evidence

[20260913-assistant-live-closure.json](../../verification/evidence/20260913-assistant-live-closure.json)

SHA-256: `48d6c08648941a473125c808a3b57612cc892427ec90c3d629e673bbe960e2b4`

Closed at 2026-09-12T19:07:47.950878+00:00.
