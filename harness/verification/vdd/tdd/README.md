---
id: vdd-tdd
level: L1
summary: 以单元和组件测试先行验证局部行为
load_when:
  - unit-behavior
  - component-behavior
  - implementation
author: Gavin
---

# TDD

TDD 是 VDD 的默认实现技术之一。优先让失败测试描述行为，再实现最小代码使其通过，最后在测试保护下重构。文档、配置、迁移和端到端流程可以采用更合适的验证方式，不机械追求单元测试先行。

