---
id: sdd-policy
level: L1
summary: 风险触发、短生命周期的 Spec-Driven Development 规则
load_when:
  - behavior-change
  - api-change
  - data-change
  - security-change
  - cross-stack-change
author: Gavin
---

# SDD policy

Spec 是高风险改动的临时协调物，不是永久文档。

以下变化必须建立 spec：用户可见行为、API、数据模型、认证或存储边界、跨端契约、架构、依赖或质量门槛。错别字、纯格式、索引修复和确定无行为变化的机械重构可以跳过。

创建 spec 前先执行 intake 与 specify workflow；实现后必须通过 VDD checks。关闭过程生成压缩归档，并要求原始 active spec 已存在于 Git 历史。验证范围由独立影响计划和细粒度源码/依赖归属决定；spec 的 cases 与所选集合必须一致。未知归属或依赖判断缺失阻断，不按目录升级全量。release 只用于明确发布任务。包门禁不得独占多条验收标准。

每个非冻结 active spec 都必须声明文档影响。`documentation_impact: required` 需要列出项目相对、非生成型的 Markdown 目标，并说明原因；这些目标必须在 spec 首次进入 Git 的提交之后发生已提交变更。`documentation_impact: none` 不列目标，但仍需写明没有 durable 文档影响的依据。task verify 在产品 gate 之前检查该契约，close 会按当前 HEAD 与 evidence 再次复核。冻结 spec 保持原契约，不要求迁移字段；恢复为 active 前才需要满足当前规则。
