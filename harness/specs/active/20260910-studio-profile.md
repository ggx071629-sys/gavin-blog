---
id: spec-20260910-studio-profile
level: L1
summary: 阶段五个人名片分组表单与真实预览
load_when:
  - task:20260910-studio-profile
task_id: 20260910-studio-profile
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录名片分区与公开资料共用边界。
state_history:
---
# Context
U5-01；U4-07 已验收归档。沿用第二版 Studio 设计，保留既有用户改动。
# Goal
个人名片以基本资料、头像、技能与联系分组，保持真实预览与保存。
# Non-goals
不改公开首页、关于页和资料 API，不进入后续任务直至本项验收归档。
# Acceptance criteria
- AC-1: 分区、实时预览和操作在双主题及 320–1440px 可读可用，技能增删排序与头像选择保持正确。
- AC-2: 保存失败保留输入、重试成功，公开名称与可见性继续由真实资料提供。
# Risks
不得泄露隐藏联系资料，不得以演示成功代替真实保存；媒体控件保持独立表单边界。
# Verification plan
## Verification cases
- AC-1 => M06-STUDIO-PROFILE-01
- AC-2 => M06-OPS-PROFILE-01, M06-PROFILE-HOME-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
