---
id: archive-20260814-public-knowledge-links
level: L2
summary: 让已发布文章、项目和书摘通过 wikilink 与可编辑参考资料形成公开反链，而不是只靠栏目标签邻近
load_when:
  - task:20260814-public-knowledge-links
author: Gavin
task_id: 20260814-public-knowledge-links
status: compressed
documentation_impact: required
documentation_targets:
  - harness/docs/product/brief.md
  - apps/web/README.md
  - apps/api/README.md
  - packages/contracts/README.md
documentation_reason: 公开内容模型增加站内知识链接与反链，需要同步产品基线和三端边界说明。
state_history:
---

# 20260814-public-knowledge-links

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在已发布且未删除的文章、项目和书摘之间建立可追溯的公开知识链接：正文支持 `[[wikilink]]`，文章工作副本可编辑参考资料并随发布修订快照，目标页展示稳定反链。草稿、未发布修改和已删除内容不得进入公开关系。

## Acceptance criteria

- AC-1: 文章、项目和书摘的 Markdown 支持 `[[slug]]`、`[[article:slug]]` / `[[notes:slug]]`、`[[project:slug]]` / `[[projects:slug]]`、`[[book:slug]]` / `[[books:slug]]`、完整站内路径，以及 `[[token|显示名]]`。解析跳过围栏代码和行内代码。唯一已发布目标渲染为站内链接；无法唯一解析时显示未链接文本，不生成死链。
- AC-2: 文章管理响应与 PATCH 携带有序 `references`。每项是 `external`（HTTPS URL + 标题）或 `internal`（已发布未删除的文章/项目/书摘 + 标题）。自动保存只更新工作副本；显式发布把工作副本快照到当前发布修订的 `public_references`，并计入 `has_unpublished_changes` 与内容哈希。
- AC-3: 文章、项目或书摘成功发布、回滚、软删除或恢复后，系统按当前发布正文中的已解析 wikilink 与已启用参考资料重建该对象的出链索引。同一对来源-目标只产生一条公开反链；自链忽略。
- AC-4: 公开文章上下文、项目详情和书摘详情返回最多 20 条反链，按发布时间与 ID 稳定降序，只含已发布未删除来源，卡片使用当前发布标题/摘要/路径。对应公开页在有数据时展示“链入”区块，空结果不渲染该区块。
- AC-5: 工作副本中的 wikilink 或参考资料在发布前不影响公开页。目标未发布、已删除或 slug 冲突时，公开渲染为未解析，且不出现在任何反链列表。恢复已发布对象后，其出链与作为目标的入链重新可见。
- AC-6: 孵化发布和回滚继续写入或复制修订级 `public_references`；这些参考资料若指向站内公开路径，同样进入反链。编辑器发布不得丢弃仍存在于工作副本中的参考资料。
- AC-7: OpenAPI 快照、Web 类型、API 测试、公开/编辑器 E2E 与产品边界文档同步新契约；长期文档不链接本 active spec。

## Result

Verified and closed by the harness close command.

## Evidence

[20260814-public-knowledge-links.json](../../verification/evidence/20260814-public-knowledge-links.json)

Closed at 2026-08-15T08:57:29.693045+00:00.
