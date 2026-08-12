---
id: spec-20260811-draft-generation-json-contract
level: L1
summary: 修复 json_object 草稿生成契约、失败重试与错误发布链路
load_when:
  - task:20260811-draft-generation-json-contract
author: Codex
task_id: 20260811-draft-generation-json-contract
status: active
state_history:
---

# Context

草稿生成调用 DeepSeek 返回 HTTP 200，但 `json_object` 请求消息没有携带 `DraftGenerationResult` Schema 或角色示例，最终以 `DRAFT_RESULT_INVALID` 失败。失败草稿不能进入发布流程，且当前草稿详情页错误地把草稿生成计划 `plan_id` 链接为发布计划 ID，导致跳转到不存在的 `/publish-plans/{id}` 并返回 404。现有已确认的 `generation-v1` 计划还会被重复复用，使提示词升级后无法为失败草稿创建新的生成任务。

# Goal

为 `json_object` 草稿生成请求显式提供完整结构契约和当前角色的最小示例；让提示词版本升级后的新计划能够复用逻辑草稿并安全重试失败生成；移除没有真实发布计划关系支持的误导链接。

# Non-goals

不放宽 Pydantic、锚点、证据或分类 ID 校验；不自动调用第三方 LLM；不自动创建或确认发布计划；不修改数据库表；不把草稿生成计划 ID 解释为发布计划 ID；不清理历史失败版本或 Token 账本。

# Acceptance criteria

- `json_object` 草稿生成消息包含完整 `DraftGenerationResult` JSON Schema 和与当前角色一致的最小示例。
- supplement 示例使用本计划真实锚点 ID；new_branch 示例不构造虚假分类或标签 ID。
- `json_schema` 模式不重复嵌入 Schema；两种模式的 Token 估算都只计算一次正确的草稿 Schema。
- 提示词版本升级后，不复用旧版本已确认计划；新计划确认时可将同一失败逻辑草稿重新排队，保留旧失败版本并创建独立任务。
- 草稿详情页不再把 `DraftDetail.plan_id` 链接到发布计划页面；失败草稿提供“重试生成”入口并创建当前提示词版本的新计划，真实发布仍只由“确认并发布”创建计划后跳转。

# Risks

嵌入 Schema 会增加输入 Token；角色示例会产生锚定偏差，因此示例必须标明只展示结构。失败草稿重排队必须创建新幂等任务，不能重放旧失败任务或覆盖旧模型版本。

# Verification plan

先增加提示词、真实 `json_object` Worker 请求、失败草稿重试和前端链路回归测试并确认旧实现失败；实施最小修复；运行 Draft/LLM/Publishing 相关测试、Web 类型检查及全量 API 回归，最后执行 Harness verify。
