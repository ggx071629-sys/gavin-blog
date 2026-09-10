---
id: spec-20260910-studio-controls
level: L1
summary: 统一写作台共用控件状态分隔行与弹窗视觉
load_when:
  - task:20260910-studio-controls
task_id: 20260910-studio-controls
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录共用控件尺度和状态语义边界供后续页面复用。
state_history:
---
# Context
阶段 1 已完成 U1-01 至 U1-03，当前执行共用控件。现有按钮、输入、状态标签、列表边框与第二版稿仍有差异。
# Goal
在 studio 作用域统一按钮、字段、页签、状态、开放列表分隔线与确认弹窗；保持所有真实业务状态及确认行为。修复版本预览所复用 ThemeToggle 的初始读屏状态水合不一致，公开视觉不变。
# Non-goals
不新增筛选、搜索、批量操作或状态模拟；不改 API、自动保存、发布、回滚逻辑、公开站视觉和已有用户改动；登录整体布局留 U1-05。
# Acceptance criteria
- AC-1: 后台主要/次要按钮桌面至少 48px、手机至少 44px；字段边框、字号、圆角和聚焦层级一致；页签保持选中反馈，窄屏与双主题可读且无页面横溢。
- AC-2: 草稿、已发布、有未发布修改和保存/错误状态保留不同真实语义，列表采用开放行和细分隔线，确认弹窗继承后台双主题并保留取消、Escape、焦点归还与真实回滚。
# Risks
共用 CSS 覆盖组件 scoped 样式或改变狭窄表单宽度；规则限定后台根节点，保留既有写作正文/设置切换和单实例预览。文本不只靠颜色表达状态。
# Verification plan
## Verification cases
- AC-1 => M02-DESK-LAYOUT-01, M07-STUDIO-THEME-01
- AC-2 => M02-DESK-REVISIONS-01, M07-STUDIO-THEME-01
## Gates
- e2e => AC-1, AC-2
- harness-integrity => AC-1, AC-2
