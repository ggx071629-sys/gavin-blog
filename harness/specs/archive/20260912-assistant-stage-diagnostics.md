---
id: archive-20260912-assistant-stage-diagnostics
level: L2
summary: Q3-04 关联无正文阶段诊断与实际调用耗时
load_when:
  - task:20260912-assistant-stage-diagnostics
task_id: 20260912-assistant-stage-diagnostics
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 明确阶段耗时、候选数量、版本与费用关联记录的位置和局限。
evidence_sha256: d5d7f3a9daca9970347da1a803db01d71d2ef0bcdf7d882c328223160f53646a
state_history:
---

# 20260912-assistant-stage-diagnostics

Deterministic compressed record. The original active spec remains in Git history.

## Goal

关联同一 turn 的检索、生成、校验、重试和终态无正文诊断，持久化已观察调用耗时。

## Acceptance criteria

- AC-1: 检索候选/过滤/选中数量、代次与策略版本、各阶段及重试和终态可按 turn 关联，记录不含问答、引文、标题或异常正文。
- AC-2: Chat/query Embedding 成功及失败耗时被记录；query 发送态费用事件不遗漏，重放结算不重复；未知仍保守结算。
- AC-3: 文档区分持久化事件和结构化日志、已观察耗时与未测生产 P95。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-stage-diagnostics.json](../../verification/evidence/20260912-assistant-stage-diagnostics.json)

SHA-256: `d5d7f3a9daca9970347da1a803db01d71d2ef0bcdf7d882c328223160f53646a`

Closed at 2026-09-12T13:33:48.367816+00:00.
