---
id: product-knowledge-incubator-history
level: L2
summary: 已从当前产品移除的旧子系统历史审计入口
load_when:
  - historical-product
  - task:20260814-zvec-vector-index
  - task:20260826-retire-knowledge-incubator
  - task:20260827-externalize-retired-github-specs
author: Gavin
---

# 旧子系统历史入口

此路径仅为已关闭规格的 documentation target 保留，不是当前产品需求、待办、恢复指南或运行边界。当前功能范围只以 [产品基线](brief.md) 的模块表为准。

完整历史设计不再参与 L1 路由。需要审计既有 evidence 时，可直接读取其中固定的 Git blob：

- 2026-08-14 验证版本：`8bd5a4b666b7d28e7af9dd4028033045317b73aa`
- 2026-08-26 最终文档目标：`651f60e8ea66bcebdf005388b04ac02bd833c009`

可用 `git cat-file blob <sha>` 只读恢复对应版本。退役原因、归档身份和历史任务处置分别记录在 [退役决策](../decisions/20260826-retire-knowledge-incubator.md) 与 [外置任务决策](../decisions/20260827-externalize-retired-github-specs.md)。

旧 Alembic revision、压缩规格、evidence、Evolution 事件和历史文章修订来源值仍用于升级兼容与审计完整性；它们不表示主项目仍提供对应功能。
