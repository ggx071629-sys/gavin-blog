---
id: archive-20260814-upload-artifact-node24
level: L2
summary: 升级 CI telemetry artifact action 到官方 Node 24 运行时并消除弃用警告
load_when:
  - task:20260814-upload-artifact-node24
author: Codex
task_id: 20260814-upload-artifact-node24
status: compressed
documentation_impact: required
documentation_targets:
  - harness/docs/decisions/20260814-python-lock-and-control-plane.md
documentation_reason: CI 供应链的固定 action 版本与运行时基线是长期控制面决策
state_history:
---

# 20260814-upload-artifact-node24

Deterministic compressed record. The original active spec remains in Git history.

## Goal

将唯一 artifact 上传步骤固定到官方 v7.0.1 的完整 commit SHA，在不改变脱敏文件集合、失败语义和保留期的前提下消除 Node 20 弃用依赖。

## Acceptance criteria

- AC-1: workflow 将 `actions/upload-artifact` 固定到 v7.0.1 对应的完整 commit `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`，注释与官方 tag 一致。
- AC-2: 上传步骤仍为 `if: always()`，只包含 runner temp 下的 sanitized summary/health，`if-no-files-found: error` 与 `retention-days: 14` 不变。
- AC-3: CI 静态测试与全局 supply-chain check 拒绝旧 SHA、浮动 ref、权限或上传边界降级。
- AC-4: 供应链决策文档记录官方 v7.0.1、Node 24 原因和远端 warning 来源，不把版本更新扩张为其他改动。
- AC-5: 本地 release 与最终 Draft PR `quality-release` 在当前 head 通过，最终 run 不再产生 upload-artifact Node 20 弃用注解。

## Result

Verified and closed by the harness close command.

## Evidence

[20260814-upload-artifact-node24.json](../../verification/evidence/20260814-upload-artifact-node24.json)

Closed at 2026-08-14T07:17:10.953012+00:00.
