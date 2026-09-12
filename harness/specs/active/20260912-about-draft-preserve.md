---
id: spec-20260912-about-draft-preserve
level: L1
summary: 关于页自动保存不再清空尚未提交的领域标签输入
load_when:
  - task:20260912-about-draft-preserve
author: Codex
task_id: 20260912-about-draft-preserve
status: active
verification_profile: focused
documentation_impact: none
documentation_reason: 只修复关于页编辑器内部草稿状态缺陷并新增回归，未改变关于页字段契约或公开内容，README 无需同步。
state_history:
---
# Context
审查确认：修改网站说明触发 PATCH 时暂缓该真实请求，在第一项“新增领域标签”输入未提交文本，放行请求后输入被清空。根因是保存回声设置 page 值触发 watch 并重建全部草稿状态。
# Goal
区分服务器工作副本刷新与自动保存回声：无关字段保存完成后保留尚未提交的标签输入，提交该标签后正常清空；领域增删排序时临时草稿仍跟随对应领域。
# Non-goals
不新增服务端字段、不改变关于页业务字段与发布边界、不改变自动保存节流与冲突处理、不重构关于页表单结构。
# Acceptance criteria
- AC-1: 无关字段自动保存回声后，尚未提交的标签输入仍保留，提交后可正常清空。
- AC-2: 领域增删排序时临时草稿跟随对应领域，既有增删上限、预览与发布语义不变。
# Risks
只在保存回声跳过草稿重建，误判服务器刷新会保留过期草稿；草稿按领域索引跟随，若未来改为服务端排序可能与本地顺序不一致。
# Verification plan
## Verification cases
- AC-1 => M11-ABOUT-DRAFT-01
- AC-2 => M11-ABOUT-DRAFT-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
