---
id: spec-20260901-verification-control-hardening
level: L1
summary: 封闭模块验证、产品 Gate evidence 与历史证据中的假绿和语义错配
load_when:
  - task:20260901-verification-control-hardening
author: Codex
task_id: 20260901-verification-control-hardening
status: active
verification_profile: release
verification_escalation: 完整修复会改动 Gate 命令绑定、历史 evidence 与跨栈模块测试合同，最终必须执行 release 证明不存在控制面或产品回归。
documentation_impact: required
documentation_targets:
  - harness/verification/README.md
  - harness/specs/_sdd/template.md
  - harness/workflows/specify.md
  - harness/docs/decisions/20260901-verification-attestation.md
documentation_reason: 修复会改变测试引用的收集权威、Gate evidence 的可信边界、关闭后证据完整性以及新模块的 specify 规则，需要固化为长期验证政策和架构决策。
state_history:
---

# Context

模块验证合同已建立 M01-M10 到 expectation、test_ref、leaf Gate 与 task evidence 的链路，但评审确认静态源码扫描可把未收集或跳过的测试当作精确引用，Gate 名称未绑定真实 collector，产品 Gate evidence 可通过手工构造自洽 JSON 绕过执行，关闭后的 evidence 也没有内容摘要保护。当前合同还存在测试与自然语言预期不完全对应、默认关闭模块缺少独立权威覆盖、输入类型和诊断边界不确定，以及 planned 新模块无法遵循 spec-first 的问题。

# Goal

让模块验证与任务关闭重新满足失败关闭：测试引用必须来自对应 Gate 的真实可收集清单；产品 Gate 结果必须具备可验证且不可由普通 evidence 编辑伪造的执行绑定；关闭后的 evidence 必须保持内容完整；当前模块合同的每项声明必须由实际断言对应；验证器对恶意或畸形输入返回确定、有限诊断；新增模块仍能先写 planned spec、再由 task verify 对当前 authority 和合同严格收口。

# Non-goals

- 不改变博客产品的现行业务行为、公开问答生产资格或部署状态。
- 不把自然语言 expectation 与测试断言的语义等价自动化为不可判定的静态分析问题；该责任必须由明确的人工作业和可审查引用承担。
- 不修改或提交用户现有的 package.json、package-lock.json、.agents 或 skills-lock.json 工作区变更。

# Acceptance criteria

- AC-1: module-coverage 只接受真实 collector 可见且未被永久 skip/todo/fixme 的 Pytest、Vitest 与 Playwright 测试；引用文件、框架配置或 Gate command 漂移时确定性失败，字符串、死代码、嵌套函数和非收集文件不得形成假绿引用。
- AC-2: task evidence 对每个产品 Gate 校验规范化命令、零退出结果和可信执行绑定；手工把失败或未运行 Gate 改成 passed、删除 result 或重算 summary/criteria_results 均不能通过 validate_evidence 或 close，且修复不依赖可由同一 JSON 自行伪造的字段。
- AC-3: close 固化完整 evidence 的不可变摘要，后续 history-integrity 会拒绝 evidence 缺字段、内容篡改、digest 漂移或归档／事件绑定缺失，同时保留既有历史 evidence 的明确兼容边界。
- AC-4: 模块合同与引用测试逐项对应：M08 覆盖真实仓库合同、完整负向 mutation、direct/subsumed Gate 和人工语义审查责任；M02 验证旧 revision 不变；M04 验证稳定年月路径；M07 准确表述本地 production-build preview；M09/M10 分别覆盖 API capability 与 fresh-start 默认关闭事实。
- AC-5: 验证器严格拒绝浮点 schema 版本和非字符串枚举输入，所有诊断净化、确定排序并有单条与总条数上限；required-check 配置复用统一 schema；spec-lint 强制新模板的 Verification plan 结构，并允许 planned 新模块在实现前通过、到 task verify 时由当前 authority/合同严格解析。
- AC-6: 新增正向、失败和防篡改单测覆盖全部上述分支；Harness 全局检查、API 测试、Web 质量门禁和完整 release 通过，且无关工作区改动未被覆盖或提交。

# Risks

- 真实 collector 会增加 module-coverage 的运行成本，需缓存同一 Gate 的收集清单并避免启动产品服务。
- close 若直接重跑完整 release 会显著增加关闭时长；可信绑定设计必须在防伪与可重复成本之间给出明确权威，而不能退化成自签字段。
- 既有压缩 evidence 没有新摘要，历史完整性迁移必须显式区分 legacy 与新合同，不能批量改写历史文件。
- planned 模块放宽只能发生在 specify 阶段；task verify 仍必须拒绝未进入当前产品 authority 和模块合同的模块。

# Verification plan

## Verification cases

- AC-1 => M08-COLLECTOR-01
- AC-2 => M08-EVIDENCE-01
- AC-3 => M08-HISTORY-01
- AC-4 => M08-SEMANTICS-01, M02-P1-01, M04-P1-01, M07-P1-01, M09-P0-02, M10-P0-02
- AC-5 => M08-VALIDATOR-01, M08-SPEC-01
- AC-6 => M08-COLLECTOR-01, M08-EVIDENCE-01, M08-HISTORY-01, M08-SEMANTICS-01, M08-VALIDATOR-01, M08-SPEC-01

## Gates

- harness-tests => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6
- harness-integrity => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6
- api-tests => AC-4, AC-6
- web-quality => AC-4, AC-6
- release => AC-2, AC-3, AC-6
