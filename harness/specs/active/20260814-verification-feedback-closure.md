---
id: spec-20260814-verification-feedback-closure
level: L1
summary: 让 AC 结果、失败诊断与人工确认的重复失败 Evolution 链可审计闭合
load_when:
  - task:20260814-verification-feedback-closure
author: Codex
task_id: 20260814-verification-feedback-closure
status: active
verification_profile: release
documentation_impact: required
documentation_targets:
  - harness/verification/README.md
  - harness/telemetry/README.md
  - harness/evolution/policy.md
  - harness/workflows/retrospect.md
documentation_reason: AC 证据、失败诊断、task 级健康序列与人工 repeated-failure 事件是长期验证和演进合同
state_history:
---

# Context

schema v2 evidence 保存 gate 的 `covers`，但没有逐 AC 的派生状态，审阅者必须手工反推；gate 失败时 CLI 只打印有限尾部，多次 Nuxt/Playwright 瞬态失败没有保留首个诊断锚点。Telemetry health 又把不同 task 的 `task.verification` 混成同一 series，而显式 `verification.repeated_failure` 事件不要求引用真实失败 run，导致观察与人工 Evolution 决定之间缺少可靠证据桥。

# Goal

在不让 telemetry 自动驱动行为的前提下，让 task evidence 确定性呈现逐 AC 状态，让失败输出同时保留脱敏首因与有限尾部，并要求人工 repeated-failure 事件引用同一 task 至少两个真实、失败的本地 telemetry run。

# Non-goals

- 不根据 telemetry signal 自动发 event、创建/接受/应用 proposal 或修改 gate。
- 不提交原始 telemetry、stdout/stderr、截图、trace、环境变量或绝对路径。
- 不用文本启发式宣称 AC 的自然语言与测试语义必然一致；只证明声明映射的 gate 结果。
- 不增加测试重试、自动修复或修改 `AGENTS.md`。

# Acceptance criteria

- AC-1: schema v2 task evidence 按 spec 中 AC 顺序保存每项 `passed`、`failed` 或 `not-run` 状态及其声明 gate，结果由 gate checks 确定性计算。
- AC-2: evidence validation 重新计算逐 AC 结果，拒绝缺失、伪造、顺序或状态不一致的 criteria results；旧历史 inventory 不被追溯性改写。
- AC-3: 非零 gate 的 CLI details 第一项保存脱敏诊断锚点，并在固定总行数内追加去重尾部；结构化 failure summary 与 details 使用同一锚点，绝不保存完整输出。
- AC-4: telemetry health 将 `task.verification` 按 task ID 分成独立 series；缺少 task ID 的 task 事件不参与健康判断，release series 语义不变。
- AC-5: `emit-event verification.repeated_failure` 只接受 manual source，必须提供至少两个唯一 run ID；每个 ID 必须匹配本地同 task 的 failed verification event，事件和 proposal 只保存 run ID、时间、commit、failure kinds 与 cleanup 状态。
- AC-6: telemetry 读取或 signal 本身仍不写 event/proposal；其他 event 类型拒绝 repeated-failure run 引用，生命周期事件保持原行为。
- AC-7: 回归测试覆盖 AC passed/failed/not-run、evidence 篡改、诊断锚点与限长、跨 task 假连续失败、有效/缺失/重复/错误 task/非失败 run 引用及 proposal 内容。
- AC-8: Verification、Telemetry、Evolution 与 Retrospect 文档明确能力、人工确认步骤、证据边界和不可自动应用原则。
- AC-9: release profile 与最终 change coverage 完整通过，生成当前 schema v2 evidence。

# Risks

- 把 gate 映射派生状态误写成语义证明会制造虚假确定性；文档和字段命名必须限定为声明映射结果。
- 首因启发式可能抓到无关 warning；必须使用有序强诊断模式并同时保留有限尾部供人工判断。
- 本地 telemetry 可能被清理或来自不可比较环境；缺失时应失败，不得凭 reason 伪造引用。
- event 保存过多观测字段会扩大持久化边界；只允许现有脱敏 schema 的最小引用字段。

# Verification plan

- release => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9
