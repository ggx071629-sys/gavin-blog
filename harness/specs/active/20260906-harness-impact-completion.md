---
id: spec-20260906-harness-impact-completion
level: L1
summary: 完成受影响模块选择的归属、传递分析、真实产品闭环及成本验收
load_when:
  - task:20260906-harness-impact-completion
author: Codex
task_id: 20260906-harness-impact-completion
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - harness/docs/decisions/20260905-verification-resume.md
  - harness/workflows/verify.md
documentation_reason: 补全影响计划、输入准备、精确执行和成本验收的持久合同。
state_history:
---

# Context

用户授权按统一提案完成 Harness 改造。既有归档只证明有限试点；本任务承接提案全部剩余要求，保留原始提案修改、历史 evidence 和 archive。

# Goal

完成显式源码归属、消费者及传递影响分析，验证 Pytest/Vitest/Playwright 的真实受限执行和产品任务关闭，逐项补齐故障与成本证据。

# Non-goals

不改变产品业务行为，不自动修改 AGENTS.md，不把普通任务升级为 release，不宣称本地凭据能抵抗同权限恶意操作者。

# Acceptance criteria

- AC-1: 当前受治理源码、共享配置及 Harness 工具有细粒度归属和可追溯 case；未知或歧义归属阻断且不回退全量。
- AC-2: 公共契约影响沿实际受影响消费者逐项审查，传递遗漏阻断；普通文档与可执行合同文档显式区分。
- AC-3: 真实产品模块计划、受限 Pytest/Vitest/Playwright 执行及同进程关闭成功，未选模块不执行或构建。
- AC-4: 新选择路径保留失败历史、未执行状态、同输入新失败优先、篡改及输入失效拒绝，fresh 仍保持所选范围。
- AC-5: 前置失败阻断昂贵检查，父子证明去重、产物缺失与清理失败有可执行证据。
- AC-6: plan/status/close 不调用产品测试、构建或 collector，文档任务不扫描安装依赖。
- AC-7: 全复用、部分复用、中断、并发和关闭竞态回滚经真实 CLI 验证，passed 能被 close 消费。
- AC-8: 最终输入及证据链接在执行前准备，验证后提交和关闭不机械重复测试；同一受控环境比较真实 Harness 与产品模块任务的修改前后耗时、范围及输出字节。
- AC-9: 逐项记录提案验收证据和真实局限，成本未改善或条目未通过时不误标 applied。

# Risks

依赖注册不等于影响证明；case 语义需要审查。真实浏览器场景需要已安装工具和可用端口。基准为本地受控测量，不外推模型 token 或普遍性能结论。

# Verification plan

## Verification cases

- AC-1 => M08-IMPACT-MAPPING-01
- AC-2 => M08-IMPACT-GRAPH-01
- AC-3 => M08-IMPACT-RUNNERS-01
- AC-4 => M08-IMPACT-EXECUTION-01
- AC-5 => M08-IMPACT-PREREQUISITES-01
- AC-6 => M08-IMPACT-SELECTION-01
- AC-7 => M08-IMPACT-SELECTION-01, M08-IMPACT-CLOSURE-01
- AC-8 => M08-IMPACT-BENCHMARK-01
- AC-9 => M08-DOCS-01

## Gates

- harness-tests => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8
- harness-integrity => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9
