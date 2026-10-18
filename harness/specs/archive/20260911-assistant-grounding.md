---
id: archive-20260911-assistant-grounding
level: L2
summary: 自然综合回答按块绑定支持材料并拒绝已知事实错配
load_when:
  - task:20260911-assistant-grounding
author: Codex
task_id: 20260911-assistant-grounding
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明内部支持材料、兼容失败、留存预算与确定性校验的语义局限。
evidence_sha256: 2ad8ac053d71c8ddacdaf1c48b257cb994c0b8b3cfc5ba2505b3dc9affd52c81
state_history:
---

# 20260911-assistant-grounding

Deterministic compressed record. The original active spec remains in Git history.

## Goal

每块自然综合回答绑定本轮有效证据原句，拒绝已确认的不支持结论，保证共同消费链路和内部材料隔离。

## Acceptance criteria

- AC-1: 无关引用假奖项、跨块借证据、数字单位/子串误配被拒；有据自述、自然综合、部分回答及路径呈现仍可用。
- AC-2: 每块 supports 与所引本轮 body 绑定，缺失/伪造/错绑拒绝；生产与本地 JSON 模式字段一致，固定简历提示例外保留；输入/输出预算包含材料且不提高配置额度。
- AC-3: 公开/管理问答、SSE、恢复和成功历史仅消费校验后回答；支持材料不进公开载荷、历史或 checkpoint，失败/成功终止清除临时解析材料，旧未完成输出不得绕过校验；撤销来源仍不能发布。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-assistant-grounding.json](../../verification/evidence/20260911-assistant-grounding.json)

SHA-256: `2ad8ac053d71c8ddacdaf1c48b257cb994c0b8b3cfc5ba2505b3dc9affd52c81`

Closed at 2026-09-11T14:39:55.242957+00:00.
