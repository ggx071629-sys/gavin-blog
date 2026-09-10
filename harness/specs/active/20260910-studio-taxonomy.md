---
id: spec-20260910-studio-taxonomy
level: L1
summary: 栏目标签开放列表、编辑与关联约束提示
load_when:
  - task:20260910-studio-taxonomy
task_id: 20260910-studio-taxonomy
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U5-05 按计划在前置验收归档后实施。
# Goal
栏目标签开放列表、编辑与关联约束提示
# Non-goals
不改变分类契约或增加虚构关联统计；本项归档后转 U5-06。
# Acceptance criteria
- AC-1: 栏目与标签有清晰列表、数量和独立编辑区，键盘焦点、长文本及双主题响应式可用。
- AC-2: 真实新增、编辑和删除保留服务端关联约束与失败反馈，取消编辑不修改数据。
# Risks
已关联栏目不可被错误删除；表单失败不丢弃输入。
# Verification plan
## Verification cases
- AC-1 => M03-STUDIO-TAXONOMY-01
- AC-2 => M03-STUDIO-TAXONOMY-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
