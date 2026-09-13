---
id: archive-20260912-assistant-expanded-input
level: L2
summary: 按最新指令扩至32000输入并保持200次2元累计边界
load_when:
  - task:20260912-assistant-expanded-input
author: Codex
task_id: 20260912-assistant-expanded-input
status: compressed
documentation_impact: required
documentation_targets:
  - plan-build/assistant-gap-closure/evaluation/Q5-EVALUATION.md
documentation_reason: 记录32000配置、8000对照及累计预算不变，独立评测和生产资格不升级。
evidence_sha256: bffd662d9e26f7249317cd4660af8dfc760d7a1f5c96051d1930a577f6bdb258
state_history:
---

# 20260912-assistant-expanded-input

Deterministic compressed record. The original active spec remains in Git history.

## Goal

当前本地配置与固定题集运行器输入上限扩大到32000，输出512和上下文配置保持，累计200次/2元；签名账本继承历史，按实际完整提示估算预留费用。

## Acceptance criteria

- AC-1: 32000预算可容纳代表性多个完整来源，超过输入或上下文仍不准入；原8000边界测试继续有效。
- AC-2: 运行器拒绝不匹配的输入配置/旧授权，累计200次2元不重置，未知结果保守结算，prepare不发送Chat。
- AC-3: 8000与32000结果分开保存，成本/正确性/缺证据与未验证事项清楚记录；未通过的Q5和Q6不标为完成。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-expanded-input.json](../../verification/evidence/20260912-assistant-expanded-input.json)

SHA-256: `bffd662d9e26f7249317cd4660af8dfc760d7a1f5c96051d1930a577f6bdb258`

Closed at 2026-09-12T15:53:39.667464+00:00.
