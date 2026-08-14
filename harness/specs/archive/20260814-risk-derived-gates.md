---
id: archive-20260814-risk-derived-gates
level: L2
summary: 根据 spec 后的已提交变更自动推导不可降低的最低验证 gate
load_when:
  - task:20260814-risk-derived-gates
author: Codex
task_id: 20260814-risk-derived-gates
status: compressed
documentation_impact: required
documentation_targets:
  - harness/verification/README.md
  - harness/workflows/verify.md
documentation_reason: 风险路径如何推导最低产品 gate 是长期验证合同和日常执行流程的一部分
state_history:
---

# 20260814-risk-derived-gates

Deterministic compressed record. The original active spec remains in Git history.

## Goal

从 active spec 首次提交到当前 HEAD 的已提交路径中确定性推导最低 gate，并要求 spec 的显式 verification plan 至少包含这些 gate；spec 可以增加验证但不能降低系统推导的风险下限。

## Acceptance criteria

- AC-1: `config.toml` 声明有序、可验证的 risk routes，每条 route 使用项目相对 prefix/file 匹配并引用已注册 gate。
- AC-2: task verify 以 spec introduction commit 的下一提交至 HEAD 为范围，确定性返回匹配路径、route 和去重后的最低 gate。
- AC-3: verification plan 缺少任一推导 gate 时在产品执行前失败，并报告缺失 gate 与触发路径；spec 不能用较低 profile 绕过。
- AC-4: spec 声明全部推导 gate 或额外 gate 时继续通过现有白名单、AC 覆盖、隔离和 evidence 校验。
- AC-5: risk route 配置、推导结果和变更路径进入规范化 evidence 指纹，配置或 HEAD 漂移使旧 evidence 失效。
- AC-6: 回归测试覆盖 API、Web、contracts/跨栈、依赖/CI/Harness、非风险文档、未知 gate、未提交修改与无实现变化。
- AC-7: 权威验证政策和 verify workflow 明确说明自动风险下限与 spec 只能增加不能降低的规则。
- AC-8: release profile 与最终 change coverage 完整通过，生成当前 schema v2 evidence。

## Result

Verified and closed by the harness close command.

## Evidence

[20260814-risk-derived-gates.json](../../verification/evidence/20260814-risk-derived-gates.json)

Closed at 2026-08-14T03:47:01.739684+00:00.
