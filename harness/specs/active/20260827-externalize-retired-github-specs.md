---
id: spec-20260827-externalize-retired-github-specs
level: L1
summary: 将两份未完成的 GitHub 知识孵化规格从主项目开放列表迁出，并以独立只读归档保留原始基线
load_when:
  - task:20260827-externalize-retired-github-specs
author: Gavin
task_id: 20260827-externalize-retired-github-specs
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - README.md
  - harness/docs/decisions/0006-freeze-github-source-crawler-spec.md
  - harness/docs/decisions/0007-freeze-github-discovery-ingestion-spec.md
  - harness/docs/decisions/0008-harness-freeze-lifecycle.md
  - harness/docs/decisions/20260826-retire-knowledge-incubator.md
  - harness/docs/decisions/20260827-externalize-retired-github-specs.md
documentation_reason: 主项目不再保留两份冻结规格，需要用长期决策和项目入口准确记录外部归档、未完成语义与未来恢复边界。
state_history:
---

# Context

知识孵化已于 2026-08-26 从博客主项目退役，但 `20260807-github-discovery-ingestion` 与 `20260807-github-source-crawler` 仍以 frozen 状态保存在主项目 `harness/specs/active/`。它们依赖已经删除的摄入、Worker、Webhook 与跨仓库链路，不再具备在博客主项目恢复和关闭的前提。

独立私有只读归档 `my_blog-knowledge-incubator-archive` 的 `main` 已指向 `6be9a8190c57498938fe381f0676d6631fce119f`，不可变标签 `incubator-final-20260826` 解引用到源提交 `35e458e82bd62a5dc113da691ffddbcf758526ed`。两份 frozen spec 已在该快照的原路径中保存，且与主项目当前副本逐字节一致。因此本任务迁出的是主项目中的重复开放规格，不改写只读归档。

当前 Harness 生命周期没有 `cancelled` 或 `externalized` 状态；`compressed` 只表示已经验证并关闭。两份规格没有完成真实跨仓库 E2E，不能通过 resume/close 或手工压缩来伪造完成。

# Goal

在保持独立知识孵化归档及其不可变标签不变的前提下，从博客主项目开放规格列表移除两份未完成的 GitHub 孵化规格，并通过长期 ADR 明确“取消并外置、不是完成”的审计语义；同时修复 Harness 在 merge 历史中漏判原始 active spec 的路径查询，使本次变更能够通过真实的历史完整性门禁。

# Non-goals

- 不恢复或实现 GitHub crawler、discovery ingestion、Webhook、Worker 或知识孵化运行面。
- 不把两份未完成规格写入主项目 `harness/specs/archive/`，不生成 `spec.completed` 事件或 passed evidence。
- 不修改独立归档仓库、`incubator-final-20260826` 标签、加密数据库快照或 manifest。
- 不删除旧冻结 ADR、历史 evidence、压缩规格或日期锁定的审计记录。
- 不改变通用 frozen 生命周期；未来仍可对其他任务执行 freeze/resume。
- 不修改博客产品代码、API、数据模型、部署或现有 Penpot 规格。

# Acceptance criteria

- AC-1: 主项目 `harness/specs/active/` 和生成索引不再包含 `20260807-github-discovery-ingestion`、`20260807-github-source-crawler`，frozen 计数为 0；主项目不生成这两项的 compressed spec 或完成事件。
- AC-2: 新的长期 ADR 记录独立归档仓库、远端提交、不可变标签、归档内原路径、Git blob、SHA-256，以及两项“未完成、不可从博客恢复”的语义；0006、0007、0008 和知识孵化退役 ADR 明确引用该后续决策。
- AC-3: 根 README 不再把两项描述成主项目中的冻结规格，而是说明未完成设计仅由独立只读归档保存，未来恢复必须作为独立产品重新立项。
- AC-4: `history-integrity` 的 active-spec 历史查询在 merge 提交发生路径简化时仍能发现当前 HEAD 祖先中的原始规格，并有回归测试；全局 Harness 完整性检查通过。

# Risks

- 使用 Harness `close` 处理原 frozen spec 会把未完成验收误写成 completed。
- 仅删除 active 文件而不留下长期决策，会丢失取消原因、归档位置和未来恢复边界。
- 修改独立归档或不可变标签会破坏已经验证的数据与代码恢复点。
- Git 默认路径简化可能在 merge 后漏掉 side-parent 中的 active spec，形成 history-integrity 假失败。
- 当前主工作树包含无关 UI 修改；本任务必须在隔离 worktree 中完成并只合入自身提交。

# Verification plan

- harness-integrity => AC-1, AC-2, AC-3, AC-4
- harness-tests => AC-4
