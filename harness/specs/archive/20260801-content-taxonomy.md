---
id: archive-20260801-content-taxonomy
level: L2
summary: 为文章增加栏目与标签管理、关联和公开筛选，启动完整内容系统阶段
load_when:
  - task:20260801-content-taxonomy
author: Gavin
task_id: 20260801-content-taxonomy
status: compressed
---

# 20260801-content-taxonomy

Deterministic compressed record. The original active spec remains in Git history.

## Goal

单管理员可以维护栏目与标签并关联到文章；公开读者可以看到文章的栏目与标签，并在文章列表按栏目或标签筛选已发布内容。

## Acceptance criteria

- Alembic 新增栏目、标签、文章标签关联及文章可选栏目外键；栏目和标签 slug 唯一。
- 管理 API 支持栏目与标签的读取、创建、更新和删除；仍受 Session 与 CSRF 保护。
- 文章创建与带版本号自动保存可以设置一个栏目和多个标签；无效关联返回 `422`，并保留 `409` 乐观锁语义。
- 已使用的栏目或标签不能被删除，API 明确返回 `409`。
- 公开文章响应包含栏目与标签；公开列表支持 `category` 和 `tag` slug 查询参数，且永不返回草稿。
- Nuxt 管理端提供栏目与标签维护入口，并在文章编辑器中支持元数据关联。
- 公开文章卡片和详情展示栏目与标签；文章列表提供可分享 URL 的栏目／标签筛选。
- Pytest 覆盖 CRUD、防护、关联、删除冲突、筛选与草稿隔离；Vitest 覆盖筛选查询工具。
- OpenAPI 快照与前端 TypeScript 契约同步。

## Result

Verified and closed by the harness close command.

## Evidence

[20260801-content-taxonomy.json](../../verification/evidence/20260801-content-taxonomy.json)

Closed at 2026-08-01T16:42:34.219206+00:00.
