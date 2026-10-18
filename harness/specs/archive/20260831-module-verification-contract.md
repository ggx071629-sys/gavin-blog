---
id: archive-20260831-module-verification-contract
level: L2
summary: 建立现行产品模块、可观察预期、具体测试引用与验证 Gate 之间的机器可校验闭环
load_when:
  - task:20260831-module-verification-contract
author: Codex
task_id: 20260831-module-verification-contract
status: compressed
documentation_impact: required
documentation_targets:
  - harness/docs/product/brief.md
  - harness/verification/README.md
  - harness/specs/_sdd/template.md
  - harness/workflows/specify.md
documentation_reason: 模块验证合同会改变新任务的验证计划格式、全局 Harness 完整性检查与 evidence 解释边界，必须同步长期验证政策、Spec 模板和 specify 工作流。
state_history:
---

# 20260831-module-verification-contract

Deterministic compressed record. The original active spec remains in Git history.

## Goal

建立最小、确定性且失败关闭的模块验证合同：覆盖权威十个现行模块的 P0/P1 基线场景；让每个场景声明明确预期及覆盖这些预期的真实测试引用；让新任务把每项 AC 映射到场景 ID；让全局检查、task verify、schema v2 evidence 与 close 对合同、测试引用和 Gate 覆盖漂移保持一致。

## Acceptance criteria

- AC-1: 仓库包含版本化模块验证合同，精确覆盖产品基线的 M01—M10；每个模块至少有一个 P0 和一个 P1 场景，每个场景都有唯一 ID、可观察预期、禁止发生项、Gate 与真实测试引用，且每条预期都被至少一个引用显式覆盖。
- AC-2: 全局 `module-coverage` 检查确定性拒绝合同字段漂移、缺失或重复模块／场景／预期、危险路径、未知 Gate、Gate 与测试套件不兼容、测试文件缺失、测试定位符不存在或不唯一，以及未被测试引用覆盖的预期；当前仓库合同通过该检查。
- AC-3: 新 active Spec 必须用 `Verification cases` 将每项 AC 映射到一个或多个合法场景 ID；spec-lint 验证结构完整性，task verify 在实现完成后解析场景、验证该 AC 的 Gate 计划直接或经已证明 subsumption 覆盖场景所需 Gate，并把解析后的场景、测试引用及合同摘要写入 schema v2 evidence；合同、映射、测试引用或 Gate 漂移使旧 evidence 失效。
- AC-4: 长期验证政策、SDD 模板与 specify 工作流准确说明模块场景映射格式、机器保证边界、人工语义审查责任，以及 planned 场景在 spec-lint 与 task verify 间的解析时点。
- AC-5: 新增控制面逻辑有正向与失败路径单测；Harness 全局检查、Harness 测试和完整 release gate 通过，且不修改或提交现有无关工作区变更。

## Result

Verified and closed by the harness close command.

## Evidence

[20260831-module-verification-contract.json](../../verification/evidence/20260831-module-verification-contract.json)

Closed at 2026-08-31T15:08:38.099398+00:00.
