---
id: spec-20260827-document-module-alignment
level: L1
summary: 使当前项目文档与现有博客功能模块一一对应，并把已退役知识孵化资料隔离为冷历史
load_when:
  - task:20260827-document-module-alignment
author: Codex
task_id: 20260827-document-module-alignment
status: active
verification_profile: release
documentation_impact: required
documentation_targets:
  - README.md
  - apps/web/README.md
  - apps/api/README.md
  - packages/contracts/README.md
  - harness/docs/product/brief.md
  - harness/docs/product/knowledge-incubator.md
  - harness/docs/architecture/boundaries.md
  - harness/docs/decisions/0006-freeze-github-source-crawler-spec.md
  - harness/docs/decisions/0007-freeze-github-discovery-ingestion-spec.md
  - harness/docs/decisions/20260814-zvec-derived-vector-index.md
  - harness/docs/decisions/20260826-retire-knowledge-incubator.md
  - harness/docs/decisions/20260827-externalize-retired-github-specs.md
  - harness/docs/reviews/2026-08-09-project-audit.md
  - harness/docs/reviews/2026-08-09-project-audit-remediation-plan.md
  - harness/docs/reviews/2026-08-15-project-audit.md
  - harness/docs/reviews/2026-08-15-project-audit-remediation-plan.md
  - harness/docs/reviews/2026-08-16-project-audit.md
  - harness/docs/reviews/2026-08-16-project-audit-remediation-plan.md
documentation_reason: 当前 L1 产品文档、应用边界、历史审计和旧自动化仍把已退役模块带入当前知识面；需要建立现行功能模块映射，并把退役资料收窄为只按历史任务加载的审计记录。
state_history:
---

# Context

当前 Web、API 与 OpenAPI 已不再注册知识孵化的页面、路由、Worker、Retrieval Service 或专属 schema，但项目文档仍存在三类漂移：

- 717 行历史需求仍作为 L1 产品文档按通用 ingestion、retrieval、article-revision 标签路由；
- 根 README、Web/API/Contracts 边界和架构基线持续把退役模块作为当前项目说明的一部分；
- 2026-08-15 的 Grok 审计工作流仍调用已删除的文件、测试和运行面，日期锁定的审计与 superseded ADR 也仍挂在通用当前任务标签上。

压缩规格、schema v2 evidence、Evolution 事件、旧 Alembic revision 与只读来源枚举承担历史完整性和数据库升级兼容，不能为了“零字符串命中”而删除。当前知识面与历史审计层必须明确分离。

# Goal

让现行产品文档只描述当前博客模块及其 Web、API、数据、契约和 Harness 所有权；将知识孵化需求压缩为同路径 L2 历史墓碑，并把相关 ADR、审计快照和修复计划收窄为只按历史任务加载的冷资料，同时移除会执行已删除模块检查的过时 Grok 工作流。

# Non-goals

- 不删除或改写压缩规格、verification evidence、Evolution 事件、Git 历史或 Alembic 升级链。
- 不删除兼容历史文章修订所需的只读 source 枚举、显示标签和迁移验证测试。
- 不恢复、重建或重新设计知识孵化、GitHub crawler/discovery、Retrieval Service、Worker、LLM 或向量索引。
- 不修改 Web/API 用户行为、数据库结构、OpenAPI 路径、部署边界或当前 Admin Login active spec。
- 不处理与本次模块文档映射无关的视觉改动、临时 QA 文件或其它未提交用户修改。

# Acceptance criteria

- AC-1: 产品基线包含当前功能模块到 Web、API/数据、契约/长期文档的明确映射，覆盖公开阅读、文章写作与修订、栏目标签与搜索、项目与读书、媒体与内容可移植性、认证与个人资料、发现输出及控制面；映射中不存在已退役模块。
- AC-2: 根 README、Web/API/Contracts 边界和架构边界只描述当前运行模块；过时 Grok 项目审计工作流被移除，不再有当前说明或可执行指令要求访问已删除的孵化页面、API、测试、Worker 或 Retrieval Service。
- AC-3: harness/docs/product/knowledge-incubator.md 保留原路径但缩减为 L2 历史墓碑，只含退役结论、恢复/审计指针和已验证历史 blob；相关 superseded ADR、退役 ADR及日期审计文档不再使用通用当前任务标签。
- AC-4: 压缩规格、evidence、Evolution 事件、Alembic 历史和兼容 source 值保持不变；生成索引、metadata、链接、历史完整性与结构检查全部通过。
- AC-5: 应用边界文档与当前页面、FastAPI router、OpenAPI 路径和仓库文件清单一致；只保留数据库升级所需的精简旧迁移警告，不把历史子系统陈述为当前功能。

# Risks

- 直接删除历史产品文档会让两份已关闭规格的 documentation target 失去当前可读入口，即使现有 history-integrity 仍可能全绿。
- 只把文档从 L1 改成 L2但保留通用 load_when，仍会在普通检索或文章修订任务中污染上下文。
- 清除所有孵化字符串会破坏 Alembic 单链升级、历史 evidence 和旧 revision source 兼容；本任务只清除当前知识面，不伪造历史。
- 修改应用 README 与 contracts README 会触发 API、Web 和 release 路由门槛；必须在隔离工作树运行完整派生 gate。

# Verification plan

- harness-integrity => AC-1, AC-2, AC-3, AC-4, AC-5
- api-lint => AC-2, AC-4, AC-5
- api-tests => AC-2, AC-4, AC-5
- web-quality => AC-1, AC-2, AC-4, AC-5
- release => AC-1, AC-2, AC-3, AC-4, AC-5
