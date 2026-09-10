---
id: spec-20260910-studio-article-list
level: L1
summary: 文章列表接通真实查询并对齐开放行设计
load_when:
  - task:20260910-studio-article-list
task_id: 20260910-studio-article-list
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录列表查询、状态提示和操作布局。
state_history:
---
# Context
U3-01 查询合同已验收归档，文章页仍使用旧数组列表。
# Goal
文章采用开放行、真实查询和状态计数、低频操作入口，保留分页与删除确认。
# Non-goals
不改 API、发布机制、公开页面或其他列表。
# Acceptance criteria
- AC-1: 文章搜索与状态筛选先于服务端分页，切换条件回第一页，分页和历史返回保留条件；错误可重试、空态可清除。
- AC-2: 文章开放行展示真实栏目、版本、未发布提示，编辑/预览/历史/删除可达，双主题手机桌面无横溢且通过 axe。
# Risks
迟到请求或失败不能伪装空结果，删除后需重新查询补足分页。
# Verification plan
## Verification cases
- AC-1 => M02-STUDIO-LIST-01
- AC-2 => M02-STUDIO-LIST-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
