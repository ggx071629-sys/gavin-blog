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

`telemetry-health` 产生的 `signal` 仍然只是观察：即使达到连续失败或耗时比率阈值，也不能自动转换为 `verification.repeated_failure` 或 `workflow.friction_confirmed`。人工必须核对运行环境、样本可比性与对应验证证据，再通过 Retrospect workflow 显式决定是否发出事件；`no-data`、`insufficient-data` 与 `stable` 同样不得作为自动行动指令。

显式 `verification.repeated_failure` 只能使用 `manual` source，并必须提供同一 task 至少两个唯一、本地可验证且状态为 failed 的 `task.verification` run ID。CLI 从原始本地 telemetry 提取最小脱敏引用，event 与 proposal 只持久化 run ID、观察时间、source commit、failure kinds 与隔离清理状态。缺失、重复、属于其他 task 或已经 passed 的 run 均失败且不创建 event/proposal；满足引用条件仍只证明人确认了重复失败，不等于 proposal 已获准应用。

事件是不可变审计记录，不是文件监听器或内容改写回调。生命周期 close 产生的 `spec.completed` 只表示该 spec 已通过验证并压缩，不自动创建 proposal，也不修改 README。durable 文档同步由 active spec 的 `documentation_impact` 契约在 verify/close 前强制完成；如果事件暴露新的流程摩擦，应另行显式发出允许的演进事件，生成 proposal 并经人工确认后实施。

`AGENTS.md` 是永久禁止的自动修改目标。确需调整 L0 时，必须开启新的人工决策任务。

## Proposal routing

`proposed` 与 `accepted` proposal 属于当前决策面，和 policy 一起出现在主 Evolution 索引。`applied`、`reviewed-no-action` 与 `rejected` 已经终结，只从 [proposal 历史索引](proposals/INDEX.md) 按需查询；主索引保留 [历史入口](history.md)，不展开全部冷记录。路由降级不删除、移动或重写 proposal/event，也不改变既有人工决定。
