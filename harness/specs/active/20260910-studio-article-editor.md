---
id: spec-20260910-studio-article-editor
level: L1
summary: 文章新建编辑对齐设置分区并明确保存与发布确认
load_when:
  - task:20260910-studio-article-editor
task_id: 20260910-studio-article-editor
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U4-02 按计划在前置验收归档后实施。
# Goal
文章新建编辑对齐设置分区并明确保存与发布确认
# Non-goals
不改变保存队列、发布快照、媒体校验与离页屏障，不重写编辑器。
# Acceptance criteria
- AC-1: 文章新建/编辑标题、返回入口和栏目标签/摘要链接/参考资料分区符合写作布局，必填和冲突可见，桌面手机可读。
- AC-2: 创建草稿后自动保存，发布先校验保存再明确确认；取消不发布，确认仅发送已保存版本，编辑既有发布内容不意外公开。
# Risks
发布确认必须置于校验和保存屏障后，取消不得发布；新建失败需保留表单。
# Verification plan
## Verification cases
- AC-1 => M02-STUDIO-ARTICLE-EDITOR-01
- AC-2 => M02-STUDIO-ARTICLE-EDITOR-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
