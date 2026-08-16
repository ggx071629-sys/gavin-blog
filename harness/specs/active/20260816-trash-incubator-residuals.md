---
id: spec-20260816-trash-incubator-residuals
level: L1
summary: 已发布文章可永久删除，孵化草稿/发布计划失败可恢复，预览与计数不再撒谎
load_when:
  - task:20260816-trash-incubator-residuals
author: Gavin
task_id: 20260816-trash-incubator-residuals
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
  - apps/api/README.md
documentation_reason: 永久删除级联、发布计划确认可恢复、预览横幅与公开计数都是写作台/公开契约。
state_history:
---

# Context

2026-08-16 审计 AUD26-024/027/029/030/033/035/036：已发布文章永久删除因修订 RESTRICT 409 且回收站无反馈；草稿详情加载失败画成空壳；重构预览无视采用标题/摘要旗标；发布计划先提交 `confirmed` 再执行，崩溃后不能恢复；已发布预览仍写未公开草稿；项目 JSON-LD `url` 是相对路径；「全部文章」漏计未分类。

# Goal

回收站永久删除已发布文章时清理修订、索引指针、孵化来源链和项目关联并成功。删除/恢复失败在回收站可见。草稿详情加载失败走失败分类。重构预览在旗标为假时对比当前发布修订的标题/摘要。已确认但未执行完的发布计划再次确认会继续执行。已发布文章预览不再写成未公开草稿。项目 JSON-LD 使用绝对 URL。「全部文章」计入未分类已发布文章。

# Non-goals

- 不改公开栏目读修订或文章发布 version（第二、三批已关）。
- 不改两条 GitHub frozen spec。
- 不新增 Alembic 迁移或改生产/CI/存储拓扑。
- 不改发布资格判定、批量门槛或回滚语义。

# Acceptance criteria

- AC-1: 已发布文章进入回收站后 `DELETE /api/v1/admin/trash/article/{id}` 返回 204；公开路径 404，修订与检索指针不再挡住删除。
- AC-2: 回收站恢复/永久删除失败写入可见错误，不得只停在确认框之后无反馈。
- AC-3: `drafts/[id].vue` 对详情加载调用 `useApiFailure`；加载失败不得只显示「草稿 #id」空壳。
- AC-4: 重构草稿预览在 `use_suggested_title`/`use_suggested_summary` 为假时，`title_diff`/`summary_diff` 的 after 使用当前目标修订标题/摘要，不得用建议文本。
- AC-5: `POST /publish-plans/{id}/confirm` 在计划已是 `confirmed` 或 `partially_published` 且仍有未执行项时继续执行；已成功项不重复发布。
- AC-6: 已发布文章预览横幅不得写「未公开」或「草稿预览，不会出现在公开站点」。
- AC-7: 项目详情 JSON-LD `url` 是基于站点 URL 的绝对地址。
- AC-8: 公开 `/articles`「全部文章」数字等于已发布且未删除文章总数，含未分类。
- AC-9: `apps/api/README.md` 与 `apps/web/README.md` 写明永久删除级联、发布计划确认可恢复、预览与计数语义。

# Risks

永久删除会拆掉孵化来源链行；这是操作者显式确认后的不可恢复清理，与产品承诺一致。项目修订快照里的 article_id 仍是非外键整数，不随删除失效。

# Verification plan

- api-lint => AC-1, AC-4, AC-5, AC-8, AC-9
- api-tests => AC-1, AC-4, AC-5, AC-8
- web-quality => AC-2, AC-3, AC-6, AC-7, AC-8, AC-9
