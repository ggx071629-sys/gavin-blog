---
id: spec-20260812-harness-run-telemetry
level: L1
summary: 为任务验证与发布门禁建立本地追加式运行观测和确定性摘要
load_when:
  - task:20260812-harness-run-telemetry
author: Codex
task_id: 20260812-harness-run-telemetry
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - harness/telemetry/README.md
  - harness/telemetry/schema/README.md
documentation_reason: 运行事件的字段、隐私边界、失败语义和摘要口径必须成为长期可复查的观测合同
state_history:
---

# Context

Telemetry 目录目前只有 schema 和空占位文件，无法回答 gate 成功率、耗时分布、失败分类、change coverage 跳过比例或任务验证规模。已有 schema 明确要求 observation-only，且禁止 telemetry 直接改变 Agent 行为或触发 Evolution。

# Goal

让 task verify 与 `quality:release` 以不影响门禁结果的方式追加结构化本地事件，并提供验证与确定性摘要命令，使运行状态、耗时和失败类别可复算、可人工回顾。

# Non-goals

- 不让 telemetry 自动改变 gate、workflow、Agent 行为或 Evolution 状态。
- 不提交原始 JSONL，不保存 stdout/stderr、命令参数、绝对路径、环境变量、密钥或用户内容。
- 不实现远端指标平台、dashboard、告警、CI provider 或定时任务。
- 不在本任务中设计 Harness agent eval、清理历史 proposal 或重写旧 evidence。

# Acceptance criteria

- AC-1: task verify 完成后追加 `task.verification` 事件，包含状态、总耗时、check/test 计数、失败类别、profile、source commit 与隔离清理状态，但不包含原始日志或命令。
- AC-2: `quality:release` 为每个执行阶段追加 `release.stage`，并为成功或提前失败追加一个 `release.run`；事件包含随机 run ID、阶段、状态、耗时、退出码和 change coverage 模式。
- AC-3: telemetry 写入异常只能产生有限告警，不能把原本通过的验证改成失败，也不能掩盖原始 gate 失败。
- AC-4: `python -m tools.harness telemetry-summary [--json]` 验证本地 JSONL，并确定性计算事件数、状态数、按 kind/stage 聚合以及 duration 的 count/P50/P95/max；无数据时返回合法空摘要。
- AC-5: 文档明确事件字段、隐私边界、百分位口径、原始数据不提交以及人工 retrospective 才能进入 Evolution。

# Risks

- release runner 提前退出可能漏写 run 终态；所有退出路径必须先记录终态，写入失败仍保留原始退出码。
- JSONL 追加可能遇到损坏行或并发写；读取时必须逐行报告来源和行号，不能悄悄忽略。
- 百分位样本很小时容易被误读；摘要使用明确的 nearest-rank 口径并报告 count。

# Verification plan

- harness-tests => AC-1, AC-2, AC-3, AC-4
- harness-integrity => AC-4, AC-5
