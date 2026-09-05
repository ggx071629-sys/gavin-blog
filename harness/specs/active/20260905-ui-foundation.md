---
id: spec-20260905-ui-foundation
level: L1
summary: 完成视觉提案第一阶段的共用基础、公开外壳与后台框架
load_when:
  - task:20260905-ui-foundation
task_id: 20260905-ui-foundation
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 记录真实共用组件、尺度与外壳边界，区分本轮阶段和既有产品阶段。
state_history:
---

# Context

用户授权实施 ui-fix/PROPOSAL.md 第一阶段。基线为 917b16c03e36a528b6f0552bad7015fe7b6119c8；UI_AUDIT_REPORT.md 有无关用户修改，ui-fix 是本地忽略的设计材料。现有主题、导航 modal、认证和公开助手默认关闭合同均有效。中等风险：跨页面共享 CSS 与导航交互回归。

首轮 verify 发现原型 Markdown 的本地查询链接被 links gate 当成带问号的文件名。作为验收所需的最小修复，解析本地链接时只验证 query/fragment 之前的路径，继续拒绝缺失文件和 durable → active spec 链接，不降低门禁。

# Goal

整理实际路由、共用组件与设计差异，在真实 Nuxt 中落实安静背景、统一尺度、共用主题按钮、公开页头页尾和后台框架，并提供可复查验证记录。

# Non-goals

不改 API、存储、认证策略、依赖或质量阈值；不迁入首页栏目图、各页内容布局、编辑器工作流或助手新稿；不公开启用助手、不部署、不修改本地内容数据。

# Acceptance criteria

- AC-1: 现有字体和浅蓝/深黄绿语义色保持，页面背景不再全屏点阵；共用按钮、表单、反馈、列表、阅读容器使用明确尺度；双主题与代表宽度无新增横滚，未迁移的页面业务回归通过。
- AC-2: 公开页头与页尾层级收敛，桌面和移动导航保留现有入口顺序、当前页标记、认证入口和主题持久化；菜单维持全屏/抽屉/桌面断点、焦点循环、Escape 还焦点与背景解锁；菜单导航后焦点到达正文。
- AC-3: 后台框架以紧凑侧栏和轻量分组支持所有原有入口，共用主题组件正常；短视口导航可滚动，手机模态、焦点和认证行为不退化；页面与组件清单、改造前检查及验证结果可追踪，本地设计查询链接按真实文件路径验证且缺失/不稳定引用仍失败。

# Risks

共享样式可能影响长内容和未迁移页；保留正文布局值，仅建立命名尺度，逐阶段迁移。原型触控面积和断点不能直接照搬，保留产品已验证的 44px 控件与 modal 边界。验证使用隔离工作树及临时测试数据，避免 prepare 破坏已有预览。

# Verification plan

## Verification cases

- AC-1 => M01-P1-04
- AC-2 => M01-P1-01, M01-P1-02, M01-P1-04
- AC-3 => M02-P1-02, M08-LINKS-01

## Gates

- harness-tests => AC-3
- harness-integrity => AC-3
- web-quality => AC-1, AC-2, AC-3
- e2e => AC-1, AC-2, AC-3
