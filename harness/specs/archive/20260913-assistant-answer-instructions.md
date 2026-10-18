---
id: archive-20260913-assistant-answer-instructions
level: L2
summary: Q5-04当前内容误读和schema数据混淆的有限修复
load_when:
  - task:20260913-assistant-answer-instructions
author: Codex
task_id: 20260913-assistant-answer-instructions
status: compressed
documentation_impact: required
documentation_targets:
  - plan-build/assistant-gap-closure/evaluation/Q5-EVALUATION.md
documentation_reason: 记录当前失败修复边界与真实复测，不把中间报告算收尾。
evidence_sha256: cfc446d635f247b3e431884b6436e220240956d5b25b3cb1177d127e446cc414
state_history:
---

# 20260913-assistant-answer-instructions

Deterministic compressed record. The original active spec remains in Git history.

## Goal

明确投影中文章标题/摘要/分类与正文的区别，以及JSON数据实例和schema约束的区别；引导模型保留完整原文事实，校验器和预算约束保持。

## Acceptance criteria

- AC-1: 结构示例仅有允许的数据字段，schema关键词不能成为结果字段；超预算和不完整JSON仍拒绝。
- AC-2: 提示说明文章投影的元数据与正文区别，原文事实和技术映射不增加主张；现有注入、来源及完整句规则继续通过。
- AC-3: 同一固定题集在200次2元累计授权内复测；原始失败不覆盖，Q5未验证范围继续留在计划。

## Result

Verified and closed by the harness close command.

## Evidence

[20260913-assistant-answer-instructions.json](../../verification/evidence/20260913-assistant-answer-instructions.json)

SHA-256: `cfc446d635f247b3e431884b6436e220240956d5b25b3cb1177d127e446cc414`

Closed at 2026-09-12T16:12:50.785966+00:00.
