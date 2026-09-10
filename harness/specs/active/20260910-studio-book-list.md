---
id: spec-20260910-studio-book-list
level: L1
summary: 读书列表对齐设计并接通完整书名作者查询
load_when:
  - task:20260910-studio-book-list
task_id: 20260910-studio-book-list
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录读书元信息与查询入口。
state_history:
---
# Context
U3-02 已验收，读书旧列表仍未接入查询。
# Goal
读书列表采用统一开放行及书名/作者搜索，保留阅读状态和版本操作。
# Non-goals
不新增读书历史、评分统计或公开页面变化。
# Acceptance criteria
- AC-1: 读书书名/作者、阅读状态和发布状态显示真实数据，作者查询、状态筛选、删除失败恢复可用。
- AC-2: 双主题手机桌面布局无横溢且 axe 通过，编辑及公开版本入口真实，不出现文章专属历史入口。
# Risks
共用组件已支持读书投影；本项只接入路由，不改变文章消费者。
# Verification plan
## Verification cases
- AC-1 => M04-STUDIO-BOOKS-01
- AC-2 => M04-STUDIO-BOOKS-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
