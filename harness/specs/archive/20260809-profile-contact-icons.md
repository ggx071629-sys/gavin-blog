---
id: archive-20260809-profile-contact-icons
level: L2
summary: 为个人名片接入独立网页地址并为联系方式提供一致的可访问 SVG 图标
load_when:
  - task:20260809-profile-contact-icons
author: Gavin
task_id: 20260809-profile-contact-icons
status: compressed
restoration_source: "fa89a6a2a1906ec9f80e596f5906d9ed54ccc52f:harness/specs/active/20260809-profile-contact-icons.md"
restored_at: 2026-08-11
---

# 20260809-profile-contact-icons

Deterministic compressed record. The original active spec remains in Git history.

## Goal

为 Profile 增加可选 `website_url`，贯通 SQLite、FastAPI、OpenAPI、Web 类型、后台编辑与公开名片；在名片中为 GitHub、邮箱、个人网页和简历使用统一风格的内联 SVG 图标，并保留清晰文字标签。

## Acceptance criteria

1. Alembic 新迁移为 `profiles` 增加可空、最大 500 字符的 `website_url`，支持 upgrade 与 downgrade。
2. Profile 的公开响应、管理响应与更新请求均包含可选 `website_url`；更新请求仅接受 HTTP(S) URL。
3. 后台个人名片表单提供“个人网页”输入，保存后实时预览与公开首页一致。
4. 公开名片在字段存在时展示 GitHub、复制邮箱和个人网页入口，分别使用 GitHub、信封和地球线性 SVG；简历入口使用下载 SVG。
5. 所有 SVG 标记为装饰性 `aria-hidden`，按钮或链接保留文字标签和现有可访问名称；GitHub、网页和简历新标签打开并带安全 `rel`。
6. 字段为空时对应入口不渲染；隐藏邮箱仍不会进入公开响应或公开名片。
7. OpenAPI 快照、Web 类型、API/Profile 测试和 Profile E2E 与新字段保持同步。

## Result

Verified and closed by the harness close command.

## Evidence

[20260809-profile-contact-icons.json](../../verification/evidence/20260809-profile-contact-icons.json)

Closed at 2026-08-09T13:05:17.241860+00:00.
