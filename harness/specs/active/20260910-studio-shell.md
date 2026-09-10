---
id: spec-20260910-studio-shell
level: L1
summary: 对齐第二版写作台侧栏移动导航品牌及页头
load_when:
  - task:20260910-studio-shell
task_id: 20260910-studio-shell
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录侧栏断点、主题切换和短视口导航的持续约束。
state_history:
---
# Context
U1-01 和 U1-02 已通过验收并归档，当前执行 U1-03。现有侧栏为 216px、无图标，品牌及页头层级与第二版稿不同。
# Goal
采用桌面 254px 浅灰蓝侧栏、36px 主内容边距、文字品牌和带本地图标的分组导航；中等屏 230px 侧栏，760px 以下折叠为可访问移动导航。
# Non-goals
不改内容页面业务、列表筛选、编辑器、登录布局或认证接口，不复制设计预览与演示数据，不修改公开页和已有用户改动。
# Acceptance criteria
- AC-1: 1440/1487px 桌面侧栏 254px、主内容起点 x=290；761–1300px 侧栏 230px；内容/运营九项图标和当前路径状态可辨，深浅主题保持蓝色和同一布局，短视口导航/退出可达。
- AC-2: 320/390/760px 菜单按钮打开 modal 导航，Tab 循环、Escape 和遮罩关闭后归还焦点；路由导航与切回桌面解除 inert/滚动锁，查看站点和真实退出仍可用，无横溢、缺失图标或浏览器错误。
# Risks
断点变化可能使既有写作区狭窄；只调整外壳并检查主要页面。主题按钮更换表现必须保留 color-mode 持久化、可访问名称和点击目标。退出失败仍按原逻辑报告。
# Verification plan
## Verification cases
- AC-1 => M02-STUDIO-SHELL-01
- AC-2 => M02-STUDIO-SHELL-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
