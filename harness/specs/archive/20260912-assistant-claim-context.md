---
id: archive-20260912-assistant-claim-context
level: L2
summary: 校验普通陈述并保留否定、时间、主体和冲突语境
load_when:
  - task:20260912-assistant-claim-context
author: Codex
task_id: 20260912-assistant-claim-context
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明有限事实支持、相邻撤回与同主体冲突规则、问题相关性检查及未覆盖语义。
evidence_sha256: 84794c7ce6ed720573505f3506629993460678e7ecbfa1e487ec24c3bbe71870
state_history:
---

# 20260912-assistant-claim-context

Deterministic compressed record. The original active spec remains in Git history.

## Goal

普通陈述也必须由当前引用语境支持，保留主体、否定、时间和范围；相邻撤回与同主体同属性冲突不得被选句掩盖。把当前问题传入校验，拒绝明确的主题错答并允许有界缺口说明。

## Acceptance criteria

- AC-1: 合成正反对照拒绝普通事实发明、否定反转、主体替换、时间替换及范围扩张；继续支持原有明确 About 自述、普通技术改写、已支持关系和真实引文校验。
- AC-2: 同句与相邻跨句撤回被保留；同主体同属性的明确来源冲突不能单方断言，披露冲突须引用双方；不同主体不误判为冲突。
- AC-3: 当前问题进入校验；明确数据库/许可证等主题错答被拒，材料确无对应主题时允许有界缺口说明；未知语义范围由文档明确，SSE 与正文/支持原文清理保护继续有效。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-claim-context.json](../../verification/evidence/20260912-assistant-claim-context.json)

SHA-256: `84794c7ce6ed720573505f3506629993460678e7ecbfa1e487ec24c3bbe71870`

Closed at 2026-09-12T06:25:22.553221+00:00.
