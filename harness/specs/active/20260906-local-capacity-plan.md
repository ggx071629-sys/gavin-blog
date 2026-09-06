---
id: spec-20260906-local-capacity-plan
level: L1
summary: 将阶段 D 资源验收改为本机测量与容量推算
load_when:
  - task:20260906-local-capacity-plan
task_id: 20260906-local-capacity-plan
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - build-qa.md
  - harness/docs/operations/e5-retrieval-evaluation.md
  - harness/docs/decisions/20260906-local-e5-retrieval.md
  - apps/api/README.md
documentation_reason: 用户明确替换阶段D资源方法，计划与当前操作说明需同步，历史测量不得改写。
state_history:
---

# Context

管理员已确认双语题集审核通过，现明确要求取消阶段 D 的 2 vCPU / 4 GB 真机共驻验收，改为本地运行后推算资源需求。此为验收方案变更，按 SDD 留存。无需再次询问授权。

# Goal

修改当前计划及对应说明：本机完整进程组测量，记录冷启动、稳态、查询与重建重叠的内存、CPU、延迟、磁盘，区分实测与估计，以明确余量和条件推算配置。服务器准备不再阻塞阶段 D 或 Chat 配置前置条件。

# Non-goals

本次不运行新压测、不声称已有完整容量推算，不改原始 benchmark、已关闭 spec 或审核记录事实，不修改生产 runtime/readiness 的可执行合同，也不部署服务器或调用 Chat。

# Acceptance criteria

- AC-1: build-qa 与当前操作/决策/API说明一致移除阶段D真机资源前置条件，定义可执行的本机采样与保守推算口径、假设与待补证据，保留已确认人工审核与实测结果，明确方案更新不等于本机容量测量已完成或生产自动放行。

# Verification plan

## Verification cases

- AC-1 => M08-DOCS-01

## Gates

- harness-integrity => AC-1
