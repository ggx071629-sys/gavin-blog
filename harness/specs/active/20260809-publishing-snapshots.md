---
id: spec-20260809-publishing-snapshots
level: L1
summary: 为项目与书摘建立不可变发布快照并阻止文章关联区泄露工作副本
load_when:
  - task:20260809-publishing-snapshots
author: Codex
task_id: 20260809-publishing-snapshots
status: active
---

# 20260809-publishing-snapshots

## Context

项目与读书笔记的 PATCH 当前直接修改已发布主表并同步公开搜索，使“更新发布”按钮没有真实边界（AUD-02）。公开项目关联文章虽然过滤 `published` 状态，却直接序列化文章工作副本的 title、summary 与 slug，泄露尚未发布的元数据（AUD-03）。文章已具备 working copy + immutable revision，可作为一致性模式。

## Goal

让文章、项目和读书笔记共享同一公开内容原则：管理 PATCH 只更新工作副本；publish 使用 expected working version 原子创建并切换不可变发布 revision；公开 API、搜索、sitemap、关联卡片与公开路径只读取同一个当前发布快照。

## Non-goals

- 不改变编辑器离页保存协调；该边界已由 `20260809-editor-save-safety` 关闭。
- 不长期保留双写或双读兼容层。
- 不改造孵化草稿自身的发布计划模型。
- 不重新设计项目、书摘或文章的公开 UI。

## Acceptance criteria

- 新增项目与读书笔记 revision 表及 current published revision 指针；revision 内容不可变且每个资源的 revision number 单调递增。
- 迁移为现有 published 项目/书摘生成 revision 1，草稿不生成；升级、降级、再次升级均成功，降级不删除已生成 revision 数据。
- 项目/书摘 PATCH 仅更新 working copy 与 working version，不再改变公开 API、搜索结果、sitemap 或公开页面。
- publish 请求携带 expected working version；版本不匹配稳定返回 409，成功时在单一事务中创建/切换 revision 并同步所有公开消费者。
- 管理响应暴露 current publish revision 与 has unpublished changes，Web 的“更新发布”只在发布成功后改变公开内容。
- 公开项目的关联文章 title、summary、slug、published_at 与 public path 全部来自该文章当前发布 revision。
- 删除、恢复与 slug 稳定性保持现有契约；搜索只索引当前 published revision。
- contracts、API/Web 边界说明与实现同步。

## Risks

- 这是跨模型、迁移、API、搜索与 Web 的高成本改动，任一公开消费者漏切都会产生混合快照。
- SQLite 迁移降级不能通过删表丢失新 revision 数据；需要设计可逆指针/兼容策略。
- publish 与另一个标签页 autosave 的竞态若只在客户端判断，仍会发布旧 snapshot。
- 项目关联文章包含关系来自项目工作副本还是发布快照必须一致，否则仍会泄露未发布关联变更。

## Verification plan

- Pytest 先复现：已发布项目/书摘 PATCH 后公开 API 与搜索不变；publish 后同时切换；关联文章存在工作副本时项目卡片仍读旧 revision。
- Pytest 覆盖 expected working version 的并发 409、删除/恢复、slug 冲突和 revision 单调性。
- Alembic 在隔离旧数据副本上执行 upgrade → downgrade → upgrade，并断言已生成 revision 数据不丢失。
- 更新 OpenAPI 快照与共享 TypeScript contracts，运行 API lint/全套测试、Web typecheck/单测/build、相关 Playwright E2E。
- 从 `harness/` 运行 `python -m tools.harness verify 20260809-publishing-snapshots`，生成紧凑 evidence 后关闭 spec。
