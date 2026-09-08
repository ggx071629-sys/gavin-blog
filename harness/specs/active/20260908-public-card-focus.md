---
id: spec-20260908-public-card-focus
level: L1
summary: 全站公开卡片统一聚焦反馈并排除全部写作台页面
load_when:
  - task:20260908-public-card-focus
task_id: 20260908-public-card-focus
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - harness/docs/product/interaction-references.md
documentation_reason: 记录已授权的公开卡片覆盖范围、输入方式和写作台排除边界。
state_history:
---
# Context
用户要求全站每个卡片采用所提供知识路径截图的聚焦反馈，写作台所有页面除外。现有图谱已关联点亮，其余公开卡片混用上浮与阴影。
# Goal
公开卡片采用主题色轮廓与浅色强调层，鼠标进入/离开以 180ms opacity transition 平滑切换；键盘焦点即时反馈，触屏按压即时反馈。不移动阅读位置。图谱保留整条路径选择和联动。
# Non-goals
不改接口、内容、导航目的地、图谱选择语义或写作台既有样式；不把纯展示卡片变成按钮或添加 Tab 停靠点；不把正文代码、图片或普通段落当成卡片。
# Acceptance criteria
- AC-1: 首页、文章/项目/书籍列表及详情、关于、搜索、归档、公开错误页和助手卡片具有统一反馈；两种主题下位置不变，嵌套卡片仅强调当前最内层，图谱仍联动。
- AC-2: 鼠标离开复位、键盘聚焦即时反馈、触屏不残留悬停；减少动态效果时反馈即时，原链接与控件可操作。
- AC-3: /admin 及所有子路由（含登录、运营、编辑、预览与版本页）不启用新卡片效果；公开与写作台间客户端跳转正确更新隔离标记。
# Risks
共享组件在预览和助手 Teleport 中复用；以 HTML 路由范围开关隔离，避免按组件名称误伤写作台。装饰层不捕获事件，使用显式卡片清单，不扩大到任意容器。
# Verification plan
## Verification cases
- AC-1 => M01-CARD-FOCUS-01
- AC-2 => M01-CARD-INPUT-01
- AC-3 => M01-CARD-SCOPE-01
## Gates
- e2e => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
