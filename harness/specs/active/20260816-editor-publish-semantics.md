---
id: spec-20260816-editor-publish-semantics
level: L1
summary: 锁住已发布 slug、拆开 409 语义、文章发布校验 version，导出读发布修订
load_when:
  - task:20260816-editor-publish-semantics
author: Gavin
task_id: 20260816-editor-publish-semantics
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
  - apps/api/README.md
documentation_reason: 发布携带 version、已发布 slug 只读、导出读修订都是写作台契约，需要写进 API 与 Web 边界。
state_history:
---

# Context

2026-08-16 审计 AUD26-022/023/025/026：已发布文章 slug 仍可改，409 被当成并发写入；文章 `POST /publish` 不校验 version；编辑器次级加载和空参考会假绿或 422；Markdown 导出写出工作副本却标 `published`。

# Goal

已发布 slug 在编辑器只读。版本冲突与 slug 锁定不再共用「服务器上已有更新」。文章发布携带并校验工作副本 version。文章编辑器次级加载走失败分类；未填完的参考资料不自动 PATCH。已发布内容的 Markdown 导出使用当前发布修订。

# Non-goals

- 不改公开栏目读修订（第二批已关）。
- 不改回收站级联删除或孵化发布计划确认窗口（第四批）。
- 不改两条 GitHub frozen spec。
- 不在本批处理栏目标签缓存刷新或粘贴图片竞态。

# Acceptance criteria

- AC-1: 文章/项目/书摘编辑器在 `status === published` 时禁用 slug 输入；API 对已发布改 slug 仍返回 409，且该 409 不得把保存状态标成版本冲突。
- AC-2: `POST /api/v1/admin/articles/{id}/publish` 接受 `PublishRequest.version`；与工作副本 version 不一致时 409 `article was updated elsewhere`。编辑器发布请求带上 flush 后的 version。
- AC-3: `ArticleEditor` 对栏目/标签/参考目标加载调用 `useApiFailure`；未完成的参考资料行不进入自动保存 PATCH。
- AC-4: 编辑器发布失败（非 Alt 校验）写入可见 `publishError`，不得只闪过「发布中」。
- AC-5: `GET /api/v1/admin/exports/markdown` 对已发布文章/项目/书摘写入当前发布修订的正文与 slug；未发布 PATCH 不得出现在导出文件里。
- AC-6: `apps/api/README.md` 与 `apps/web/README.md` 写明已发布 slug 只读、文章发布校验 version、导出读修订。

# Risks

禁用 slug 后操作者若要改公开地址只能新建并迁移；这是已声明的 URL 稳定契约。

# Verification plan

- api-lint => AC-1, AC-2, AC-5, AC-6
- api-tests => AC-1, AC-2, AC-5
- web-quality => AC-1, AC-2, AC-3, AC-4, AC-6
