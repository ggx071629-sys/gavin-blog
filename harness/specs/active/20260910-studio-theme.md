---
id: spec-20260910-studio-theme
level: L1
summary: 为第二版写作台建立独立双主题和本地图标基础
load_when:
  - task:20260910-studio-theme
task_id: 20260910-studio-theme
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - completed/studio-ui-foundation/U1-02.md
documentation_reason: 记录后台主题作用域、资源来源、许可证及验证结论供后续阶段复用。
state_history:
---
# Context
第二版写作台采用独立蓝色双主题；现有后台继承公开页颜色，弹窗 Teleport 到 body。用户已授权依计划逐项实施；U1-01 已完成边界和已有改动核对。
# Goal
新增限于后台 shell、login 和后台弹窗的 studio 主题，复用本地 Inter/Noto Sans SC，并提供设计稿官方图标及许可，为后续外壳和控件提供一致基础。
# Non-goals
不修改公开页面、业务 API、认证、导航交互、主题偏好持久化合同、现有依赖版本、列表和编辑器布局；不部署。
# Acceptance criteria
- AC-1: 后台浅色画布 #ffffff、正文 #080c15、主色 #005dff，深色画布 #10141e、正文 #f0f3fa、主色 #7daaff；后台弹窗保持相同主题，公开页面原始颜色不变。
- AC-2: 后台使用本地 Inter/Noto Sans SC，图标来自选定设计包并保留 Tabler/Lucide 许可证；不发出外部字体或图标网络请求，基础组件类型正确。
# Risks
局部变量在 Teleport 中丢失；公共 CSS 级联覆盖字体；全局颜色修改影响公开页。所有 token 仅在显式后台根节点和后台弹窗设置，通过真实浏览器检查 computed style 和公开页对照。
# Verification plan
## Verification cases
- AC-1 => M07-STUDIO-THEME-01
- AC-2 => M07-STUDIO-THEME-01
## Gates
- e2e => AC-1, AC-2
- web-quality => AC-2
- harness-integrity => AC-1, AC-2
