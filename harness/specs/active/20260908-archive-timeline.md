---
id: spec-20260908-archive-timeline
level: L1
summary: 归档页改用年份旗标和双轨菱形时间轴
load_when:
  - task:20260908-archive-timeline
task_id: 20260908-archive-timeline
status: active
verification_profile: focused
documentation_impact: none
documentation_reason: 仅调整归档时间轴的局部呈现，数据、链接、日期、分页和产品边界不变。
state_history:
---
# Context
用户希望截图中的细线圆点时间轴更奔放。当前工作区干净，归档数据按年份分组，日期与文章链接已有稳定合同。
# Goal
用大号年份旗标、双轨刻度线、菱形节点和短支线强化时间轴，保留文章扫描顺序。
# Non-goals
不重做页头，不新增数据接口、不改变日期、排序或分页，不引入循环装饰动画。
# Acceptance criteria
- AC-1: 年份和各文章使用醒目的时间轴层级；真实年份、篇数、日期、分类与链接保持，桌面和390px手机、深浅主题不横溢，键盘焦点清晰。
# Risks
节点与支线不得遮挡文字，局部样式须覆盖旧归档规则而不影响其他页面。
# Verification plan
## Verification cases
- AC-1 => M01-ARCHIVE-TIMELINE-01
## Gates
- e2e => AC-1
- harness-integrity => AC-1
