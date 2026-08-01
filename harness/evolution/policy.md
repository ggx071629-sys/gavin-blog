---
id: evolution-policy
level: L1
summary: 仅由显式事件驱动、经人工确认后应用的控制面演进规则
load_when:
  - process-evolution
  - repeated-failure
  - architecture-decision
author: Gavin
---

# Evolution policy

允许的事件只有：

- `spec.completed`
- `verification.repeated_failure`
- `architecture.decision`
- `workflow.friction_confirmed`

事件必须由人或确定性生命周期动作显式产生，普通 telemetry 不能直接触发。事件可以生成 proposal，但 proposal 只有在人工确认后才能修改 L1/L2、模板、workflow、index source 或 checks。

`AGENTS.md` 是永久禁止的自动修改目标。确需调整 L0 时，必须开启新的人工决策任务。

