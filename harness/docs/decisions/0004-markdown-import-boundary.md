---
id: decision-markdown-import-boundary
level: L1
summary: Markdown 导入在落库前执行严格可判别元数据验证和批次资源限制
load_when:
  - content-import-change
  - security-change
  - architecture-decision
author: Gavin
---

# Decision 0004: Markdown import boundary

## Status

Accepted.

## Decision

Markdown front matter 是不可信输入。导入只接受文章、项目和读书笔记三个可判别、禁止未知字段的元数据模型；YAML anchor/alias 不属于可移植格式并予以拒绝。文件数、单文件字节、批次总字节、front matter 字节、结构深度和节点数都在业务处理前设硬上限。

整批文件必须先完成解析、模型验证、批内去重和数据库冲突检查，之后才能在一个数据库事务中创建草稿。导出中的生命周期字段允许通过验证以支持往返，但导入永远不恢复发布或删除状态。

## Consequences

- 畸形类型和字段拼写不会再导致 500 或静默数据丢失，而会得到稳定 4xx。
- 当前导出文档可重新导入；带未知字段或 YAML alias 的宽松第三方文档需要先规范化。
- 批次内任一文件失败时不会产生部分导入，调用方可修正后安全重试。
