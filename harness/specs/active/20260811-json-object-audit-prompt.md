---
id: spec-20260811-json-object-audit-prompt
level: L1
summary: 为 json_object 审计请求显式发送结构契约与真实证据示例
load_when:
  - task:20260811-json-object-audit-prompt
author: Codex
task_id: 20260811-json-object-audit-prompt
status: active
state_history:
---

# Context

DeepSeek 的 `json_object` 模式只保证返回合法 JSON。当前审计提示词声称存在“给定 JSON Schema”，但实际消息没有携带 Schema 或输出示例；最近一次请求虽为 HTTP 200，仍因本地结构化校验失败而终止。

# Goal

在 `json_object` 审计请求中显式发送完整 `AuditResult` JSON Schema，并给出引用本次真实资料证据 ID 的最小结构示例，使模型能够生成可解析、可验证的结果。

# Non-goals

不改变 `json_schema` 请求；不放宽 Pydantic 或证据 ID 业务校验；不自动重试失败审计；不修改供应商、模型、外发确认、任务幂等或 Token 账本语义；不修复孵化草稿生成提示词。

# Acceptance criteria

- `json_object` 审计消息包含完整 `AuditResult` JSON Schema 和所有必填字段的最小 JSON 示例。
- 示例的 `evidence_chunk_ids` 使用本次计划中真实的首个 `src:` 证据 ID，不构造虚假或越权引用。
- `json_schema` 审计消息不重复嵌入 Schema。
- Token 估算在两种模式下都只计算一次 Schema，并保留 `schema_tokens` 观测字段。
- 请求指纹随消息内容变化，现有外发确认、尝试记录和本地业务校验保持不变。

# Risks

嵌入 Schema 会增加输入 Token；结构示例可能对角色选择产生锚定偏差；若重复计算 Schema 会错误拒绝本可容纳的请求。示例必须明确仅展示结构，并使用 `new_branch` 的中性形态。

# Verification plan

先补充提示词与调用构建测试，确认当前 `json_object` 缺少 Schema；实现条件化 Schema/示例和单次 Token 估算；运行 LLM prompt、audit、worker、config 测试及 Ruff；最后重新执行一次现有失败审计，由用户显式确认外发后观察结果，不由自动测试真实调用第三方。
