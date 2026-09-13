---
id: workflow-intake
level: L1
summary: 将模糊请求收敛为任务边界和风险判断
load_when:
  - task-intake
  - ambiguity
author: Gavin
---

# Intake

- Input：用户目标与当前仓库事实。
- Preconditions：先检查环境中可直接发现的事实。
- Output：目标、非目标、风险等级，以及是否需要 spec。
- Checks：边界无冲突；未知决策明确交给用户。
- Complete when：任务可以进入 specify 或轻量实现流程。

