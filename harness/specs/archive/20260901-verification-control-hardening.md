---
id: archive-20260901-verification-control-hardening
level: L2
summary: 封闭模块验证、产品 Gate evidence 与历史证据中的假绿和语义错配
load_when:
  - task:20260901-verification-control-hardening
author: Codex
task_id: 20260901-verification-control-hardening
status: compressed
documentation_impact: required
documentation_targets:
  - harness/verification/README.md
  - harness/specs/_sdd/template.md
  - harness/workflows/specify.md
  - harness/docs/decisions/20260901-verification-attestation.md
documentation_reason: 修复会改变测试引用的收集权威、Gate evidence 的可信边界、关闭后证据完整性以及新模块的 specify 规则，需要固化为长期验证政策和架构决策。
evidence_sha256: 582de658b5a7261753e4470c966456ecd0af45560239f18d8ac24df836fb2931
state_history:
---

# 20260901-verification-control-hardening

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让模块验证与任务关闭重新满足失败关闭：测试引用必须来自对应 Gate 的真实可收集清单；产品 Gate 结果必须具备可验证且不可由普通 evidence 编辑伪造的执行绑定；关闭后的 evidence 必须保持内容完整；当前模块合同的每项声明必须由实际断言对应；验证器对恶意或畸形输入返回确定、有限诊断；新增模块仍能先写 planned spec、再由 task verify 对当前 authority 和合同严格收口。

## Acceptance criteria

- AC-1: module-coverage 只接受真实 collector 可见且未被永久 skip/todo/fixme 的 Pytest、Vitest 与 Playwright 测试；引用文件、框架配置或 Gate command 漂移时确定性失败，字符串、死代码、嵌套函数和非收集文件不得形成假绿引用。
- AC-2: task evidence 对每个产品 Gate 校验规范化命令、零退出结果和可信执行绑定；手工把失败或未运行 Gate 改成 passed、删除 result 或重算 summary/criteria_results 均不能通过 validate_evidence 或 close，且修复不依赖可由同一 JSON 自行伪造的字段。
- AC-3: close 固化完整 evidence 的不可变摘要，后续 history-integrity 会拒绝 evidence 缺字段、内容篡改、digest 漂移或归档／事件绑定缺失，同时保留既有历史 evidence 的明确兼容边界。
- AC-4: 模块合同与引用测试逐项对应：M08 覆盖真实仓库合同、完整负向 mutation、direct/subsumed Gate 和人工语义审查责任；M02 验证旧 revision 不变；M04 验证稳定年月路径；M07 准确表述本地 production-build preview；M09/M10 分别覆盖 API capability 与 fresh-start 默认关闭事实。
- AC-5: 验证器严格拒绝浮点 schema 版本和非字符串枚举输入，所有诊断净化、确定排序并有单条与总条数上限；required-check 配置复用统一 schema；spec-lint 强制新模板的 Verification plan 结构，并允许 planned 新模块在实现前通过、到 task verify 时由当前 authority/合同严格解析。
- AC-6: 新增正向、失败和防篡改单测覆盖全部上述分支；Harness 全局检查、API 测试、Web 质量门禁和完整 release 通过，且无关工作区改动未被覆盖或提交。

## Result

Verified and closed by the harness close command.

## Evidence

[20260901-verification-control-hardening.json](../../verification/evidence/20260901-verification-control-hardening.json)

SHA-256: `582de658b5a7261753e4470c966456ecd0af45560239f18d8ac24df836fb2931`

Closed at 2026-08-31T19:56:41.961086+00:00.
