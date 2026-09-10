---
id: spec-20260910-studio-content-tools
level: L1
summary: 回收站恢复删除与 Markdown 迁移分区
load_when:
  - task:20260910-studio-content-tools
task_id: 20260910-studio-content-tools
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U5-07 按计划在前置验收归档后实施。
# Goal
回收站恢复删除与 Markdown 迁移分区
# Non-goals
不改变迁移格式、永久删除语义或数据模型；本项归档后只进行 U5-08，不进入阶段六。
# Acceptance criteria
- AC-1: 回收站采用开放记录、真实本页数量与恢复/永久删除操作，取消和失败保留内容。
- AC-2: Markdown 导入只创建草稿、导出真实 ZIP，失败可重试；两区及长文本在双主题窄屏可用。
# Risks
永久删除必须保留确认；导入成功不得误报为发布，导出失败不能误报下载成功。
# Verification plan
## Verification cases
- AC-1 => M05-STUDIO-CONTENT-01
- AC-2 => M05-STUDIO-CONTENT-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
