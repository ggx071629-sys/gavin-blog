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
```

摘要按 kind 与 release stage 统计事件和状态，并对非负 `duration_ms` 使用 nearest-rank 计算 P50/P95，同时报告 count 与 max。空目录产生合法空摘要；损坏行按文件名和行号失败，不能静默忽略。原始数据仍只留本机；如需提交脱敏摘要，必须人工复核来源窗口和解释，且摘要本身不能触发 Evolution。
