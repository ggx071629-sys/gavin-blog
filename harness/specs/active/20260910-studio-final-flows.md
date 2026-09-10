---
id: spec-20260910-studio-final-flows
level: L1
summary: 写作台真实管理闭环及共享边界最终回归
load_when:
  - task:20260910-studio-final-flows
task_id: 20260910-studio-final-flows
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U6-03 按计划在前置验收归档后实施。
# Goal
写作台真实管理闭环及共享边界最终回归
# Non-goals
不部署，不新增实时供应商资质门禁，不覆盖用户既有修改。
# Acceptance criteria
- AC-1: 登录退出、真实三类内容查询创建编辑保存发布、预览版本和运营操作通过。
- AC-2: 助手真实本地试问管理、失败恢复及保存和 API 查询/发布共享合同通过，公开主题不受 Studio 污染。
- AC-3: 配置简历链接时共用名片主按钮在双主题保持合格对比度，首页及关于页面无障碍回归通过。
# Risks
真实流程使用隔离本地 API 与受控助手供应商；生产数据不参与。
# Verification plan
## Verification cases
- AC-1 => M07-STUDIO-FLOWS-01, M06-STUDIO-LOGIN-01, M02-STUDIO-LIST-01, M04-STUDIO-BOOKS-01, M04-STUDIO-PROJECTS-01, M02-STUDIO-ARTICLE-EDITOR-01, M03-STUDIO-BOOK-EDITOR-01, M04-STUDIO-PROJECT-EDITOR-01, M02-STUDIO-PREVIEW-01, M02-STUDIO-REVISIONS-01, M06-STUDIO-PROFILE-01, M11-STUDIO-ABOUT-EDITOR-01, M11-STUDIO-ABOUT-PREVIEW-01, M11-STUDIO-ABOUT-HISTORY-01, M03-STUDIO-TAXONOMY-01, M05-STUDIO-MEDIA-01, M05-STUDIO-CONTENT-01
- AC-2 => M10-STUDIO-TRIAL-01, M10-STUDIO-DIALOGS-01, M10-STUDIO-OVERVIEW-01, M02-UNIT-AUTOSAVE-01, M02-UNIT-EDITOR-SAVE-CONTRACT-01, M02-STUDIO-QUERY-01, M02-UNIT-ARTICLE-REVISIONS-01, M04-P0-01, M04-P1-01, M11-PUBLISH-01, M06-STUDIO-FAILURE-GUARDS-01, M07-UNIT-TYPOGRAPHY-01, M10-STUDIO-HOST-GUARD-01, M07-STUDIO-PRODUCTION-01, M01-STUDIO-PRODUCTION-HOME-01
- AC-3 => M06-STUDIO-PROFILE-CONTRAST-01
## Gates
- e2e => AC-1, AC-2
- web-quality => AC-1, AC-2, AC-3
- api-tests => AC-1, AC-2
- harness-integrity => AC-1, AC-2, AC-3
