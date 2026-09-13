---
id: archive-20260816-editor-publish-semantics
level: L2
summary: 锁住已发布 slug、拆开 409 语义、文章发布校验 version，导出读发布修订
load_when:
  - task:20260816-editor-publish-semantics
author: Gavin
task_id: 20260816-editor-publish-semantics
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/README.md
  - apps/api/README.md
documentation_reason: 发布携带 version、已发布 slug 只读、导出读修订都是写作台契约，需要写进 API 与 Web 边界。
state_history:
---

# 20260816-editor-publish-semantics

Deterministic compressed record. The original active spec remains in Git history.

## Goal

已发布 slug 在编辑器只读。版本冲突与 slug 锁定不再共用「服务器上已有更新」。文章发布携带并校验工作副本 version。文章编辑器次级加载走失败分类；未填完的参考资料不自动 PATCH。已发布内容的 Markdown 导出使用当前发布修订。

## Acceptance criteria

- AC-1: 文章/项目/书摘编辑器在 `status === published` 时禁用 slug 输入；API 对已发布改 slug 仍返回 409，且该 409 不得把保存状态标成版本冲突。
- AC-2: `POST /api/v1/admin/articles/{id}/publish` 接受 `PublishRequest.version`；与工作副本 version 不一致时 409 `article was updated elsewhere`。编辑器发布请求带上 flush 后的 version。
- AC-3: `ArticleEditor` 对栏目/标签/参考目标加载调用 `useApiFailure`；未完成的参考资料行不进入自动保存 PATCH。
- AC-4: 编辑器发布失败（非 Alt 校验）写入可见 `publishError`，不得只闪过「发布中」。
- AC-5: `GET /api/v1/admin/exports/markdown` 对已发布文章/项目/书摘写入当前发布修订的正文与 slug；未发布 PATCH 不得出现在导出文件里。
- AC-6: `apps/api/README.md` 与 `apps/web/README.md` 写明已发布 slug 只读、文章发布校验 version、导出读修订。

## Result

Verified and closed by the harness close command.

## Evidence

[20260816-editor-publish-semantics.json](../../verification/evidence/20260816-editor-publish-semantics.json)

Closed at 2026-08-16T12:07:42.324856+00:00.
