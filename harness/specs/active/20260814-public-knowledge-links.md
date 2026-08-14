---
id: spec-20260814-public-knowledge-links
level: L1
summary: 让已发布文章、项目和书摘通过 wikilink 与可编辑参考资料形成公开反链，而不是只靠栏目标签邻近
load_when:
  - task:20260814-public-knowledge-links
author: Gavin
task_id: 20260814-public-knowledge-links
status: active
verification_profile: release
verification_escalation: 公开契约、管理编辑器和三类阅读页同时变化，必须用 release 证明 OpenAPI 快照与全栈合同一致。
documentation_impact: required
documentation_targets:
  - harness/docs/product/brief.md
  - apps/web/README.md
  - apps/api/README.md
  - packages/contracts/README.md
documentation_reason: 公开内容模型增加站内知识链接与反链，需要同步产品基线和三端边界说明。
state_history:
---

# Context

公开阅读已经有栏目/标签相关文章、上一篇/下一篇，以及孵化发布写入的 `references`。普通文章编辑器不能维护参考资料；正文里的站内指向不会被解析，目标页也不显示“谁链到了我”。项目与书摘详情同样看不到入链。本地不上公网，本任务只补知识关系，不做系列、备份、写作台效率或部署。

# Goal

在已发布且未删除的文章、项目和书摘之间建立可追溯的公开知识链接：正文支持 `[[wikilink]]`，文章工作副本可编辑参考资料并随发布修订快照，目标页展示稳定反链。草稿、未发布修改和已删除内容不得进入公开关系。

# Non-goals

- 不实现系列、置顶、知识图谱、归档混排或栏目/标签独立资源页。
- 不改 RSS、OG、分享图、搜索高亮、评论、统计或部署拓扑。
- 不为项目或书摘增加手动参考资料编辑器。
- 不在正文里自动插入反向 wikilink，不引入 Obsidian 同步或新的公开注册入口。
- 不把孵化检索语料扩大到项目、书摘或草稿。

# Acceptance criteria

- AC-1: 文章、项目和书摘的 Markdown 支持 `[[slug]]`、`[[article:slug]]` / `[[notes:slug]]`、`[[project:slug]]` / `[[projects:slug]]`、`[[book:slug]]` / `[[books:slug]]`、完整站内路径，以及 `[[token|显示名]]`。解析跳过围栏代码和行内代码。唯一已发布目标渲染为站内链接；无法唯一解析时显示未链接文本，不生成死链。
- AC-2: 文章管理响应与 PATCH 携带有序 `references`。每项是 `external`（HTTPS URL + 标题）或 `internal`（已发布未删除的文章/项目/书摘 + 标题）。自动保存只更新工作副本；显式发布把工作副本快照到当前发布修订的 `public_references`，并计入 `has_unpublished_changes` 与内容哈希。
- AC-3: 文章、项目或书摘成功发布、回滚、软删除或恢复后，系统按当前发布正文中的已解析 wikilink 与已启用参考资料重建该对象的出链索引。同一对来源-目标只产生一条公开反链；自链忽略。
- AC-4: 公开文章上下文、项目详情和书摘详情返回最多 20 条反链，按发布时间与 ID 稳定降序，只含已发布未删除来源，卡片使用当前发布标题/摘要/路径。对应公开页在有数据时展示“链入”区块，空结果不渲染该区块。
- AC-5: 工作副本中的 wikilink 或参考资料在发布前不影响公开页。目标未发布、已删除或 slug 冲突时，公开渲染为未解析，且不出现在任何反链列表。恢复已发布对象后，其出链与作为目标的入链重新可见。
- AC-6: 孵化发布和回滚继续写入或复制修订级 `public_references`；这些参考资料若指向站内公开路径，同样进入反链。编辑器发布不得丢弃仍存在于工作副本中的参考资料。
- AC-7: OpenAPI 快照、Web 类型、API 测试、公开/编辑器 E2E 与产品边界文档同步新契约；长期文档不链接本 active spec。

# Risks

- 在正文与参考资料两处同时建链可能重复计数；必须以（来源，目标）去重，而不是按 token 去重。
- 裸 `[[slug]]` 在文章/项目/书摘之间可能冲突；冲突必须视为未解析，不能 silently 选第一个。
- 修订哈希若漏掉工作副本参考资料，会让“有未发布修改”与公开快照不一致。
- 公开列表若预加载全部反链来源正文，会放大分页查询；反链必须走索引表并限制 20 条。

# Verification plan

- api-lint => AC-1, AC-2, AC-3, AC-5
- api-tests => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6
- web-quality => AC-1, AC-2, AC-4, AC-7
- e2e => AC-1, AC-2, AC-4, AC-5
- harness-integrity => AC-7
- release => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7
