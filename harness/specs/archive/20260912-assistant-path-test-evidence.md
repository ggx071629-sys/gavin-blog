---
id: archive-20260912-assistant-path-test-evidence
level: L2
summary: 修复技术路径回归的事实支持前提并保留无据反例
load_when:
  - task:20260912-assistant-path-test-evidence
author: Codex
task_id: 20260912-assistant-path-test-evidence
status: compressed
documentation_impact: none
documentation_reason: 只修复既有测试证据前提，不修改产品行为、契约或持久化。
evidence_sha256: dbd2bf6aba1a9cedb9c45aa3d18b556c42551b79ef348762c8267bdc2aec53af
state_history:
---

# 20260912-assistant-path-test-evidence

Deterministic compressed record. The original active spec remains in Git history.

## Goal

先断言无依据路径被拒绝，再以真实包含该技术路径的证据验证不会被当成来源地址替换。

## Acceptance criteria

- AC-1: 8种技术路径有证据时保持原样及引用，无对应事实来源时仍grounding；提示来源地址及历史边界继续断言。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-path-test-evidence.json](../../verification/evidence/20260912-assistant-path-test-evidence.json)

SHA-256: `dbd2bf6aba1a9cedb9c45aa3d18b556c42551b79ef348762c8267bdc2aec53af`

Closed at 2026-09-12T12:16:19.772833+00:00.
