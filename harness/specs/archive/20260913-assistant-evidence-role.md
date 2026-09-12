---
id: archive-20260913-assistant-evidence-role
level: L2
summary: Q5-04从当前已发布字段区分文章元数据和正文证据
load_when:
  - task:20260913-assistant-evidence-role
author: Codex
task_id: 20260913-assistant-evidence-role
status: compressed
documentation_impact: required
documentation_targets:
  - plan-build/assistant-gap-closure/evaluation/Q5-EVALUATION.md
documentation_reason: 记录正文归属的确定性计算与仍未验证的回答范围。
evidence_sha256: 01bcbacd214fd8a960514894db50ec8d511edc1881e8f41cbb8b1fdfa94b3214
state_history:
---

# 20260913-assistant-evidence-role

Deterministic compressed record. The original active spec remains in Git history.

## Goal

从当前已发布ArticleRevision内容与投影元数据判定片段是metadata、body或unknown，并仅作为内部提示描述符发送；歧义不猜测。

## Acceptance criteria

- AC-1: 仅当前有效公开文章字段可提供片段角色，元数据和正文重叠或混合时保持unknown，不根据标题关键词或片段排名猜测。
- AC-2: 初次hydrate和descriptor重建均计算角色；提示保留原始正文，公开引用/来源不增加字段，撤销/版本规则继续拒绝旧证据。
- AC-3: 在原200次/2元授权内对E01和对照题复测，失败和适用范围保持记录，未验证任务不提前归档。

## Result

Verified and closed by the harness close command.

## Evidence

[20260913-assistant-evidence-role.json](../../verification/evidence/20260913-assistant-evidence-role.json)

SHA-256: `01bcbacd214fd8a960514894db50ec8d511edc1881e8f41cbb8b1fdfa94b3214`

Closed at 2026-09-12T16:23:55.376591+00:00.
