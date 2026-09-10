---
id: spec-20260911-assistant-about-sync
level: L1
summary: Q2-02 关于页发布回滚原子触发索引并撤销旧版本资格
load_when:
  - task:20260911-assistant-about-sync
task_id: 20260911-assistant-about-sync
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - packages/contracts/README.md
documentation_reason: 说明关于页事务同步、旧版失效和管理来源枚举。
state_history:
---
# Context
Q2-01 已验证关闭，about 投影可辨别主动修订；当前发布入口尚未写 outbox。
# Goal
在发布和回滚事务内登记 about 最新版本任务，并通过既有来源 fence 排除旧证据和迟到任务；新来源可通过管理合同读取。
# Non-goals
不改变初次重建枚举、前端引用或生成提示；这些留给 Q2-03/04。
# Acceptance criteria
- AC-1: 发布/回滚入队与修订原子一致，草稿无任务，失败无泄漏，重复发布合并到最新目标；旧来源版本立即被 fence 拒绝，管理 schema 与共享类型接受 about。
# Risks
事务外入队会丢同步；过时 task 和 evidence 必须以发布指针判定，不能仅信索引状态。
# Verification plan
## Verification cases
- AC-1 => M11-ASSISTANT-SYNC-01
## Gates
- api-tests => AC-1
- harness-integrity => AC-1
