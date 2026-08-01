---
id: spec-20260801-markdown-import-hardening
level: L1
summary: 为 Markdown 批量导入建立严格元数据契约与聚合资源边界
load_when:
  - task:20260801-markdown-import-hardening
task_id: 20260801-markdown-import-hardening
status: verified
---

# Markdown import hardening

## Context

导入端点虽然使用 `yaml.safe_load`、单文件 2 MiB 和最多 50 文件限制，但 front matter 仍作为任意字典流入业务逻辑。列表字段传入字符串会被逐字符处理，slug 传入列表会在去重集合中触发 500；未知字段静默忽略。50 个文件还可累计到约 100 MiB，YAML alias 与过深结构缺少显式边界。

## Goal

把 Markdown 导入视为不可信批量输入：在任何数据库写入前完成文件、总量、YAML 结构和三类元数据的严格验证；错误稳定返回 4xx，整批不产生部分草稿。

## Non-goals

- 不改变导入结果仍强制创建草稿的产品行为。
- 不恢复导出文件中的发布、删除或版本状态。
- 不支持 YAML anchor/alias、高级自定义标签或宽松字段别名。
- 不改变 Markdown 正文语法、ZIP 导出格式或导入响应模型。

## Acceptance criteria

- 保留最多 50 文件和单文件 2 MiB 限制，并增加 10 MiB 批次总量、64 KiB front matter、结构深度和节点数上限。
- YAML anchor/alias 明确拒绝，解析错误和递归错误稳定返回 422。
- 文章、项目和读书笔记分别使用可判别的严格元数据模型；未知字段、非字符串 slug、错误列表类型、无效 URL/日期/评分均返回 422。
- 元数据模型兼容本系统当前 Markdown 导出字段，但 `status`、`published_at` 和 `deleted_at` 只验证不恢复，导入内容仍为草稿。
- 所有文件先完成解析、类型验证、批内 slug 去重和数据库冲突检查，之后才进入单一数据库事务；任一预验证或写入失败均不产生部分内容。
- 失败响应不回显完整不可信输入，文件名经过 basename 与长度约束。
- API、OpenAPI、Web、E2E、构建与 Harness 全量验证通过。

## Risks

- 禁止未知字段会使手工编写的宽松旧文档失败，但能避免拼写错误静默丢失；当前导出字段全部纳入模型。
- 批次总量限制降低一次导入容量；10 MiB 仍足以容纳多个长文档，超大迁移应拆批。
- YAML 日期和时间可能被解析器构造成 Python 对象，也可能保留字符串；Pydantic 契约必须同时正确验证当前导出格式。

## Verification plan

- Pytest 覆盖不可哈希 slug、字符串列表、未知字段、YAML alias、front matter 限制和聚合字节限制，均断言 4xx 而非 500。
- 混合有效/无效批次验证数据库仍为空；当前导出再导入和成功关联警告行为保持通过。
- 执行 API 全量 Pytest、Ruff、OpenAPI 哈希比较、Web Vitest、TypeScript no-emit、隔离 E2E 与 Nuxt 构建。
- 刷新索引并运行 `python -m tools.harness verify 20260801-markdown-import-hardening`。

## Implementation record

- 为文章、项目和读书笔记建立可判别的严格 Pydantic 元数据模型，禁止未知字段并验证 slug、关联 slug 列表、URL、日期、评分及生命周期时间类型。
- 导入新增 10 MiB 批次、64 KiB front matter、8 层结构和 200 节点上限；保留 50 文件和单文件 2 MiB 限制，YAML anchor/alias 明确返回 422。
- 文件名先取 basename 并限制 255 字符；验证错误只返回文件级通用说明，不回显完整不可信内容。
- 全部文件先完成解析、模型验证、批内去重和数据库冲突检查，之后才进入单事务写入；生命周期字段只验证，导入仍强制生成草稿。
- 内容可移植性与导入测试共 10 项，覆盖原先会触发 500 的不可哈希 slug、字符串列表、未知字段、数字时间戳、YAML alias、批次/front matter/复杂度上限及混合批次零写入。
- API 全量 40 项、Web 14 项、Playwright 3 项、Ruff、TypeScript no-emit、Nuxt 构建及 OpenAPI 同步均通过；E2E 临时目录无残留。
- Spec 保留在 active 目录：仓库仍无 Git HEAD，无法满足 deterministic close 的历史前置条件。
