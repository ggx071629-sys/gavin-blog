---
id: archive-20260907-about-page-editor
level: L2
summary: 为写作台增加关于页内容编辑器，以工作副本与不可变发布修订管理 About 页专属文案
load_when:
  - task:20260907-about-page-editor
author: Codex
task_id: 20260907-about-page-editor
status: compressed
documentation_impact: required
documentation_targets:
  - README.md
  - apps/web/README.md
  - apps/api/README.md
  - harness/docs/product/brief.md
documentation_reason: 新增产品模块、公开 About 数据源与管理发布生命周期，需要同步项目边界与模块映射文档。
evidence_sha256: db4b2fc60e188810a6768312aa98e9187ee0282f1b6836ad7e77b435baeda630
state_history:
---

# 20260907-about-page-editor

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在写作台提供 `/admin/about` 关于页编辑器，使管理员能编辑引言（与 `profile.bio` 解耦）、能力领域、最近在做、写作范围、网站说明与技术栈；编辑内容先保存在工作副本，预览确认后发布为不可变修订，公开 `/about` 只展示当前发布修订，并保留发布历史与回滚。

## Acceptance criteria

- AC-1: 升级或新建数据库后自动存在一个已发布修订 #1，工作副本与公开内容都等于当前 About 页面文案；`statement` 为独立字段，改 `profile.bio` 不会改变已发布引言。
- AC-2: 公开 `GET /about-page` 只返回当前发布修订中的 `statement`、`capabilities`、`now`、`editorial`、`site`，不返回草稿、`version` 冲突细节或任何未发布修改。
- AC-3: 管理员可在 `/admin/about` 编辑五块 About 专属内容，`PATCH` 持久化工作副本并推进乐观锁；保存期间公开页保持当前发布内容，版本冲突返回 409 且不覆盖。
- AC-4: `/admin/about/preview` 用已保存的工作副本渲染 About 展示区，并明确提示“草稿预览”或“工作副本预览（公开站仍显示当前发布修订）”；预览不改变公开内容。
- AC-5: 显式发布会校验工作副本、生成新的不可变修订、推进修订号与 `current_revision_id`，之后公开页与公开接口才展示新内容；存在未发布修改时后台状态可观察，草稿不得泄漏到公开页。
- AC-6: `/admin/about/revisions` 可列出、查看发布快照并与当前发布比较；显式回滚创建 `source=rollback` 的新修订且不改写历史，工作副本有未发布修改时拒绝回滚。
- AC-7: 写作台“运营”导航出现“关于页”入口；编辑器明确说明身份与联系方式来自个人名片并提供跳转，不提供重复的 profile 表单。

## Result

Verified and closed by the harness close command.

## Evidence

[20260907-about-page-editor.json](../../verification/evidence/20260907-about-page-editor.json)

SHA-256: `db4b2fc60e188810a6768312aa98e9187ee0282f1b6836ad7e77b435baeda630`

Closed at 2026-09-07T16:21:18.034462+00:00.
