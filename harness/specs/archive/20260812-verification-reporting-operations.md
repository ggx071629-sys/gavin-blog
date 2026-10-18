---
id: archive-20260812-verification-reporting-operations
level: L2
summary: 结构化采集验证结果并提供只读 task status 与批量关闭预检
load_when:
  - task:20260812-verification-reporting-operations
author: Codex
task_id: 20260812-verification-reporting-operations
status: compressed
state_history:
---

# 20260812-verification-reporting-operations

Deterministic compressed record. The original active spec remains in Git history.

## Goal

为 gate 和 task evidence 增加紧凑、结构化的测试数量、总耗时和失败摘要，并提供不改变仓库的 `status` 与 `close-all --dry-run`，让关闭前状态和阻断可机器读取、可人工复核。

## Acceptance criteria

- AC-1: gate 结果记录 exit code、耗时与可用的 passed／failed／skipped test counts；Pytest、Vitest、Playwright 及组合 release 输出不会把 test files、重复标题或非汇总行误计为测试。
- AC-2: 失败 gate 记录稳定 failure kind 与单条有限摘要，超时、可执行文件缺失、非零退出和隔离失败可区分；evidence 不保存完整日志或临时绝对路径。
- AC-3: task evidence 顶层汇总 checks 总数/通过/失败、总耗时、测试数量与失败检查列表；汇总可由 checks 重算且 close 校验一致性，手工篡改或漂移使 evidence 无效。
- AC-4: `status` 无参数时按 task ID 列出当前 active/verified/frozen，指定 task 时还能报告 compressed 或 missing；`--json` 输出稳定机器对象，且 frozen 状态不触发 task verify/evidence 校验。
- AC-5: `close-all --dry-run` 与真实关闭共享 active 排序、frozen skip、evidence、目标 archive/event 冲突和 Harness 前置检查；只读预检成功或失败均不写 archive、event、evidence、索引或 spec。
- AC-6: status 与 dry-run 使用明确退出码：可执行且状态可读返回 0，指定 missing task 或任何 active 关闭阻断返回 1；没有 active spec 时 dry-run 返回 0。
- AC-7: 无 task ID 全局 verify、task verify、单任务 close、真实 close-all、freeze/resume、隔离清理与历史 compressed evidence 保持兼容。
- AC-8: verification policy、verify workflow 与生命周期说明结构化 evidence、status 和 dry-run 的用途与边界。

## Result

Verified and closed by the harness close command.

## Evidence

[20260812-verification-reporting-operations.json](../../verification/evidence/20260812-verification-reporting-operations.json)

Closed at 2026-08-12T03:55:06.970513+00:00.
