---
id: archive-20260814-verification-feedback-closure
level: L2
summary: 让 AC 结果、失败诊断与人工确认的重复失败 Evolution 链可审计闭合
load_when:
  - task:20260814-verification-feedback-closure
author: Codex
task_id: 20260814-verification-feedback-closure
status: compressed
documentation_impact: required
documentation_targets:
  - harness/verification/README.md
  - harness/telemetry/README.md
  - harness/evolution/policy.md
  - harness/workflows/retrospect.md
documentation_reason: AC 证据、失败诊断、task 级健康序列与人工 repeated-failure 事件是长期验证和演进合同
state_history:
---

# 20260814-verification-feedback-closure

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在不让 telemetry 自动驱动行为的前提下，让 task evidence 确定性呈现逐 AC 状态，让失败输出同时保留脱敏首因与有限尾部，并要求人工 repeated-failure 事件引用同一 task 至少两个真实、失败的本地 telemetry run。

## Acceptance criteria

- AC-1: schema v2 task evidence 按 spec 中 AC 顺序保存每项 `passed`、`failed` 或 `not-run` 状态及其声明 gate，结果由 gate checks 确定性计算。
- AC-2: evidence validation 重新计算逐 AC 结果，拒绝缺失、伪造、顺序或状态不一致的 criteria results；旧历史 inventory 不被追溯性改写。
- AC-3: 非零 gate 的 CLI details 第一项保存脱敏诊断锚点，并在固定总行数内追加去重尾部；结构化 failure summary 与 details 使用同一锚点，绝不保存完整输出。
- AC-4: telemetry health 将 `task.verification` 按 task ID 分成独立 series；缺少 task ID 的 task 事件不参与健康判断，release series 语义不变。
- AC-5: `emit-event verification.repeated_failure` 只接受 manual source，必须提供至少两个唯一 run ID；每个 ID 必须匹配本地同 task 的 failed verification event，事件和 proposal 只保存 run ID、时间、commit、failure kinds 与 cleanup 状态。
- AC-6: telemetry 读取或 signal 本身仍不写 event/proposal；其他 event 类型拒绝 repeated-failure run 引用，生命周期事件保持原行为。
- AC-7: 回归测试覆盖 AC passed/failed/not-run、evidence 篡改、诊断锚点与限长、跨 task 假连续失败、有效/缺失/重复/错误 task/非失败 run 引用及 proposal 内容。
- AC-8: Verification、Telemetry、Evolution 与 Retrospect 文档明确能力、人工确认步骤、证据边界和不可自动应用原则。
- AC-9: release profile 与最终 change coverage 完整通过，生成当前 schema v2 evidence。

## Result

Verified and closed by the harness close command.

## Evidence

[20260814-verification-feedback-closure.json](../../verification/evidence/20260814-verification-feedback-closure.json)

Closed at 2026-08-14T06:02:57.029212+00:00.
