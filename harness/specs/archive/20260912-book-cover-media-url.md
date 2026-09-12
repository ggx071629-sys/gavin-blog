---
id: archive-20260912-book-cover-media-url
level: L2
summary: 读书封面接受媒体库站内地址并完成保存发布闭环
load_when:
  - task:20260912-book-cover-media-url
author: Codex
task_id: 20260912-book-cover-media-url
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 书籍封面地址契约新增受限站内媒体路径，需要在 API 文档中记录可接受形式。
evidence_sha256: aa2546789820f034caa41a68bb4a57b1063380bbff45d24b9dbf6bfad19bb81a
state_history:
---

# 20260912-book-cover-media-url

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让书籍封面在创建与更新中同时接受完整 http(s) 地址和受限站内媒体路径，使媒体库选图到访客公开显示的闭环可完成，并保留既有无效输入校验。

## Acceptance criteria

- AC-1: 媒体库选中的站内封面地址通过表单校验，保存、刷新后保持，发布后访客看到同一图片。
- AC-2: 既有 http(s) 封面仍可用，其他相对与危险地址仍被拒绝，共享写作台字段文案可覆盖。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-book-cover-media-url.json](../../verification/evidence/20260912-book-cover-media-url.json)

SHA-256: `aa2546789820f034caa41a68bb4a57b1063380bbff45d24b9dbf6bfad19bb81a`

Closed at 2026-09-12T04:54:27.897905+00:00.
