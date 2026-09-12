---
id: spec-20260912-book-cover-media-url
level: L1
summary: 读书封面接受媒体库站内地址并完成保存发布闭环
load_when:
  - task:20260912-book-cover-media-url
author: Codex
task_id: 20260912-book-cover-media-url
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 书籍封面地址契约新增受限站内媒体路径，需要在 API 文档中记录可接受形式。
state_history:
---
# Context
审查确认：读书编辑器的媒体库“使用 URL”写入 /api/v1/media/{id}/webp，而封面输入 type=url/pattern 与 BookNoteCreate/Update 的 HttpUrl 校验都拒绝该值，导致保存与发布受阻。既有个人名片头像已采用受限站内媒体路径约定。
# Goal
让书籍封面在创建与更新中同时接受完整 http(s) 地址和受限站内媒体路径，使媒体库选图到访客公开显示的闭环可完成，并保留既有无效输入校验。
# Non-goals
不放宽其他 URL 字段、不允许任意相对路径或非 HTTP(S) 协议、不改变 Markdown 导入元数据校验、不新增数据迁移、不改变媒体库自身契约。
# Acceptance criteria
- AC-1: 媒体库选中的站内封面地址通过表单校验，保存、刷新后保持，发布后访客看到同一图片。
- AC-2: 既有 http(s) 封面仍可用，其他相对与危险地址仍被拒绝，共享写作台字段文案可覆盖。
# Risks
联合类型顺序错误会退回 HttpUrl 拒绝站内路径；放宽到任意相对路径会引入协议外地址；Markdown 导入元数据仍只接受 http(s)，往返导入站内封面会 422，作为剩余风险记录。
# Verification plan
## Verification cases
- AC-1 => M04-BOOK-COVER-01, M04-BOOK-COVER-WEB-01, M08-DOCS-01
- AC-2 => M04-BOOK-COVER-01, M02-WRITING-FIELD-ERROR-01
## Gates
- api-tests => AC-1, AC-2
- e2e => AC-1, AC-2
- harness-integrity => AC-1
