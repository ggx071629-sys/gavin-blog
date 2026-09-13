---
id: archive-20260912-assistant-question-focus
level: L2
summary: 让当前问题在提示末尾明确回答范围和语言
load_when:
  - task:20260912-assistant-question-focus
author: Codex
task_id: 20260912-assistant-question-focus
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录提示关注当前问题和有限英文通知关系的边界。
evidence_sha256: 75eef2daa2852d584ee8fb699a25c7dca48322624d9d6ef424365053766ae5dc
state_history:
---

# 20260912-assistant-question-focus

Deterministic compressed record. The original active spec remains in Git history.

## Goal

历史和证据之后呈现当前问题，明确不回答无关资料；在完整邮件通知关系保持一致时允许有限英文表达，仍要求原文quote。

## Acceptance criteria

- AC-1: 当前问题最后呈现，资料和历史仍为隔离的不可信数据，24个提示在原预算内；原有历史裁剪检查通过。
- AC-2: 有据邮件通知英文关系可用，错误协议、主体、条件、否定仍拒绝；事实、数值及讨论保护通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-question-focus.json](../../verification/evidence/20260912-assistant-question-focus.json)

SHA-256: `75eef2daa2852d584ee8fb699a25c7dca48322624d9d6ef424365053766ae5dc`

Closed at 2026-09-12T11:57:50.100210+00:00.
