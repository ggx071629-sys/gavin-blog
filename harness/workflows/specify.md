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
- Checks：验收标准可观察，验证计划覆盖风险下限；多条 AC 不得只映射到同一个包门禁。`## Verification cases` 必须让每个 AC 恰好出现一次并至少映射一个 `M01-SCENARIO-01` 形式的 case，多个 case 用逗号分隔；未知 AC、未知模块 ID、同一 AC 内重复 case ID或缺失 AC 覆盖均禁止，同一 case 可被多条相关 AC 复用。Case ID 可以在 specify 时尚未出现在变更前合同中，视为本任务将新增的 planned case；task verify 才以当前提交中的模块验证合同解析全部 case，并核对 exact test refs、observable required／forbidden expectations、leaf gate 与 `gate => AC` 覆盖，届时任何未解析 planned case 都必须失败。实现前运行 `python -m tools.harness spec-lint <task_id>`。
- Complete when：实现者无需猜测产品行为或完成条件，且 spec-lint 通过。
