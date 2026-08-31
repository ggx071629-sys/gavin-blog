---
id: spec-20260831-module-verification-contract
level: L1
summary: 建立现行产品模块、可观察预期、具体测试引用与验证 Gate 之间的机器可校验闭环
load_when:
  - task:20260831-module-verification-contract
author: Codex
task_id: 20260831-module-verification-contract
status: active
verification_profile: release
verification_escalation: 模块合同进入 task evidence 与 Gate 覆盖计算，必须用完整 release 证明现有 API、Web、E2E 和 Harness 子门禁仍被同一包门禁实际执行。
documentation_impact: required
documentation_targets:
  - harness/docs/product/brief.md
  - harness/verification/README.md
  - harness/specs/_sdd/template.md
  - harness/workflows/specify.md
documentation_reason: 模块验证合同会改变新任务的验证计划格式、全局 Harness 完整性检查与 evidence 解释边界，必须同步长期验证政策、Spec 模板和 specify 工作流。
state_history:
---

# Context

当前 Harness 将验收标准映射到白名单 Gate，并在 schema v2 evidence 中保存 Gate 结果；它明确不能证明自然语言验收标准与 Gate 内具体测试断言的语义一致性。项目已有十个权威现行模块和大量 Pytest、Vitest、Playwright 用例，但控制面没有版本化的“模块—场景—可观察预期—测试引用—Gate”合同，也没有要求新 Spec 把每项 AC 映射到具体模块验证场景。因此，一个宽泛 Gate 可以通过，而控制面无法判断对应预期是否存在测试、是否被唯一引用、是否由该 Gate 实际包含，形成验证假绿风险。

# Goal

建立最小、确定性且失败关闭的模块验证合同：覆盖权威十个现行模块的 P0/P1 基线场景；让每个场景声明明确预期及覆盖这些预期的真实测试引用；让新任务把每项 AC 映射到场景 ID；让全局检查、task verify、schema v2 evidence 与 close 对合同、测试引用和 Gate 覆盖漂移保持一致。

# Non-goals

- 不声称静态工具能够理解测试断言与自然语言预期的真实语义等价；该判断仍需代码审查。
- 不在本任务中引入任意覆盖率百分比、跨浏览器支持矩阵、视觉快照、在线漏洞扫描或生产 SLO。
- 不改变博客、管理后台或公开问答的用户可见业务行为，也不为未实现能力制造测试。
- 不修改、恢复或关闭冻结的公开问答生产资格任务。
- 不把历史 archive、旧迁移或兼容枚举重新定义为现行产品模块。

# Acceptance criteria

- AC-1: 仓库包含版本化模块验证合同，精确覆盖产品基线的 M01—M10；每个模块至少有一个 P0 和一个 P1 场景，每个场景都有唯一 ID、可观察预期、禁止发生项、Gate 与真实测试引用，且每条预期都被至少一个引用显式覆盖。
- AC-2: 全局 `module-coverage` 检查确定性拒绝合同字段漂移、缺失或重复模块／场景／预期、危险路径、未知 Gate、Gate 与测试套件不兼容、测试文件缺失、测试定位符不存在或不唯一，以及未被测试引用覆盖的预期；当前仓库合同通过该检查。
- AC-3: 新 active Spec 必须用 `Verification cases` 将每项 AC 映射到一个或多个合法场景 ID；spec-lint 验证结构完整性，task verify 在实现完成后解析场景、验证该 AC 的 Gate 计划直接或经已证明 subsumption 覆盖场景所需 Gate，并把解析后的场景、测试引用及合同摘要写入 schema v2 evidence；合同、映射、测试引用或 Gate 漂移使旧 evidence 失效。
- AC-4: 长期验证政策、SDD 模板与 specify 工作流准确说明模块场景映射格式、机器保证边界、人工语义审查责任，以及 planned 场景在 spec-lint 与 task verify 间的解析时点。
- AC-5: 新增控制面逻辑有正向与失败路径单测；Harness 全局检查、Harness 测试和完整 release gate 通过，且不修改或提交现有无关工作区变更。

# Risks

- 静态测试定位符只能证明测试定义存在并由 Gate 包含，不能证明断言语义正确；文档和审查界面必须明确该边界。
- 过度细化合同会增加维护成本；v1 只保存高风险 P0/P1 基线，不枚举所有页面细节或每个测试。
- 测试标题或函数重命名会让合同失败；这是预期的显式漂移信号，但错误信息必须足够定位。
- 新 Spec 可能计划尚未实现的场景；spec-lint 只验证 AC 到场景 ID 的结构，task verify 才要求 ID 已在当前合同中解析并有可执行测试引用。
- 现有冻结 Spec 不含新章节；全局校验不得因此破坏合法冻结状态。

# Verification cases

- AC-1 => M08-TRACE-01
- AC-2 => M08-TRACE-02
- AC-3 => M08-TRACE-03
- AC-4 => M08-TRACE-04
- AC-5 => M08-TRACE-02, M08-TRACE-03

# Verification plan

- harness-tests => AC-1, AC-2, AC-3, AC-4, AC-5
- harness-integrity => AC-1, AC-2, AC-4, AC-5
- release => AC-3, AC-5
