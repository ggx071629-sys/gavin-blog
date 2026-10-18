---
id: workflow-retrospect
level: L1
summary: 从已确认的摩擦或失败中产生显式 Evolution 事件
load_when:
  - retrospective
  - repeated-failure
author: Gavin
---

# Retrospect

- Input：spec、evidence 与人工确认的问题。
- Preconditions：不得用普通 telemetry 指标替代判断；重复失败必须由人核对同一 task 的环境、失败类别和样本可比性。
- Output：必要时产生允许类型的 evolution event。
- Checks：事件有来源、有理由、不直接修改 `AGENTS.md`。`verification.repeated_failure` 从 `harness/` 显式运行 `python -m tools.harness emit-event verification.repeated_failure <task_id> --run-id <failed-run-1> --run-id <failed-run-2> --reason "..."`；两个 run 必须来自本地同 task 的 failed telemetry，命令只生成等待人工确认的 proposal。task verify 失败现场若已具备两个 run，会打印同一命令，仍须人工执行。
- Complete when：无行动，或形成等待人工确认的 proposal。
