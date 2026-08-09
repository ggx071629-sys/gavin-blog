---
id: spec-20260809-restore-writing-desk-entry
level: L1
summary: 在公开站点桌面与移动导航中恢复受认证保护的写作台入口
load_when:
  - task:20260809-restore-writing-desk-entry
author: Gavin
task_id: 20260809-restore-writing-desk-entry
status: verified
---

# Context

Electric Editorial UI 收口时，公开站点桌面导航和移动菜单中的“写作台”入口被移除，但 `/admin/articles`、管理员认证中间件和后台内容工作流仍然存在。站点管理员因此失去从公开页面进入私人工作区的持久入口。

# Goal

在不改变认证与后台行为的前提下，为桌面和移动端公开导航恢复清晰、一致的“写作台”入口，并复用当前 Electric Editorial 视觉语言。

# Non-goals

- 不新增公开注册、免登录访问或认证绕过。
- 不修改 API、数据库、Cookie、CSRF 或管理员会话逻辑。
- 不重构后台导航，也不在首页正文区增加重复 CTA。
- 不改变搜索、主题切换或现有公共导航顺序。

# Acceptance criteria

1. 桌面断点的公共页头显示“写作台”链接，目标为 `/admin/articles`，视觉层级与当前主按钮样式一致。
2. 移动端菜单打开后显示“写作台”链接，目标为 `/admin/articles`；点击后菜单关闭并进入现有认证流程。
3. 未登录访问入口仍由管理员中间件跳转到 `/admin/login`，不暴露后台内容。
4. 现有公共导航、搜索、主题切换和响应式菜单行为不回归。
5. 相关自动化测试能够观察桌面入口、移动入口及未登录重定向。

# Risks

- 入口恢复后后台地址更容易被发现；安全边界必须继续由服务端 Session、CSRF 和管理员中间件承担，不能依赖隐藏链接。
- 新按钮可能挤压中等宽度页头；实现需要保持当前 `lg` 断点策略，并通过桌面与移动视口验证。
- 移动菜单增加一项后可能改变网格平衡，但不得造成横向溢出或不可聚焦控件。

# Verification plan

- 先扩展 `public-experience` Playwright 场景，使其在实现前因缺少入口而失败。
- 运行目标 Playwright 场景，验证桌面与移动导航及未登录重定向。
- 运行 Web 类型检查和单元测试，排除组件与类型回归。
- 运行生产构建，确认 Nuxt 路由与样式编译成功。
- 运行 `python -m tools.harness verify 20260809-restore-writing-desk-entry`，验证 spec 与控制面完整性。
