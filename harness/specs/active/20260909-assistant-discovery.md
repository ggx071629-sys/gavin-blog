---
id: spec-20260909-assistant-discovery
level: L1
summary: 助手入口进入导航并提供可关闭首页提示
load_when:
  - task:20260909-assistant-discovery
task_id: 20260909-assistant-discovery
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 更新入口位置、提示偏好和焦点恢复合同。
state_history:
---
# Context
右下悬浮入口遮挡内容，用户确认仅实施顶部文字入口和首页可关闭提示。
# Goal
导航持续显示问 Gavin；首页介绍下方显示开始提问提示，关闭后记住偏好。
# Non-goals
不添加文章上下文入口，不改变面板模式、服务端、准入或会话存储。
# Acceptance criteria
- AC-1: 允许路径且开关启用时导航显示唯一问 Gavin 入口，无悬浮入口；不同视口无横溢。
- AC-2: 首页提示正常占位，点击打开同一面板，关闭后刷新不再出现；存储不可用时不影响页面及助手。
- AC-3: 入口不提前请求助手接口；关闭面板恢复触发点焦点，导航及助手保持单一 modal，禁用时入口和提示均隐藏。
# Risks
移动页眉空间、SSR hydration、存储异常和多个触发点的焦点恢复需要验证；仅存提示偏好，不存问答数据。
# Verification plan
## Verification cases
- AC-1 => M09-UI-DISCOVERY-01
- AC-2 => M09-UI-DISCOVERY-01
- AC-3 => M09-UI-DISCOVERY-01, M09-UI-BOUNDARY-01, M09-UNIT-ASSISTANT-DISABLED-01
## Gates
- e2e => AC-1, AC-2, AC-3
- web-quality => AC-3
- harness-integrity => AC-1, AC-2, AC-3
