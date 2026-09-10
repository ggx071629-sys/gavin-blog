---
id: spec-20260910-studio-list-states
level: L1
summary: 验收三类列表的跨页查询、状态恢复与响应式闭环
load_when:
  - task:20260910-studio-list-states
task_id: 20260910-studio-list-states
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U3-05 按计划在前置验收归档后实施。
# Goal
验收三类列表的跨页查询、状态恢复与响应式闭环
# Non-goals
不改变发布或公开读取语义，不补充无依据统计。
# Acceptance criteria
- AC-1: 三类列表在大于一页的真实集合上可查询分页，切换状态回第一页，浏览器返回保留条件，清除恢复全部。
- AC-2: 三类列表读取中、失败、空集互不混淆，手机更多弹窗关闭还焦，深浅主题窄屏保持可达。
# Risks
条件变化必须复位分页，失败或迟到请求不能恢复旧集合。
# Verification plan
## Verification cases
- AC-1 => M02-STUDIO-LIST-STATES-01
- AC-2 => M02-STUDIO-LIST-STATES-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
