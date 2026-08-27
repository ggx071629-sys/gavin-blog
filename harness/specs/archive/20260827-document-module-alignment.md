---
id: archive-20260827-document-module-alignment
level: L2
summary: 使当前项目文档与现有博客功能模块一一对应，并把已退役知识孵化资料隔离为冷历史
load_when:
  - task:20260827-document-module-alignment
author: Codex
task_id: 20260827-document-module-alignment
status: compressed
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
  - harness/docs/decisions/0008-harness-freeze-lifecycle.md
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

# 20260827-document-module-alignment

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让现行产品文档只描述当前博客模块及其 Web、API、数据、契约和 Harness 所有权；将知识孵化需求压缩为同路径 L2 历史墓碑，并把相关 ADR、审计快照和修复计划收窄为只按历史任务加载的冷资料，同时移除会执行已删除模块检查的过时 Grok 工作流。保持 E2E 默认端口不变，但允许隔离验证显式覆盖 Web 端口，避免复用或终止主工作区服务。

## Acceptance criteria

- AC-1: 产品基线包含当前功能模块到 Web、API/数据、契约/长期文档的明确映射，覆盖公开阅读、文章写作与修订、栏目标签与搜索、项目与读书、媒体与内容可移植性、认证与个人资料、发现输出及控制面；映射中不存在已退役模块。
- AC-2: 根 README、Web/API/Contracts 边界和架构边界只描述当前运行模块；过时 Grok 项目审计工作流被移除，不再有当前说明或可执行指令要求访问已删除的孵化页面、API、测试、Worker 或 Retrieval Service。
- AC-3: harness/docs/product/knowledge-incubator.md 保留原路径但缩减为 L2 历史墓碑，只含退役结论、恢复/审计指针和已验证历史 blob；相关 superseded ADR、退役 ADR及日期审计文档不再使用通用当前任务标签。
- AC-4: 压缩规格、evidence、Evolution 事件、Alembic 历史和兼容 source 值保持不变；生成索引、metadata、链接、历史完整性与结构检查全部通过。
- AC-5: 应用边界文档与当前页面、FastAPI router、OpenAPI 路径和仓库文件清单一致；只保留数据库升级所需的精简旧迁移警告，不把历史子系统陈述为当前功能；核心 E2E 可在不复用或终止已有服务的前提下覆盖 Web 端口。

## Result

Verified and closed by the harness close command.

## Evidence

[20260827-document-module-alignment.json](../../verification/evidence/20260827-document-module-alignment.json)

Closed at 2026-08-27T17:09:27.230444+00:00.
