---
id: archive-20260912-assistant-answer-language
level: L2
summary: 明确英文问句的回答语言并保留教程方式转述
load_when:
  - task:20260912-assistant-answer-language
author: Codex
task_id: 20260912-assistant-answer-language
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录有限英文问句识别、引用原文语言与教程方式转述边界。
evidence_sha256: 7c13ccfebe5d1a8f0b88d226f539418f5879cd2abfe447320778ac59a79d62bb
state_history:
---

# 20260912-assistant-answer-language

Deterministic compressed record. The original active spec remains in Git history.

## Goal

对明确英文问句增加固定可信英文语言提示；正常教程“方式是”保留完整内容关系。其他语言继续遵循原有按问题语言回答政策。

## Acceptance criteria

- AC-1: 明确英文问句得到固定English语言约束、quote保持原文；中文及未知语言不被强制英语，24提示预算与历史安全通过。
- AC-2: 真实“方式是”完整转述通过，改变事实、否定及限定仍拒绝；数值、语境和讨论边界回归通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-answer-language.json](../../verification/evidence/20260912-assistant-answer-language.json)

SHA-256: `7c13ccfebe5d1a8f0b88d226f539418f5879cd2abfe447320778ac59a79d62bb`

Closed at 2026-09-12T12:02:22.122940+00:00.
