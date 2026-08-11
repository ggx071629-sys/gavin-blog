---
id: archive-20260811-harness-close-signal-integrity
level: L2
summary: 消除关闭流程的空 Evolution proposal，并保证压缩归档保留关键章节
load_when:
  - task:20260811-harness-close-signal-integrity
author: Codex
task_id: 20260811-harness-close-signal-integrity
status: compressed
---

# 20260811-harness-close-signal-integrity

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让确定性 close 只记录完成事件而不制造空 proposal，并在删除 active spec 前可靠提取和验证 H1/H2 关键章节，使新归档始终保留非空 Goal 与 Acceptance criteria。

## Acceptance criteria

1. `python -m tools.harness close <task_id>` 继续生成 archive、evidence、索引和 `spec.completed` event，但默认不生成同名 proposal。
2. `python -m tools.harness emit-event ...` 继续为显式、带 reason 的允许事件生成 proposal。
3. 压缩器精确支持 H1 或 H2 的 Goal 与 Acceptance criteria，不把 H3 或正文中的相似文本当作章节。
4. Goal 或 Acceptance criteria 缺失、仅空白时，close 在删除 active spec 前失败并回滚，不留下 archive、event、proposal 或错误 evidence。
5. SDD template 与 lifecycle guidance 明确规范章节结构和关闭前完整性要求。
6. 自动化测试覆盖 H1/H2、缺失/空章节、默认 close 无 proposal、显式 event 有 proposal及回滚语义。
7. Harness verify 与完整 `quality:release` 通过；关闭本 spec 时实际证明新行为不生成空 `spec.completed` proposal。

## Result

Verified and closed by the harness close command.

## Evidence

[20260811-harness-close-signal-integrity.json](../../verification/evidence/20260811-harness-close-signal-integrity.json)

Closed at 2026-08-11T11:42:57.659166+00:00.
