---
id: decision-externalize-retired-github-specs
level: L2
summary: 两份未完成旧任务外置到独立只读归档的历史决策
load_when:
  - historical-architecture
  - task:20260827-externalize-retired-github-specs
  - task:20260807-github-discovery-ingestion
  - task:20260807-github-source-crawler
author: Gavin
---

# Decision: externalize the retired GitHub incubator specs

## Status

Accepted on 2026-08-27. Supersedes the task-specific operating instructions in [Decision 0006](0006-freeze-github-source-crawler-spec.md) and [Decision 0007](0007-freeze-github-discovery-ingestion-spec.md), and amends the two-task migration note in [Decision 0008](0008-harness-freeze-lifecycle.md). The general Harness frozen lifecycle remains accepted.

## Context

`20260807-github-source-crawler` 与 `20260807-github-discovery-ingestion` 因缺少真实跨仓库 E2E 一直保持 frozen，从未完成产品验收。知识孵化运行面随后于 2026-08-26 从博客主项目退役，两个任务依赖的摄入、Worker、Webhook 和待处理池边界已不存在，继续把它们留在博客的开放规格列表会错误暗示仍可恢复执行。

独立私有只读归档 [my_blog-knowledge-incubator-archive](https://github.com/ggx071629-sys/my_blog-knowledge-incubator-archive) 已保存完整退役前 monorepo。2026-08-27 的只读远端核验确认：

- 归档 `main`：`6be9a8190c57498938fe381f0676d6631fce119f`
- 不可变标签：`incubator-final-20260826`，解引用到 `35e458e82bd62a5dc113da691ffddbcf758526ed`

两份规格在归档中继续保留 frozen 元数据和原始相对链接：

| Task | 归档内路径 | Git blob | SHA-256 |
| --- | --- | --- | --- |
| `20260807-github-discovery-ingestion` | `harness/specs/active/20260807-github-discovery-ingestion.md` | `9c2f76fa8bb6c667abeebf2235eeaec6cb27a1a2` | `fac70181a2fdb235e310260d4a532da9c869a2d078f19fde647bc597bf5a1f17` |
| `20260807-github-source-crawler` | `harness/specs/active/20260807-github-source-crawler.md` | `86b9163176fb3ab2fea3a8915c1b0084c79a9590` | `95c504434c96d6aa1c79938fd6739f212414fb28c2e1180ad32f24c1231eec14` |

## Decision

- 从博客主项目 `harness/specs/active/` 删除这两份重复规格，并由生成索引移除其开放任务条目。
- 不执行 `resume`、`verify` 或 `close`，不在主项目 `harness/specs/archive/` 创建 compressed 记录，也不生成 `spec.completed` 事件。外置表示取消当前产品方向，不表示验收完成。
- 保留主项目 Git 历史、旧冻结 ADR、压缩规格中的历史陈述和 schema v1 evidence；这些记录只证明当时的结构检查与冻结背景，不升级为产品完成证据。
- 独立归档中的文件保持原路径、原字节和 frozen 状态；不修改归档 `main`、不可变标签、加密数据快照或 manifest。
- 博客主项目不再允许通过旧 task ID 恢复这两项工作。未来若重新考虑 GitHub discovery/crawler，必须作为独立于博客知识孵化发布链路的新产品建立新的 ADR、spec、数据边界和跨仓库验证计划。

## Consequences

- 本次清理规格关闭后，博客主项目规格索引为 9 active、0 frozen；独立归档仍保留两份未完成设计的完整审计基线。
- Decision 0006/0007 的冻结原因仍可用于历史解释，但其中要求保留在主项目 active 目录及后续 resume/close 的指令不再有效。
- Decision 0008 的通用 frozen 生命周期不变；本次是产品退役后的显式外置决策，不新增通用 `cancelled` 或 `externalized` 状态。
- 日期锁定的历史审计、旧 evidence 和压缩规格中的路径引用不回写，以免篡改当时证据。

## Re-evaluate when

只有出现独立产品提案，并明确用户价值、所有者、运维预算、数据来源许可、GitHub 权限、跨仓库边界和真实 E2E 环境时才重新评估。代码仍存在于只读归档不是恢复理由。
