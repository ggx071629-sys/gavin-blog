---
id: archive-20260913-assistant-fact-alignment
level: L2
summary: Q5起句语言和结构化来源事实对齐修复及保留反例
load_when:
  - task:20260913-assistant-fact-alignment
author: Codex
task_id: 20260913-assistant-fact-alignment
status: compressed
documentation_impact: required
documentation_targets:
  - plan-build/assistant-gap-closure/evaluation/Q5-EVALUATION.md
documentation_reason: 记录有限格式对齐与语言约束边界，不将真实质量或人工项目提前通过。
evidence_sha256: 3d721bd0cc459ce9181821a9865040fcbc6ad1d98a7761208b3bf150985b02b3
state_history:
---

# 20260913-assistant-fact-alignment

Deterministic compressed record. The original active spec remains in Git history.

## Goal

按完整事实对齐映射、表格单行与简历展示包装；明确正文起句与标题区别、英语问句语言。先离线保留数字、否定、主体、限定与撤回反例，再在既有授权内独立记录真实回归和新题结果。

## Acceptance criteria

- AC-1: 完整映射合句及表格/简历展示等价通过，数字、主体、否定、限定与撤回错配继续拒绝，原始引文仍精确。
- AC-2: 正文起句提示区分标题、语言识别覆盖According to英文问题，事实引用与既有安全回归保留。

## Result

Verified and closed by the harness close command.

## Evidence

[20260913-assistant-fact-alignment.json](../../verification/evidence/20260913-assistant-fact-alignment.json)

SHA-256: `3d721bd0cc459ce9181821a9865040fcbc6ad1d98a7761208b3bf150985b02b3`

Closed at 2026-09-12T16:54:22.148837+00:00.
