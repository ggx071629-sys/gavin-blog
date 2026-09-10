---
id: spec-20260910-studio-book-editor
level: L1
summary: 读书新建编辑与页内预览对齐写作区和书籍设置
load_when:
  - task:20260910-studio-book-editor
task_id: 20260910-studio-book-editor
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U4-03 按计划在前置验收归档后实施。
# Goal
读书新建编辑与页内预览对齐写作区和书籍设置
# Non-goals
不新增读书版本历史，不改变保存队列、媒体与公开快照合同。
# Acceptance criteria
- AC-1: 读书新建编辑采用正文书名与右侧作者、阅读信息、封面及摘要链接分区；必填、媒体与页内预览可用。
- AC-2: 新建自动保存、取消与确认发布、工作副本隔离及双主题 320–1440px 可读性通过真实浏览器验证。
# Risks
作者、阅读日期和评分需完整保留；确认发布须在保存成功后。
# Verification plan
## Verification cases
- AC-1 => M03-STUDIO-BOOK-EDITOR-01
- AC-2 => M03-STUDIO-BOOK-EDITOR-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
