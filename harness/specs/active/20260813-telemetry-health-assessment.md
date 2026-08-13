---
id: spec-20260813-telemetry-health-assessment
level: L1
summary: 为本地 Harness 遥测增加保守、只读且不触发行为的健康评估
load_when:
  - task:20260813-telemetry-health-assessment
author: Codex
task_id: 20260813-telemetry-health-assessment
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - harness/telemetry/README.md
  - harness/evolution/policy.md
documentation_reason: 健康信号的统计语义及其不得自动驱动门禁或 Evolution 的边界属于长期控制面合同
state_history:
---

# Context

Harness 已能追加记录 task verification、release stage 和 release run，并生成 P50/P95 摘要，但没有区分样本不足、稳定与退化的确定性评估。当前人工只能阅读原始聚合后自行判断，`verification.repeated_failure` 虽是允许的 Evolution 事件，却没有机器可读的观察依据；同时 Telemetry 政策明确禁止指标直接改变 Agent 行为或触发 Evolution。

# Goal

增加只读 `telemetry-health` 命令，按配置化窗口和阈值评估连续失败与耗时回归，明确报告样本不足，并保持观察与决策隔离。

# Non-goals

- 不让健康评估改变验证/发布退出码、Agent 工具选择、加载路径或 spec 要求。
- 不自动发出 Evolution event、创建 proposal、修改 workflow 或调整门禁阈值。
- 不提交本地原始遥测、远端 dashboard、通知系统或长期趋势数据库。
- 不把单次失败或小样本波动解释为确认的重复失败。

# Acceptance criteria

- AC-1: `python -m tools.harness telemetry-health [--json]` 只读现有 JSONL，按 task verification、release run 与稳定 release stage 序列输出确定性 assessment。
- AC-2: 每个序列至少区分 `no-data`、`insufficient-data`、`stable` 与 `signal`，且只有达到配置化最小样本后才能产生 failure 或 duration 信号。
- AC-3: failure 信号只基于最近连续失败数；duration 信号比较不重叠 baseline/recent 窗口的中位数比率，并处理零基线、缺失或非法 duration，避免除零和猜测。
- AC-4: 命令发现 signal 时仍返回成功，不写 telemetry/event/proposal，不输出动作建议；损坏 JSONL 仍按既有合同失败并定位文件与行号。
- AC-5: 配置与文档明确阈值、样本边界及“观察不能自动成为演化决定”的人工确认路径。

# Risks

- 阈值过敏会制造噪声；默认要求多个样本并只看连续失败。
- 本地样本跨机器和环境不可直接比较；评估只描述当前本地事件流，不声称全局健康。
- 将 signal 误当 gate 会破坏 Telemetry 边界；CLI 必须保持报告型成功退出，除非输入损坏或配置非法。

# Verification plan

- harness-tests => AC-1, AC-2, AC-3, AC-4, AC-5
- harness-integrity => AC-1, AC-4, AC-5
