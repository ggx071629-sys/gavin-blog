---
id: archive-20260912-assistant-lexical-recall
level: L2
summary: 修复问答检索的中英文自然问句词法召回
load_when:
  - task:20260912-assistant-lexical-recall
author: Codex
task_id: 20260912-assistant-lexical-recall
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录 FTS 词法投影、匹配回退顺序，以及既有 generation 必须重建才能获得中文子串召回。
evidence_sha256: b3f94f4b2c95927e241b72697d78f6c132509834086d953273b69972fca06978
state_history:
---

# 20260912-assistant-lexical-recall

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让中文子串、中文自然问句与英文自然问句在词法分支可召回，同时保持精确术语、代码标识符和旧 generation 的既有行为；并明确既有索引的重建路径，使修复不只在新建索引上成立。

## Acceptance criteria

- AC-1: 中文子串、中文自然问句、英文自然问句、代码标识符与精确术语都能通过真实 FTS5 表召回；端到端检索的候选来源包含词法分支。
- AC-2: 无关问题不被宽松回退召回，未重建的 generation 仍保持原来的召回范围，且不会被当作已经支持中文子串。
- AC-3: 逐字词法投影与既有原文投影都通过完整性审计，FTS 定向修复使用同一投影。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-lexical-recall.json](../../verification/evidence/20260912-assistant-lexical-recall.json)

SHA-256: `b3f94f4b2c95927e241b72697d78f6c132509834086d953273b69972fca06978`

Closed at 2026-09-12T05:48:43.960248+00:00.
