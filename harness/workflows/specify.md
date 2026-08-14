---
id: workflow-specify
level: L1
summary: 按 SDD 产生短生命周期、可验证的 active spec
load_when:
  - spec-create
  - risky-change
author: Gavin
---

# Specify

- Input：intake 结果与相关 L1 文档。
- Preconditions：命中 SDD 风险触发器。
- Output：带 task ID 的 active spec。
- Checks：验收标准可观察，验证计划覆盖风险下限；多条 AC 不得只映射到同一个包门禁。实现前运行 `python -m tools.harness spec-lint <task_id>`。
- Complete when：实现者无需猜测产品行为或完成条件，且 spec-lint 通过。

