---
id: decision-retire-knowledge-incubator
level: L2
summary: 旧子系统退役与独立只读归档的历史决策
load_when:
  - historical-architecture
  - task:20260826-retire-knowledge-incubator
author: Gavin
---

# Decision: retire the knowledge incubator

## Status

Accepted on 2026-08-26. Supersedes [Zvec derived vector index](20260814-zvec-derived-vector-index.md) as an active architecture decision.

## Context

知识孵化把摄入、异步 Worker、本地模型、Retrieval Service、第三方 LLM、草稿与发布计划耦合进个人博客。它已经具备完整闭环，但三进程拓扑、约 270 MiB 模型资产、专属依赖、数据库对象和质量矩阵成为主项目的持续负担。现有文章修订全部来自普通编辑器，没有孵化来源链或非终态任务，因此可以在一致性归档后安全退役。

## Decision

- 最终实现以标签 `incubator-final-20260826` 固定，并同步到独立私有归档 `my_blog-knowledge-incubator-archive`；归档设为只读，默认分支不继续开发。
- 退役前 SQLite 使用一致性 backup API 复制，再以 Windows DPAPI CurrentUser 加密。明文哈希、密文哈希、字节数、表计数和恢复命令记录在归档 manifest；明文数据库不进入 Git。
- 主项目删除管理入口、摄入/审计/草稿/发布计划 API、Worker、Retrieval Service、模型准备、检索基准和专属依赖。
- 普通文章继续拥有不可变 revision、栏目/标签与参考资料快照、修订列表/详情/差异/回滚、wikilink/反链和公共 FTS5 搜索；这些能力不再产生孵化任务或索引副作用。
- 旧 Alembic revision 保留，以保证历史数据库仍能沿单一链升级。新迁移 `20260826_0020` 只前向删除孵化和派生索引对象，故意不实现会伪装数据恢复能力的 downgrade。
- 恢复知识孵化不是博客回滚操作。必须先从加密备份恢复旧数据库，再检出归档标签，并在独立项目中重新完成安全、依赖和部署评审。

## Consequences

- 主应用回到 Web + API + SQLite 的两应用边界，不再需要模型、向量存储、内部检索令牌或 LLM 配置。
- 已删除的 API 和管理 URL 返回 404；OpenAPI 不再声明对应路径与 schema。
- 历史 `ArticleRevision.source = "incubator"` 仍是合法只读值，以便未来读取归档导入的核心修订，但来源链表和界面链接已删除。
- 数据库迁移的技术 downgrade 不可用；可恢复性由独立代码标签和经过实际解密、校验的数据库备份提供。

## Re-evaluate when

只有出现独立于博客发布链路、具备明确用户价值、运维预算、数据边界和长期维护者的新产品提案时才重新评估。不得以“代码仍在归档”为理由直接恢复主项目路由、表或依赖。

## Follow-up: frozen GitHub specifications

2026-08-27，两个依赖旧知识孵化运行面的 GitHub crawler/discovery 规格以“未完成并外置”的语义从博客主项目开放列表移除。它们没有经过 resume、verify 或 close，也没有被伪装成 compressed；原始 frozen 文件由独立只读归档继续保存。具体归档身份、完整性哈希和未来恢复边界见 [Externalize the retired GitHub incubator specs](20260827-externalize-retired-github-specs.md)。
