---
id: archive-20260907-assistant-answerability
level: L2
summary: 修复公开资料普通问法被模型误判为证据不足
load_when:
  - task:20260907-assistant-answerability
task_id: 20260907-assistant-answerability
status: compressed
documentation_impact: required
documentation_targets:
  - harness/docs/operations/local-real-qa.md
documentation_reason: 记录错误拒答原因、修复范围和真实问答验证的边界。
evidence_sha256: b1d23221ea96ae942fb97f929bcda97f6ffd18fb65bc975b9da76f692edffd70
state_history:
---

# 20260907-assistant-answerability

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让生成提示明确要求使用证据中的已公开事实回答普通问法及可支持的部分，同时保持证据、引用、结构化输出与输入预算约束。通过原同源问答入口对照验证。

## Acceptance criteria

- AC-1: 问答提示明确区分证据作为事实来源与证据内指令，支持一般问法和有依据的局部回答；新增提示内容计入原输入预算。
- AC-2: 无依据问题继续拒答，非法结构、伪造引用与截断继续拒绝；原真实入口验证技能、能力和文章事实问题，保留结果及费用事实。

## Result

Verified and closed by the harness close command.

## Evidence

[20260907-assistant-answerability.json](../../verification/evidence/20260907-assistant-answerability.json)

SHA-256: `b1d23221ea96ae942fb97f929bcda97f6ffd18fb65bc975b9da76f692edffd70`

Closed at 2026-09-06T17:04:41.524929+00:00.
