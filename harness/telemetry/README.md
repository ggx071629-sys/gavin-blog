---
id: telemetry-policy
level: L1
summary: Telemetry 仅用于观测，不能直接影响 Agent 行动
load_when:
  - observability-review
  - telemetry-change
author: Gavin
---

# Telemetry policy

原始事件采用追加式 JSONL，保存在 `local/` 且不提交 Git。可提交的 `summaries/` 必须脱敏并引用来源范围。

Telemetry 不得改变 Agent 的工具选择、加载路径、spec 要求或验证门槛，也不得直接触发 Evolution。只有人工确认的显式事件可以进入 Evolution。

## Runtime observations

`python -m tools.harness verify <task_id>` 完成后尽力追加 `task.verification`；`npm run quality:release` 为每个阶段追加 `release.stage`，并在成功或提前失败时追加一个 `release.run`。写入错误只输出有限告警，不改变原始 gate 的通过或失败。

运行事件只允许保存状态、毫秒耗时、check/test 计数、失败类别、profile、提交 SHA、隔离清理状态、随机 run ID、稳定阶段名、退出码和 change coverage 模式。禁止保存 stdout/stderr、命令参数、绝对路径、环境变量、密钥、用户内容或动作建议。

从 `harness/` 运行以下命令验证全部本地 JSONL 并生成即时摘要：

```powershell
python -m tools.harness telemetry-summary
python -m tools.harness telemetry-summary --json
python -m tools.harness telemetry-health
python -m tools.harness telemetry-health --json
```

摘要按 kind 与 release stage 统计事件和状态，并对非负 `duration_ms` 使用 nearest-rank 计算 P50/P95，同时报告 count 与 max。空目录产生合法空摘要；损坏行按文件名和行号失败，不能静默忽略。原始数据仍只留本机；如需提交脱敏摘要，必须人工复核来源窗口和解释，且摘要本身不能触发 Evolution。

`telemetry-health` 只评估 `task.verification`、`release.run` 与带稳定 stage 名的 `release.stage`。默认至少 3 个状态样本才评估连续失败，最近 2 个连续失败产生 observation signal；耗时比较只用于 release run/stage，要求 3 个 baseline 与随后 3 个 recent 样本，并在 recent 中位数达到 baseline 的 1.5 倍时产生 signal。窗口、最小样本和阈值来自 `config.toml`；不完整或非法配置会失败，零耗时 baseline 只明确标记而不猜测比率。

健康状态为 `no-data`、`insufficient-data`、`stable` 或 `signal`。`signal` 仍是本机事件流的观察，不是已确认的退化：命令不会写入任何文件，发现 signal 仍返回成功，也不得直接改变 gate 或产生 Evolution event。人必须结合环境、样本可比性和原始验证证据确认问题；只有确认属于重复失败或流程摩擦后，才能按 Retrospect workflow 显式发出允许的事件。
