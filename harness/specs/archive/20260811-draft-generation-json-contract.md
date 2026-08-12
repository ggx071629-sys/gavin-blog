---
id: archive-20260811-draft-generation-json-contract
level: L2
summary: 修复 json_object 草稿生成契约、失败重试与错误发布链路
load_when:
  - task:20260811-draft-generation-json-contract
author: Codex
task_id: 20260811-draft-generation-json-contract
status: compressed
state_history:
---

# 20260811-draft-generation-json-contract

Deterministic compressed record. The original active spec remains in Git history.

## Goal

为 `json_object` 草稿生成请求显式提供完整结构契约和当前角色的最小示例；让提示词版本升级后的新计划能够复用逻辑草稿并安全重试失败生成；移除没有真实发布计划关系支持的误导链接。

## Acceptance criteria

- `json_object` 草稿生成消息包含完整 `DraftGenerationResult` JSON Schema 和与当前角色一致的最小示例。
- supplement 示例使用本计划真实锚点 ID；new_branch 示例不构造虚假分类或标签 ID。
- `json_schema` 模式不重复嵌入 Schema；两种模式的 Token 估算都只计算一次正确的草稿 Schema。
- 提示词版本升级后，不复用旧版本已确认计划；新计划确认时可将同一失败逻辑草稿重新排队，保留旧失败版本并创建独立任务。
- 草稿详情页不再把 `DraftDetail.plan_id` 链接到发布计划页面；失败草稿提供“重试生成”入口并创建当前提示词版本的新计划，真实发布仍只由“确认并发布”创建计划后跳转。

## Result

Verified and closed by the harness close command.

## Evidence

[20260811-draft-generation-json-contract.json](../../verification/evidence/20260811-draft-generation-json-contract.json)

Closed at 2026-08-12T02:22:54.156804+00:00.
