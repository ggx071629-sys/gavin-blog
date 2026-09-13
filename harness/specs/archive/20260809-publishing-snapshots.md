---
id: archive-20260809-publishing-snapshots
level: L2
summary: 为项目与书摘建立不可变发布快照并阻止文章关联区泄露工作副本
load_when:
  - task:20260809-publishing-snapshots
author: Codex
task_id: 20260809-publishing-snapshots
status: compressed
---

# 20260809-publishing-snapshots

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让文章、项目和读书笔记共享同一公开内容原则：管理 PATCH 只更新工作副本；publish 使用 expected working version 原子创建并切换不可变发布 revision；公开 API、搜索、sitemap、关联卡片与公开路径只读取同一个当前发布快照。

## Acceptance criteria

- 新增项目与读书笔记 revision 表及 current published revision 指针；revision 内容不可变且每个资源的 revision number 单调递增。
- 迁移为现有 published 项目/书摘生成 revision 1，草稿不生成；升级、降级、再次升级均成功，降级不删除已生成 revision 数据。
- 项目/书摘 PATCH 仅更新 working copy 与 working version，不再改变公开 API、搜索结果、sitemap 或公开页面。
- publish 请求携带 expected working version；版本不匹配稳定返回 409，成功时在单一事务中创建/切换 revision 并同步所有公开消费者。
- 管理响应暴露 current publish revision 与 has unpublished changes，Web 的“更新发布”只在发布成功后改变公开内容。
- 公开项目的关联文章 title、summary、slug、published_at 与 public path 全部来自该文章当前发布 revision。
- 删除、恢复与 slug 稳定性保持现有契约；搜索只索引当前 published revision。
- contracts、API/Web 边界说明与实现同步。

## Result

Verified and closed by the harness close command.

## Evidence

[20260809-publishing-snapshots.json](../../verification/evidence/20260809-publishing-snapshots.json)

Closed at 2026-08-09T15:15:28.092019+00:00.
