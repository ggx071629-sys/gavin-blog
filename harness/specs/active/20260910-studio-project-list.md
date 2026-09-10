---
id: spec-20260910-studio-project-list
level: L1
summary: 项目列表对齐开放行并呈现真实技术信息与查询操作
load_when:
  - task:20260910-studio-project-list
task_id: 20260910-studio-project-list
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
state_history:
---
# Context
U3-04 按计划在前置验收归档后实施。
# Goal
项目列表对齐开放行并呈现真实技术信息与查询操作
# Non-goals
不虚构技术栈字段，不新增项目版本历史，不改变发布接口。
# Acceptance criteria
- AC-1: 项目标题搜索与状态筛选使用完整服务端集合，真实摘要、仓库和站点链接可达，编辑及删除沿用确认。
- AC-2: 双主题窄屏无横溢且 axe 通过，读取失败可重试，不新增项目历史或虚构统计。
# Risks
真实模型只有摘要和仓库/站点链接，技术信息以这些字段为准。
# Verification plan
## Verification cases
- AC-1 => M04-STUDIO-PROJECTS-01
- AC-2 => M04-STUDIO-PROJECTS-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
