---
id: workflow-verify
level: L1
summary: 用 VDD 与机器证据验证变更，而非依赖自然语言自证
load_when:
  - verification
  - implementation
author: Gavin
---

# Verify

- Input：实现、验收标准与相关 VDD 指南。
- Preconditions：检查命令可重复执行。
- Output：checks 结果与紧凑 evidence 清单。
- Checks：TDD、Contract、Integration、E2E、Quality 中与风险相关的部分。
- Complete when：证据支持每项验收标准，或明确报告失败。

