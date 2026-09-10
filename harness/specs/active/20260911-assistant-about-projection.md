---
id: spec-20260911-assistant-about-projection
level: L1
summary: Q2-01 为关于页增加显式问答资格和发布正文投影
load_when:
  - task:20260911-assistant-about-projection
task_id: 20260911-assistant-about-projection
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明 about 来源投影、显式资格和草稿隔离。
state_history:
---
# Context
阶段二整体规格已提交；本子规格使 Q2-01 可独立通过正式验证并关闭，不提前要求 Q2-02—Q2-04 的未来实现。
# Goal
提供 about 来源类型、发布正文投影及资格迁移，保留既有四类来源和数据。
# Non-goals
本项不接发布 outbox、不改引用前端或提示词；它们仍按后续任务顺序实施。
# Acceptance criteria
- AC-1: 仅当前主动发布/回滚修订可投影，正文覆盖适用结构字段；草稿与 seed 排除，旧库升级保留数据并允许 about 索引类型，非法来源仍拒绝。
# Risks
seed 不能按 published 直接纳入；扩展数据库约束必须走新增迁移，不能修改历史迁移。
# Verification plan
## Verification cases
- AC-1 => M11-ASSISTANT-PROJECTION-01
## Gates
- api-tests => AC-1
- harness-integrity => AC-1
