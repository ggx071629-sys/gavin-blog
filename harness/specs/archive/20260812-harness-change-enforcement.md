---
id: archive-20260812-harness-change-enforcement
level: L2
summary: 建立基于 Git diff 的 Harness 任务覆盖门禁并统一可重复执行入口
load_when:
  - task:20260812-harness-change-enforcement
author: Codex
task_id: 20260812-harness-change-enforcement
status: compressed
documentation_impact: required
documentation_targets:
  - README.md
  - harness/docs/operations/release-readiness.md
documentation_reason: 新增变更覆盖门禁和发布入口需要成为开发者与发布流程的长期操作契约
state_history:
---

# 20260812-harness-change-enforcement

Deterministic compressed record. The original active spec remains in Git history.

## Goal

建立可测试的 Git diff 任务覆盖检查：风险变更必须在同一变更范围内包含当前 schema 的任务归档和有效 evidence；统一公开命令入口，并为未来 required status check 提供无平台绑定的执行接口。

## Acceptance criteria

- AC-1: `python -m tools.harness change-check --base <ref> [--head <ref>]` 能确定性识别配置中的风险路径；存在风险变更但没有同一 diff 内的新任务归档与 schema v2 passed evidence 时返回失败。
- AC-2: 合格任务证据必须属于同一 task、来源提交位于 base 之后且可从 head 到达；伪造旧任务、旧提交或 schema v1 evidence 不能通过。
- AC-3: 纯文档或配置声明的低风险变更明确报告无需 task coverage；无效 Git ref、脏的受控验证源码和不完整 artifact 给出可操作错误。
- AC-4: `quality:release` 在设置 `HARNESS_BASE_REF` 时执行 change-check，在未设置时明确报告本地覆盖检查未启用且不虚构远端强制性。
- AC-5: README 与 release-readiness 准确说明命令工作目录、基线变量、保证边界及当前尚无远端 required check。

## Result

Verified and closed by the harness close command.

## Evidence

[20260812-harness-change-enforcement.json](../../verification/evidence/20260812-harness-change-enforcement.json)

Closed at 2026-08-12T08:43:38.145573+00:00.
