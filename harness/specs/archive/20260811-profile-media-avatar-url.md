---
id: archive-20260811-profile-media-avatar-url
level: L2
summary: 允许个人名片保存媒体库生成的受限站内头像地址
load_when:
  - task:20260811-profile-media-avatar-url
author: Codex
task_id: 20260811-profile-media-avatar-url
status: compressed
state_history:
---

# 20260811-profile-media-avatar-url

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让个人名片能够保存媒体库生成的安全同源头像路径，同时继续支持外部 HTTP(S) 头像 URL，并保持其他联系 URL 的严格 HTTP(S) 校验。

## Acceptance criteria

- `PATCH /api/v1/admin/profile` 接受 `/api/v1/media/{positive-id}/webp|avif` 形式的 `avatar_url` 并原样返回。
- 绝对 HTTP(S) 头像 URL 继续可用。
- 任意其他相对路径、路径穿越、协议相对 URL、查询串、片段及非 HTTP(S) 外部 URL 返回 422。
- 使用媒体库头像后，个人名片页保存成功且不再显示 422 错误。
- 其他个人资料 URL 字段的校验行为不变。

## Result

Verified and closed by the harness close command.

## Evidence

[20260811-profile-media-avatar-url.json](../../verification/evidence/20260811-profile-media-avatar-url.json)

Closed at 2026-08-12T02:23:26.874841+00:00.
