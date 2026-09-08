---
id: spec-20260909-public-card-glow
level: L1
summary: 补齐公开卡片随鼠标移动的局部光晕
load_when:
  - task:20260909-public-card-glow
task_id: 20260909-public-card-glow
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - harness/docs/product/interaction-references.md
documentation_reason: 记录用户确认的鼠标跟随光晕参数及首页图谱保留边界。
state_history:
---
# Context
上一轮仅推广了轮廓和浅色背景，遗漏用户希望复用的局部光晕。已检查首页原实现；用户确认进入卡片后光晕跟随鼠标。
# Goal
公开卡片采用首页同款 160px、12% 主题色径向光晕，随鼠标直接移动，进入离开沿用 180ms 淡入淡出。原卡片位置、图谱联动保持稳定。
# Non-goals
不改首页知识分支原有光晕，不改写作台，不新增设置开关、依赖、接口或卡片跳转语义。
# Acceptance criteria
- AC-1: 普通公开卡片和嵌套卡片的最内层光晕随两个不同鼠标位置移动，沿用页面主题色，裁切在圆角内部；首页分支保留原光晕且不重复叠加。
- AC-2: 离开、键盘输入、减少动态效果、触屏和进入写作台后无残留跟随光晕；清理待执行帧与事件监听，原反馈和导航可用。
# Risks
全局事件需限定路由、输入能力和显式卡片标记；坐标更新按帧合并；装饰不拦截交互，避免嵌套继承造成外层光晕。
# Verification plan
## Verification cases
- AC-1 => M01-CARD-GLOW-01
- AC-2 => M01-CARD-GLOW-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
