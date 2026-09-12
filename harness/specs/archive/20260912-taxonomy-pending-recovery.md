---
id: archive-20260912-taxonomy-pending-recovery
level: L2
summary: 栏目标签请求悬挂时退出无限保存并保留输入和结果核对入口
load_when:
  - task:20260912-taxonomy-pending-recovery
author: Codex
task_id: 20260912-taxonomy-pending-recovery
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 记录栏目标签操作的局部等待上限、超时不等于服务端未写入、手动核对与禁止自动重放的边界。
evidence_sha256: dfe4a55a19a856ff2ab68d7321e4a0c295cbcc1458579b269d21ecbcfefe9725
state_history:
---

# 20260912-taxonomy-pending-recovery

Deterministic compressed record. The original active spec remains in Git history.

## Goal

为共享栏目/标签组件的操作提供 15 秒局部等待上限，退出无限 pending、保留输入并如实提示写入结果未知；允许有界只读核对最新列表，禁止自动重放 mutation。

## Acceptance criteria

- AC-1: 栏目与标签保存请求持续悬挂时，15 秒后退出保存中，保留名称/slug/说明，提示结果未确认并提供核对最新列表入口；不自动再次 POST/PATCH。
- AC-2: 请求已在服务器成功但响应丢失时不得假报失败或清空输入；核对仅发 GET、更新真实列表并保留输入。核对或删除本身悬挂也必须有界结束；离页中止本组件等待，不接受迟到结果覆盖状态。
- AC-3: 正常新增、编辑、删除、持久化刷新及重复 slug 409 继续有效；文档明确局部恢复与未知写入边界。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-taxonomy-pending-recovery.json](../../verification/evidence/20260912-taxonomy-pending-recovery.json)

SHA-256: `dfe4a55a19a856ff2ab68d7321e4a0c295cbcc1458579b269d21ecbcfefe9725`

Closed at 2026-09-12T05:31:50.168221+00:00.
