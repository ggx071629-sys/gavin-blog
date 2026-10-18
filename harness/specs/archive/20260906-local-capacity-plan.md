---
id: archive-20260906-local-capacity-plan
level: L2
summary: 将阶段 D 资源验收改为本机测量与容量推算
load_when:
  - task:20260906-local-capacity-plan
task_id: 20260906-local-capacity-plan
status: compressed
documentation_impact: required
documentation_targets:
  - build-qa.md
  - harness/docs/operations/e5-retrieval-evaluation.md
  - harness/docs/decisions/20260906-local-e5-retrieval.md
  - apps/api/README.md
documentation_reason: 用户明确替换阶段D资源方法，计划与当前操作说明需同步，历史测量不得改写。
evidence_sha256: 64de603ff8ca5b176ba646c25821f51078a50c245e0c1d8a34e4c69a01a4d786
state_history:
---

# 20260906-local-capacity-plan

Deterministic compressed record. The original active spec remains in Git history.

## Goal

修改当前计划及对应说明：本机完整进程组测量，记录冷启动、稳态、查询与重建重叠的内存、CPU、延迟、磁盘，区分实测与估计，以明确余量和条件推算配置。服务器准备不再阻塞阶段 D 或 Chat 配置前置条件。

## Acceptance criteria

- AC-1: build-qa 与当前操作/决策/API说明一致移除阶段D真机资源前置条件，定义可执行的本机采样与保守推算口径、假设与待补证据，保留已确认人工审核与实测结果，明确方案更新不等于本机容量测量已完成或生产自动放行。

## Result

Verified and closed by the harness close command.

## Evidence

[20260906-local-capacity-plan.json](../../verification/evidence/20260906-local-capacity-plan.json)

SHA-256: `64de603ff8ca5b176ba646c25821f51078a50c245e0c1d8a34e4c69a01a4d786`

Closed at 2026-09-06T10:13:02.947398+00:00.
