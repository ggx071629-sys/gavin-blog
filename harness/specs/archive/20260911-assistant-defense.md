---
id: archive-20260911-assistant-defense
level: L2
summary: 保留正常安全讨论并检查资料元数据与历史的指令边界
load_when:
  - task:20260911-assistant-defense
author: Codex
task_id: 20260911-assistant-defense
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明安全词汇讨论与执行请求的区别及资料字段、历史的有限规则防护。
evidence_sha256: d29a01fec519827ae39c5614e990ae15c73b706d4dc152e3460650bd58a09ab1
state_history:
---

# 20260911-assistant-defense

Deterministic compressed record. The original active spec remains in Git history.

## Goal

保留正常技术讨论，拒绝代表性直接执行/泄露请求；资料正文、标题、heading 和历史均不能授予行为权限。

## Acceptance criteria

- AC-1: 提示按权限、历史、逐块证据、夹带指令、错误前提/时间与格式分段；保留自然综合、自述、冲突、部分回答、片段限制与简历例外。
- AC-2: 正常提示词工程/安全教程不再单凭词汇拒绝；直接、改写、角色冒充、混合、英文、编码和 Unicode 代表攻击继续拒绝，既有凭据/工具/路径约束不回退。
- AC-3: hydrate 与恢复复核都扫描正文、标题和 heading；带明确执行指令的旧历史不进入模型，普通历史保持指代功能且不是证据；正常公开技术内容仍可回答。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-assistant-defense.json](../../verification/evidence/20260911-assistant-defense.json)

SHA-256: `d29a01fec519827ae39c5614e990ae15c73b706d4dc152e3460650bd58a09ab1`

Closed at 2026-09-11T15:02:57.420724+00:00.
