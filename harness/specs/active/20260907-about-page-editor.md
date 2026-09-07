---
id: spec-20260907-about-page-editor
level: L1
summary: 为写作台增加关于页内容编辑器，以工作副本与不可变发布修订管理 About 页专属文案
load_when:
  - task:20260907-about-page-editor
author: Codex
task_id: 20260907-about-page-editor
status: active
verification_profile: focused
planned_modules:
  - M11
documentation_impact: required
documentation_targets:
  - README.md
  - apps/web/README.md
  - apps/api/README.md
  - harness/docs/product/brief.md
documentation_reason: 新增产品模块、公开 About 数据源与管理发布生命周期，需要同步项目边界与模块映射文档。
state_history:
---
# Context

公开 `/about` 目前把姓名、头像、技能等身份资料读自 `/profile`，把引言读自 `profile.bio`，并把能力领域、最近在做、写作范围、网站说明与技术栈写死在 `apps/web/pages/about.vue` 中；管理员只能改个人名片，无法在不改代码的情况下维护 About 专属文案。

仓库已有成熟的文章/项目/读书工作副本模型：`PATCH` 只改工作副本，`POST publish` 创建不可变发布修订，公开读取只解析 `current_revision`。About 页内容需要同一套发布纪律，而不是再做一份“保存即公开”的配置表。

# Goal

在写作台提供 `/admin/about` 关于页编辑器，使管理员能编辑引言（与 `profile.bio` 解耦）、能力领域、最近在做、写作范围、网站说明与技术栈；编辑内容先保存在工作副本，预览确认后发布为不可变修订，公开 `/about` 只展示当前发布修订，并保留发布历史与回滚。

# Non-goals

- 不把姓名、头像、定位、技能、城市、邮箱、GitHub、个人网页、简历等 `profile` 字段复制进 About 内容模型或编辑器。
- 不编辑区块编号、装饰性英文标签、联系方式卡片与 RSS 等设计/派生展示。
- 不提供自由 URL 形式的“最近在做”目标；只允许站内文章/项目/读书页枚举。
- 不把 About 内容加入问答 RAG 语料、FTS5 或搜索索引。
- 不做通用 CMS、任意区块排序/显隐或草稿回收站。
- 不修改首页名片对 `profile.bio` 的现有读取与展示。

# Acceptance criteria

- AC-1: 升级或新建数据库后自动存在一个已发布修订 #1，工作副本与公开内容都等于当前 About 页面文案；`statement` 为独立字段，改 `profile.bio` 不会改变已发布引言。
- AC-2: 公开 `GET /about-page` 只返回当前发布修订中的 `statement`、`capabilities`、`now`、`editorial`、`site`，不返回草稿、`version` 冲突细节或任何未发布修改。
- AC-3: 管理员可在 `/admin/about` 编辑五块 About 专属内容，`PATCH` 持久化工作副本并推进乐观锁；保存期间公开页保持当前发布内容，版本冲突返回 409 且不覆盖。
- AC-4: `/admin/about/preview` 用已保存的工作副本渲染 About 展示区，并明确提示“草稿预览”或“工作副本预览（公开站仍显示当前发布修订）”；预览不改变公开内容。
- AC-5: 显式发布会校验工作副本、生成新的不可变修订、推进修订号与 `current_revision_id`，之后公开页与公开接口才展示新内容；存在未发布修改时后台状态可观察，草稿不得泄漏到公开页。
- AC-6: `/admin/about/revisions` 可列出、查看发布快照并与当前发布比较；显式回滚创建 `source=rollback` 的新修订且不改写历史，工作副本有未发布修改时拒绝回滚。
- AC-7: 写作台“运营”导航出现“关于页”入口；编辑器明确说明身份与联系方式来自个人名片并提供跳转，不提供重复的 profile 表单。

# Risks

- About 展示结构与 v2 视觉改动重叠，实现必须保持当前视觉基线并逐步把硬编码常量迁移为数据，防止上线后公开内容突变。
- SQLite 迁移需要兼容既有数据库链；初始种子内容必须与迁移前公开文案一致，引言解耦的一次性拷贝不得改变可见输出。
- 发布语义若与文章实现不一致，会造成“保存即公开”或草稿泄漏；必须复用版本号、修订指针与工作副本哈希判断。
- 新模块 M11 需要进入产品基线、模块验证合同与影响归属；验收 case 若无精确测试引用与叶子 gate，task verify 将失败。
- OpenAPI 快照与 Web 手写类型必须同步，否则 release gate 的契约一致性会失败。

# Verification plan

## Verification cases

- AC-1 => M11-MIGRATION-01
- AC-2 => M11-PUBLIC-01
- AC-3 => M11-WORKING-COPY-01
- AC-4 => M11-PREVIEW-01
- AC-5 => M11-PUBLISH-01
- AC-6 => M11-HISTORY-01
- AC-7 => M11-ADMIN-NAV-01

## Gates

- api-tests => AC-1, AC-2, AC-3, AC-5, AC-6
- e2e => AC-2, AC-3, AC-4, AC-5, AC-6, AC-7
- web-quality => AC-7
- harness-integrity => AC-7
