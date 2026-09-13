---
id: archive-20260814-ci-telemetry-persistence
level: L2
summary: 在 CI 成功或失败后持久化脱敏 Harness telemetry 摘要
load_when:
  - task:20260814-ci-telemetry-persistence
author: Codex
task_id: 20260814-ci-telemetry-persistence
status: compressed
documentation_impact: required
documentation_targets:
  - harness/telemetry/README.md
  - harness/docs/operations/release-readiness.md
documentation_reason: CI telemetry 的持久化范围、保留周期、失败语义和人工解释边界属于长期观测与发布合同
state_history:
---

# 20260814-ci-telemetry-persistence

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让每次 GitHub release workflow 无论权威 gate 成功或失败，都生成可审计的脱敏 summary 与 health 派生结果，写入 GitHub Job Summary 并以短保留期 artifact 保存，同时维持只读权限、不可变 action 依赖和原 release 失败语义。

## Acceptance criteria

- AC-1: release workflow 在权威 gate 成功或失败后都运行 telemetry 派生步骤，并从 runner 本次生成的本地事件计算 JSON summary 与 health。
- AC-2: CI 只把脱敏 summary 与 health 写入 runner 临时目录；artifact 路径不包含原始 JSONL、日志、工作区目录或三个永久排除目录。
- AC-3: GitHub Job Summary 展示有限的人类可读 telemetry 结果，生成或上传失败会显式失败，且不会把已失败的权威 release gate 改为成功。
- AC-4: artifact 使用固定提交 SHA 的官方 upload action、短期保留和缺失文件失败策略；workflow 继续只拥有 `contents: read` 权限。
- AC-5: 静态回归测试锁定 always 语义、两类派生产物、Job Summary、artifact 范围、保留策略、不可变 action 和禁止原始 telemetry 上传。
- AC-6: telemetry policy 与 release readiness 文档说明 CI 持久化边界、保留期、观察不驱动行为原则和 GitHub 存储成本。
- AC-7: release profile 与最终 change coverage 完整通过，生成当前 schema v2 evidence。

## Result

Verified and closed by the harness close command.

## Evidence

[20260814-ci-telemetry-persistence.json](../../verification/evidence/20260814-ci-telemetry-persistence.json)

Closed at 2026-08-14T04:11:59.385050+00:00.
