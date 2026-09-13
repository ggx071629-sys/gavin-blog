---
id: spec-20260908-assistant-design-v2
level: L1
summary: 按助手设计稿还原公开问答浮窗与移动端视觉
load_when:
  - task:20260908-assistant-design-v2
task_id: 20260908-assistant-design-v2
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 记录设计来源、真实数据替代和现有模式范围。
state_history:
---
# Context
用户要求尽量一致还原 plan-build/ui-refinement/assistant_page_preview.html；现有公开助手具有严格会话与引用合同。
# Goal
还原主题色标识、分层面板、欢迎卡片、快捷问题、提问气泡、来源卡片和输入区，在真实问答中保持双主题和移动适配。按用户后续要求，深色强调色继承本站绿色，数据说明按钮移除加减号，保留展开交互。
# Non-goals
不引入全屏科研工作台、虚构指标和版本、原型控制条或示例答案；不变更服务端、准入、会话与键盘合同。
# Acceptance criteria
- AC-1: 480px 浮窗及手机/平板沿用现有尺寸与模式，应用设计稿视觉，长来源及短视口无横溢且操作可达。
- AC-2: 快捷提问、引用定位返回、数据披露、输入和清除交互保持可用，文案只展示已有事实。
# Risks
原型虚构匹配率、篇数与销毁承诺不可进入产品；小字号和深色颜色须保证可读性；样式限定助手以免污染页面。
# Verification plan
## Verification cases
- AC-1 => M09-UI-LAYOUT-01
- AC-2 => M09-UI-INTERACTION-01, M09-UI-STATES-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
