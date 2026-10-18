---
id: spec-20261018-harness-completion
level: L1
summary: 补齐远端 Harness 引用的文档、业务测试和质量门禁工作流
load_when:
  - task:20261018-harness-completion
task_id: 20261018-harness-completion
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - README.md
  - harness/docs/operations/release-readiness.md
documentation_reason: 说明远端检出所需的文档、测试、CI依赖及结构验证和发布候选验证各自的范围，记录可复现入口与真实结果。
state_history:
---

# Context

用户要求将前次 Harness 上传中遗漏的文档、业务测试和 CI 补齐至 gavin-blog，并使完整校验通过。前次上传保留了源仓库的规格历史，远端业务树与本地工作树可能不同。以远端 main 为候选基线，核对每个实际引用并恢复所需支持文件，不把本地未提交业务改动混入本任务。

# Goal

补齐当前 Harness 所需且可追溯的项目文档、可执行业务测试和 CI 工作流；修复由文件遗漏、源码引用或测试入口漂移造成的校验缺口。保持所有既有模块、case、锁文件安全策略与质量门禁，生成当前索引并提交完整候选。全局 Harness verify 必须通过；远端 CI 执行权威发布候选质量链并据真实运行结果处理本次引入的问题。

# Non-goals

不部署、不开放公开助手、不生成生产资格，不重写历史证据，不降低现有检查或删除 case 以通过验证；独立既有产品行为缺陷如超出本次恢复范围，必须先报告其证据和影响。

# Acceptance criteria

- AC-1: 远端候选包含当前 Harness 引用的项目文档和业务测试，模块合同、文件归属、链接与生成索引完整；无 task 的全局 Harness verify 通过。
- AC-2: GitHub CI 从锁文件重建依赖并执行权威质量链，保留完整提交历史和可信变更覆盖基线，actions、权限及脱敏 telemetry 符合现行合同。
- AC-3: README 和发布准备文档说明候选验证的可复现命令、边界和实际结果；本任务提交快照的精确 Harness 检查通过，关闭产物与新提交保持一致。

# Verification plan

## Verification cases

- AC-1 => M08-DOCS-01, M08-TRACE-01, M08-LINKS-01, M08-UNIT-METADATA-01
- AC-2 => M08-UNIT-CI-01, M08-UNIT-SUPPLY-CHAIN-01
- AC-3 => M08-DOCS-01, M08-TRACE-04

## Gates

- harness-integrity => AC-1, AC-3
- harness-tests => AC-1, AC-2, AC-3
