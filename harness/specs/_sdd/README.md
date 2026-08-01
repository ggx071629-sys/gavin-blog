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

创建 spec 前先执行 intake 与 specify workflow；实现后必须通过 VDD checks。关闭过程生成压缩归档，并要求原始 active spec 已存在于 Git 历史。

