---
id: spec-20260811-profile-media-avatar-url
level: L1
summary: 允许个人名片保存媒体库生成的受限站内头像地址
load_when:
  - task:20260811-profile-media-avatar-url
author: Codex
task_id: 20260811-profile-media-avatar-url
status: active
state_history:
---

# Context

个人名片页的媒体选择器返回同源路径 `/api/v1/media/{id}/{variant}`，前端将该值作为 `avatar_url` 原样提交。API 的 `ProfileUpdate.avatar_url` 仅接受绝对 `HttpUrl`，导致使用媒体库头像后保存稳定返回 422。登录前的 401 来自 `localhost` 与 `127.0.0.1` 不共享 Host-only 会话 Cookie，不是本次保存失败的根因。

# Goal

让个人名片能够保存媒体库生成的安全同源头像路径，同时继续支持外部 HTTP(S) 头像 URL，并保持其他联系 URL 的严格 HTTP(S) 校验。

# Non-goals

不放宽 GitHub、个人网页或简历 URL；不改变认证、CSRF、媒体存储或数据库结构；不接受任意相对路径、协议相对 URL、查询串或片段。

# Acceptance criteria

- `PATCH /api/v1/admin/profile` 接受 `/api/v1/media/{positive-id}/webp|avif` 形式的 `avatar_url` 并原样返回。
- 绝对 HTTP(S) 头像 URL 继续可用。
- 任意其他相对路径、路径穿越、协议相对 URL、查询串、片段及非 HTTP(S) 外部 URL 返回 422。
- 使用媒体库头像后，个人名片页保存成功且不再显示 422 错误。
- 其他个人资料 URL 字段的校验行为不变。

# Risks

放宽字符串校验可能引入开放重定向式或危险协议 URL。修复必须使用显式路径模式，而不是将头像字段退化为任意字符串。

# Verification plan

先补充 API 单元/集成测试覆盖允许与拒绝矩阵，再实现受限头像 URL 类型；重新生成 OpenAPI 契约并检查差异；运行 profile API 测试、相关 Web 测试与类型检查；最后在本地浏览器使用现有媒体头像执行一次真实保存并确认 200。
