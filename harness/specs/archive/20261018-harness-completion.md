---
id: archive-20261018-harness-completion
level: L2
summary: 补齐远端 Harness 引用的文档、业务测试和质量门禁工作流
load_when:
  - task:20261018-harness-completion
task_id: 20261018-harness-completion
status: compressed
documentation_impact: required
documentation_targets:
  - README.md
  - harness/docs/operations/release-readiness.md
documentation_reason: 说明远端检出所需的文档、测试、CI依赖及结构验证和发布候选验证各自的范围，记录可复现入口与真实结果。
evidence_sha256: 776bd59c4174c6ec84deb902ed91f769414ac73c018232035f5080542b47f440
state_history:
---

# 20261018-harness-completion

Deterministic compressed record. The original active spec remains in Git history.

## Goal

补齐当前 Harness 所需且可追溯的项目文档、可执行业务测试和 CI 工作流；修复由文件遗漏、源码引用或测试入口漂移造成的校验缺口。保持所有既有模块、case、锁文件安全策略与质量门禁，生成当前索引并提交完整候选。全局 Harness verify 必须通过；远端 CI 执行权威发布候选质量链并据真实运行结果处理本次引入的问题。

## Acceptance criteria

- AC-1: 远端候选包含当前 Harness 引用的项目文档和业务测试，模块合同、文件归属、链接与生成索引完整；无 task 的全局 Harness verify 通过。
- AC-2: GitHub CI 从锁文件重建依赖并执行权威质量链，保留完整提交历史和可信变更覆盖基线，actions、权限及脱敏 telemetry 符合现行合同；恢复的本地工具保留安全隔离，Windows 跨盘生成路径可重复归一，Git 中文路径在 GBK 默认环境保持 UTF-8 精确身份；恢复完整门禁时暴露的类型错误通过保持接口语义的修复消除，下载、解析、lease 与索引的既有运行语义保持不变；生产质量测试按已存在的账号恢复入口校正断言，并保留响应式、键盘顺序、触控和 WCAG 门槛；公开卡片反馈仅验证已标注的卡片，不把静态自述文字块误当反馈卡片，现有 UI 与 CSS 保持；列表 loading 测试遵循真实客户端分页导航和路由响应生命周期，保留 loading、空态与上游失败的正负边界；Studio 断言使用既有共享主题 token、含账号安全的十个导航入口，以及当前试问恢复的错误与数据合同，保留原响应式和无障碍矩阵；公开简历引用测试区分 localDev 确定性本地摘录与云端说明，明确回答所据 PDF 版本，并保留双端精确文件下载与路径安全检查。
- AC-3: README 和发布准备文档说明候选验证的可复现命令、边界和实际结果；本任务提交快照的精确 Harness 检查通过，关闭产物与新提交保持一致。

## Result

Verified and closed by the harness close command.

## Evidence

[20261018-harness-completion.json](../../verification/evidence/20261018-harness-completion.json)

SHA-256: `776bd59c4174c6ec84deb902ed91f769414ac73c018232035f5080542b47f440`

Closed at 2026-10-18T07:56:03.390270+00:00.
