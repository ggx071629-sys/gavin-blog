---
id: spec-20260910-studio-login
level: L1
summary: 对齐居中登录稿并完成阶段一适用验收
load_when:
  - task:20260910-studio-login
task_id: 20260910-studio-login
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录登录单列布局与保留的认证和错误反馈合同。
state_history:
---
# Context
U1-01 至 U1-04 已按顺序验收归档；登录页仍为旧双栏结构，选定第二版稿使用居中 430px 单列表单。
# Goal
对齐 #login 的字体、留白和表单层级，保留真实登录、安全返回、提交防重、字段错误和返回站点；完成阶段一适用回归。
# Non-goals
不更改认证 API、CSRF、用户名默认值、密码规则或公开站视觉；不复制演示登录或注册入口，不部署。
# Acceptance criteria
- AC-1: 登录页在双主题使用同一居中单列结构，桌面表单宽 430px，手机保留安全边距；标题、说明、字段、主按钮与选定稿一致，320–1440px 无横溢、axe 违规或水合错误。
- AC-2: 真实凭据登录后保留安全 returnTo；提交期间锁定防重，401/403/429/500/网络失败保留准确可操作反馈和字段可访问关联；后台主题和真实弹窗未回退。
# Risks
旧双栏验收断言须同步为新布局，不能删除行为断言；设计稿仅演示，不能替代真正的 CSRF、错误分类和安全返回路径。
# Verification plan
## Verification cases
- AC-1 => M06-STUDIO-LOGIN-01
- AC-2 => M06-STUDIO-LOGIN-01, M06-STUDIO-LOGIN-ERROR-01, M07-STUDIO-THEME-01
## Gates
- e2e => AC-1, AC-2
- web-quality => AC-2
- harness-integrity => AC-1, AC-2
