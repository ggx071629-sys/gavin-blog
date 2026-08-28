---
id: spec-20260827-admin-login-penpot-alignment
level: L1
summary: 按 Penpot Admin Login 桌面与移动目标重排登录页视觉，同时完整保留现有认证、安全与失败合同
load_when:
  - task:20260827-admin-login-penpot-alignment
author: Gavin
task_id: 20260827-admin-login-penpot-alignment
status: active
verification_profile: release
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 管理登录页的桌面分栏、开放式表单、移动单列和可访问状态发生用户可见变化，需要同步 Web 应用边界说明。
state_history:
---

# Context

当前 `/admin/login` 桌面端是品牌分栏加蓝色装饰渐变，右侧表单位于带边框、圆角和阴影的悬浮卡片；移动端仍保留外层卡片感。登录页已有用户名/密码、CSRF、safe returnTo、提交禁用、失败分类与无障碍错误合同。

已核验的 Penpot 视觉目标为：

- Admin Login Desktop `faa08c08-ba3b-8031-8008-831cbbe71f65`
- Admin Login Mobile `153af549-5bcc-80a6-8008-836363972a40`

Penpot 只约束视觉与交互表达；认证、路由、安全和失败语义以仓库现有实现为准。设计未明确的 submitting、disabled、error、深色主题等状态必须保留仓库合同，并通过现有 `--ee-*` 语义 token 表达。

# Goal

在不改变认证行为的前提下，使 `/admin/login` 桌面保留等宽左右分栏但改为安静 surface + 开放式表单，移动端改为具有安全边距的单列表单并去除外层卡片感，对齐已核验 Penpot 目标，同时保持双主题、键盘、触控和失败状态可用。

# Non-goals

- 不修改 API、数据库、共享 contracts、Session、Cookie、CSRF、限流或权限边界。
- 不修改 safe `returnTo` 规则、成功后的导航目标或现有错误分类文案。
- 不新增注册、找回密码、第三方登录、记住我或设计稿不存在的功能。
- 不重做其它后台页面、后台壳层或公开站 Header。
- 不新增平行设计 token，不在 Vue 组件中加入原始 hex 色值，不做无关 CSS 清理。
- 不修改 Penpot 云端资源、远程仓库或部署流程。

# Acceptance criteria

- AC-1: 1440px 桌面对齐 Admin Login Desktop `faa08c08-ba3b-8031-8008-831cbbe71f65`：使用等宽左右分栏；左栏使用安静的现有 surface 表达且不再出现明显蓝色装饰渐变；右侧表单采用开放式布局，不再呈现带边框、阴影和悬浮卡片轮廓；保留真实品牌与私人工作区文案。
- AC-2: 320、390 和 414px 对齐 Admin Login Mobile `153af549-5bcc-80a6-8008-836363972a40`：直接呈现有安全边距的单列表单，不保留外层卡片感；1024 与 1440 布局连续，无横向溢出、遮挡或裁切。浅色和深色均只复用现有 `--ee-*` token。
- AC-3: 用户名和密码字段、autocomplete、CSRF 获取及 `X-CSRF-Token` 发送、登录 POST、safe `returnTo`、成功导航、hydration 前禁用、submitting 防重复提交及完成后的状态恢复保持现有行为。
- AC-4: 401、403、429、5xx 和网络失败继续使用现有分类与文案；错误使用 `role="alert"`，相关字段保持 `aria-invalid`/`aria-describedby`，提交中与 disabled 状态可见且不会伪装成功。
- AC-5: 页面保持一个可见 H1、明确 label、可见键盘焦点和至少 44×44 CSS px 的交互目标；返回首页、主题切换与 `noindex,nofollow` 保留；axe 无新增 A/AA 问题，真实浏览器无 page error、console error 或新增非预期 warning；页面不出现注册或找回密码入口。
- AC-6: `apps/web/README.md` 记录登录页桌面分栏、开放式表单、移动单列及认证状态不变的边界；类型检查、Vitest、构建、登录失败套件、quality 与相关 E2E 按 gate 实际结果留证。

# Risks

- 视觉层若重写表单 DOM，容易破坏现有 testid、label、autocomplete、错误关联或提交状态。
- 去除卡片边框和阴影不能通过透明边框占位伪装完成；应检查真实 computed style 和截图。
- Penpot 未定义全部认证失败、submitting 和深色状态；这些状态必须服从仓库合同，不得为视觉一致删减。
- 320px 宽度及移动软键盘可能压缩可用高度；表单不能依赖固定视口高度或导致底部按钮不可达。
- 登录页 CSS 必须保持局部，避免改变其它后台 surface、field 或 button 默认样式。

# Verification plan

- e2e => AC-1, AC-2, AC-3, AC-4, AC-5
- web-quality => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6
- release => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6
