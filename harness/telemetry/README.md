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

