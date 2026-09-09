---
id: spec-20260909-assistant-orb-motion
level: L1
summary: 用 GSAP 将助手入口改为可暂停的持续动效能量球
load_when:
  - task:20260909-assistant-orb-motion
task_id: 20260909-assistant-orb-motion
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 记录持续动效、暂停偏好和响应式生命周期。
state_history:
---
# Context
用户要求夸张、现代的常态悬浮球动效，使用 gsap-expert，优先 ScrollTrigger，保留移动端、性能、cleanup 与无障碍。
# Goal
以主题色能量核心、轨道和呼吸光晕强化助手入口；滚动仅驱动装饰环；持续动效可暂停。
# Non-goals
不改变问答、准入、默认开关、面板模式和拖动位置合同，不引入新的动画库或整页滚动劫持。
# Acceptance criteria
- AC-1: 双主题能量球持续悬浮和旋转，滚动驱动装饰环；双端点击、拖动吸边、引导和焦点恢复保持可用。
- AC-2: 用户可暂停并记住选择；减少动态效果下静态可用；后台、隐藏、拖动和聚焦停止常态动画；路由卸载清理自身时间线与 ScrollTrigger，反复进入不累积。
# Risks
连续动效可能影响阅读和电量，提供暂停并降低触屏幅度；装饰与真实点击区域分层，避免动画导致拖动坐标或焦点目标漂移；异步模块加载必须防卸载竞争。
# Verification plan
## Verification cases
- AC-1 => M09-UI-ORB-01, M09-UI-ORB-MOTION-01
- AC-2 => M09-UI-ORB-MOTION-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
