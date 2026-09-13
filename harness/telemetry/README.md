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

摘要按 kind 与 release stage 统计事件和状态，并对非负 `duration_ms` 使用 nearest-rank 计算 P50/P95，同时报告 count 与 max。空目录产生合法空摘要；损坏行按文件名和行号失败，不能静默忽略。原始数据仍只留产生它的运行环境；如需提交脱敏摘要，必须人工复核来源窗口和解释，且摘要本身不能触发 Evolution。

GitHub `Release gate` workflow 是唯一的自动持久化例外：权威 release gate 结束后，无论通过或失败，workflow 都从本次 runner 的本地 JSONL 生成 `telemetry-summary --json` 与 `telemetry-health --json`，把两份派生 JSON 写入 Job Summary，并上传到精确限定的 runner 临时目录 artifact。artifact 保留 14 天，不包含原始 JSONL、stdout/stderr、环境变量、绝对路径、工作区文件或永久排除目录；生成或上传失败会显式使 job 失败，但后置 `always()` 步骤不会把原 release gate 的失败改为成功。

CI summary/health 只是跨运行人工比较的短期输入，不是自动控制信号。下载、聚合或解释 artifact 时必须考虑 runner 性能、缓存、依赖下载与并发差异；不得据此改变 Agent 行为、gate、spec 或 Evolution 状态。私有仓库 artifact 占用 GitHub Actions 存储配额，因此内容和 14 天保留期属于受测试保护的成本边界。

`telemetry-health` 只评估带 task ID 的 `task.verification`、`release.run` 与带稳定 stage 名的 `release.stage`。task verification 按 `task.verification:<task_id>` 分组，不把不同任务的失败拼成连续序列；缺少 task ID 的 task 事件不参与健康判断。默认至少 3 个同 series 状态样本才评估连续失败，最近 2 个连续失败产生 observation signal；耗时比较只用于 release run/stage，要求 3 个 baseline 与随后 3 个 recent 样本，并在 recent 中位数达到 baseline 的 1.5 倍时产生 signal。窗口、最小样本和阈值来自 `config.toml`；不完整或非法配置会失败，零耗时 baseline 只明确标记而不猜测比率。

人工确认同一 task 存在至少两个可比较失败后，可以在本地 JSONL 尚存时把明确 run ID 交给 Retrospect workflow。读取和校验 run 只返回 run ID、观察时间、source commit、failure kinds 与 isolation cleanup；不会复制 reason、stdout、路径或用户内容，也不会自行写 Evolution 文件。

健康状态为 `no-data`、`insufficient-data`、`stable` 或 `signal`。`signal` 仍是本机事件流的观察，不是已确认的退化：命令不会写入任何文件，发现 signal 仍返回成功，也不得直接改变 gate 或产生 Evolution event。人必须结合环境、样本可比性和原始验证证据确认问题；只有确认属于重复失败或流程摩擦后，才能按 Retrospect workflow 显式发出允许的事件。
