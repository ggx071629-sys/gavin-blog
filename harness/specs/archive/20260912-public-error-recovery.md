---
id: archive-20260912-public-error-recovery
level: L2
summary: 公开页面首次客户端加载失败进入可恢复错误页而不是旧页面内容
load_when:
  - task:20260912-public-error-recovery
author: Codex
task_id: 20260912-public-error-recovery
status: compressed
documentation_impact: none
documentation_reason: 只修复既有客户端错误呈现缺陷并新增回归，README 未记录页面错误态约定，没有需要同步的 durable 文档。
evidence_sha256: 86664ca08ef79be46a2420d02bc07e7962ddabcbbc69915c7b705957e8068a53
state_history:
---

# 20260912-public-error-recovery

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让首次客户端加载失败在目标路由呈现既有全站错误页与操作内恢复入口；错误页的站内入口可用；服务端直接访问失败与公开详情缺失的既有语义不变。

## Acceptance criteria

- AC-1: 首次客户端加载失败时目标路由渲染可恢复错误页，不再显示上一页内容。
- AC-2: 错误页恢复入口可用，且服务端失败、搜索后续失败与缺失详情语义保持不变。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-public-error-recovery.json](../../verification/evidence/20260912-public-error-recovery.json)

SHA-256: `86664ca08ef79be46a2420d02bc07e7962ddabcbbc69915c7b705957e8068a53`

Closed at 2026-09-12T04:47:10.169539+00:00.
