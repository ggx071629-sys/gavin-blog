---
id: archive-20260910-studio-login
level: L2
summary: 对齐居中登录稿并完成阶段一适用验收
load_when:
  - task:20260910-studio-login
task_id: 20260910-studio-login
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录登录单列布局与保留的认证和错误反馈合同。
evidence_sha256: 8831cf878f1f91aabb9c1983c88861220c08abd0d53bb672cff2d3c6151561bb
state_history:
---

# 20260910-studio-login

Deterministic compressed record. The original active spec remains in Git history.

## Goal

对齐 #login 的字体、留白和表单层级，保留真实登录、安全返回、提交防重、字段错误和返回站点；完成阶段一适用回归。

## Acceptance criteria

- AC-1: 登录页在双主题使用同一居中单列结构，桌面表单宽 430px，手机保留安全边距；标题、说明、字段、主按钮与选定稿一致，320–1440px 无横溢、axe 违规或水合错误。
- AC-2: 真实凭据登录后保留安全 returnTo；提交期间锁定防重，401/403/429/500/网络失败保留准确可操作反馈和字段可访问关联；后台主题和真实弹窗未回退。

## Result

Verified and closed by the harness close command.

## Evidence

[20260910-studio-login.json](../../verification/evidence/20260910-studio-login.json)

SHA-256: `8831cf878f1f91aabb9c1983c88861220c08abd0d53bb672cff2d3c6151561bb`

Closed at 2026-09-10T07:18:25.636683+00:00.
