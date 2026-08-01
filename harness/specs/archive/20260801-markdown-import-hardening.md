---
id: archive-20260801-markdown-import-hardening
level: L2
summary: 为 Markdown 批量导入建立严格元数据契约与聚合资源边界
load_when:
  - task:20260801-markdown-import-hardening
task_id: 20260801-markdown-import-hardening
status: compressed
---

# 20260801-markdown-import-hardening

Deterministic compressed record. The original active spec remains in Git history.

## Goal

把 Markdown 导入视为不可信批量输入：在任何数据库写入前完成文件、总量、YAML 结构和三类元数据的严格验证；错误稳定返回 4xx，整批不产生部分草稿。

## Acceptance criteria

- 保留最多 50 文件和单文件 2 MiB 限制，并增加 10 MiB 批次总量、64 KiB front matter、结构深度和节点数上限。
- YAML anchor/alias 明确拒绝，解析错误和递归错误稳定返回 422。
- 文章、项目和读书笔记分别使用可判别的严格元数据模型；未知字段、非字符串 slug、错误列表类型、无效 URL/日期/评分均返回 422。
- 元数据模型兼容本系统当前 Markdown 导出字段，但 `status`、`published_at` 和 `deleted_at` 只验证不恢复，导入内容仍为草稿。
- 所有文件先完成解析、类型验证、批内 slug 去重和数据库冲突检查，之后才进入单一数据库事务；任一预验证或写入失败均不产生部分内容。
- 失败响应不回显完整不可信输入，文件名经过 basename 与长度约束。
- API、OpenAPI、Web、E2E、构建与 Harness 全量验证通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260801-markdown-import-hardening.json](../../verification/evidence/20260801-markdown-import-hardening.json)

Closed at 2026-08-01T16:42:59.035645+00:00.
