---
id: archive-20260912-assistant-quantity-binding
level: L2
summary: 在完整陈述中规范化中文数值和明确单位换算
load_when:
  - task:20260912-assistant-quantity-binding
author: Codex
task_id: 20260912-assistant-quantity-binding
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明数值原位规范化、已支持单位和百分比范围，以及未支持的歧义单位/算术。
evidence_sha256: ba6b3fdf0546a112fcb1be17fe4614a207334d7feef650e33855b107beaf1d6a
state_history:
---

# 20260912-assistant-quantity-binding

Deterministic compressed record. The original active spec remains in Git history.

## Goal

中文数词、阿拉伯数值及确定时间单位可等价匹配；对象、属性、时间、范围/上下限和分母错配被拒绝。

## Acceptance criteria

- AC-1: 数值在原陈述位置规范化，中文数词、60秒=1分钟、小数/毫秒、明确范围和百分比等正例可通过；对象交换、时间/上下限反转、数值和分母变化被拒绝。
- AC-2: 既有数字、事实、自述和引用支持保护继续通过；零分母不得作为有效等价换算，文档保留歧义/未知单位的限制。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-quantity-binding.json](../../verification/evidence/20260912-assistant-quantity-binding.json)

SHA-256: `ba6b3fdf0546a112fcb1be17fe4614a207334d7feef650e33855b107beaf1d6a`

Closed at 2026-09-12T06:31:51.626603+00:00.
