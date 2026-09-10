---
id: spec-20260910-studio-project-editor
level: L1
summary: 项目新建编辑与页内预览对齐项目链接与关联文章设置
load_when:
  - task:20260910-studio-project-editor
task_id: 20260910-studio-project-editor
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U4-04 按计划在前置验收归档后实施。
# Goal
项目新建编辑与页内预览对齐项目链接与关联文章设置
# Non-goals
不新增技术栈字段或项目版本历史，不改变保存队列和公开快照合同。
# Acceptance criteria
- AC-1: 项目标题正文与摘要链接、项目地址、关联文章分区清晰；必填、URL 校验和真实页内预览可用。
- AC-2: 保存成功后确认发布、取消保留草稿、工作副本隔离及双主题 320–1440px 通过验证。
# Risks
仓库站点 URL 必须通过校验；关联文章完整分页来源保持不变。
# Verification plan
## Verification cases
- AC-1 => M04-STUDIO-PROJECT-EDITOR-01
- AC-2 => M04-STUDIO-PROJECT-EDITOR-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
