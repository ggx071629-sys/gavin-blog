---
id: spec-20260909-assistant-orb
level: L1
summary: 保留导航并增加可拖动悬浮球与一次性提示
load_when:
  - task:20260909-assistant-orb
task_id: 20260909-assistant-orb
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 记录悬浮球位置偏好、引导生命周期和移除首页提示。
state_history:
---
# Context
用户经逐项讨论确认保留顶部入口，删除首页行内提示，双端提供可拖动悬浮球与首次使用提示。
# Goal
允许公开路径显示导航和悬浮球；页面稳定约三秒后展示可关闭提示；关闭或打开助手结束引导；拖动吸附最近左右边缘并记住位置。
# Non-goals
不修改问答服务端、准入、面板模式和问答数据存储，不增加文章上下文。
# Acceptance criteria
- AC-1: 顶部入口保留，首页行内提示移除；双端悬浮球点击打开同一助手，关闭恢复原触发点；禁止路径和禁用开关不展示。
- AC-2: 首次约三秒展示提示及影响阅读可关闭文案；关闭仅隐藏提示，任一入口打开助手也结束引导，同浏览器刷新和跨路由不再展开；存储异常安全降级。
- AC-3: 鼠标和触摸拖动不会误触打开；松手吸附最近左右边缘，刷新恢复位置；改变视口仍在安全可见范围，提示也不横溢。
# Risks
区分点击与拖动、pointercancel、尺寸变化、模态焦点锁和跨路由计时器清理；只保存位置和引导偏好，不保存问答数据。
# Verification plan
## Verification cases
- AC-1 => M09-UI-ORB-01, M09-UNIT-ASSISTANT-DISABLED-01
- AC-2 => M09-UI-ORB-01
- AC-3 => M09-UI-ORB-01, M09-UNIT-ORB-01
## Gates
- e2e => AC-1, AC-2, AC-3
- web-quality => AC-3
- harness-integrity => AC-1, AC-2, AC-3
