---
id: archive-20260811-json-object-audit-prompt
level: L2
summary: 为 json_object 审计请求显式发送结构契约与真实证据示例
load_when:
  - task:20260811-json-object-audit-prompt
author: Codex
task_id: 20260811-json-object-audit-prompt
status: compressed
state_history:
---

# 20260811-json-object-audit-prompt

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在 `json_object` 审计请求中显式发送完整 `AuditResult` JSON Schema，并给出引用本次真实资料证据 ID 的最小结构示例，使模型能够生成可解析、可验证的结果。

## Acceptance criteria

- `json_object` 审计消息包含完整 `AuditResult` JSON Schema 和所有必填字段的最小 JSON 示例。
- 示例的 `evidence_chunk_ids` 使用本次计划中真实的首个 `src:` 证据 ID，不构造虚假或越权引用。
- `json_schema` 审计消息不重复嵌入 Schema。
- Token 估算在两种模式下都只计算一次 Schema，并保留 `schema_tokens` 观测字段。
- 请求指纹随消息内容变化，现有外发确认、尝试记录和本地业务校验保持不变。

## Result

Verified and closed by the harness close command.

## Evidence

[20260811-json-object-audit-prompt.json](../../verification/evidence/20260811-json-object-audit-prompt.json)

Closed at 2026-08-12T02:23:07.266046+00:00.
