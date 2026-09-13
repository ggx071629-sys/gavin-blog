---
id: archive-20260912-about-draft-preserve
level: L2
summary: 关于页自动保存不再清空尚未提交的领域标签输入
load_when:
  - task:20260912-about-draft-preserve
author: Codex
task_id: 20260912-about-draft-preserve
status: compressed
documentation_impact: none
documentation_reason: 只修复关于页编辑器内部草稿状态缺陷并新增回归，未改变关于页字段契约或公开内容，README 无需同步。
evidence_sha256: 5b6300da3619b363b5e13cf36e31e0b00d244be6f3c6b64b368daae59b6b8c8a
state_history:
---

# 20260912-about-draft-preserve

Deterministic compressed record. The original active spec remains in Git history.

## Goal

区分服务器工作副本刷新与自动保存回声：无关字段保存完成后保留尚未提交的标签输入，提交该标签后正常清空；领域增删排序时临时草稿仍跟随对应领域。

## Acceptance criteria

- AC-1: 无关字段自动保存回声后，尚未提交的标签输入仍保留，提交后可正常清空。
- AC-2: 领域增删排序时临时草稿跟随对应领域，既有增删上限、预览与发布语义不变。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-about-draft-preserve.json](../../verification/evidence/20260912-about-draft-preserve.json)

SHA-256: `5b6300da3619b363b5e13cf36e31e0b00d244be6f3c6b64b368daae59b6b8c8a`

Closed at 2026-09-12T04:50:34.352523+00:00.
