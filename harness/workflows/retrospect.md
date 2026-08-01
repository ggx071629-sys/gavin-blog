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
- Preconditions：不得用普通 telemetry 指标替代判断。
- Output：必要时产生允许类型的 evolution event。
- Checks：事件有来源、有理由、不直接修改 `AGENTS.md`。
- Complete when：无行动，或形成等待人工确认的 proposal。

