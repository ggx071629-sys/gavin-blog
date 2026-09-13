---
id: archive-20260913-assistant-restart-recovery
level: L2
summary: 保留本机问答启停选择并在恢复试问时验证新索引资格
load_when:
  - task:20260913-assistant-restart-recovery
task_id: 20260913-assistant-restart-recovery
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明本机启动状态保留与切换后恢复试问的资格验证边界。
evidence_sha256: 51e4ce1c95d8e596880ff78e224711a19db5b502dd1455d6322e2012579a0661
state_history:
---

# 20260913-assistant-restart-recovery

Deterministic compressed record. The original active spec remains in Git history.

## Goal

正常重启保留启停选择；本机管理员显式恢复试问时完成新索引资格验证，无需重启。

## Acceptance criteria

- AC-1: 本机正常启动和退出保留访客开放或关闭选择及管理员停止状态，失败不开放服务。
- AC-2: 本机恢复试问在新索引完整、签名探测有效和维护保护允许时更新资格并恢复，保持访客关闭；不完整索引、无效探测及维护保护拒绝恢复，非本机入口不自动签发资格。

## Result

Verified and closed by the harness close command.

## Evidence

[20260913-assistant-restart-recovery.json](../../verification/evidence/20260913-assistant-restart-recovery.json)

SHA-256: `51e4ce1c95d8e596880ff78e224711a19db5b502dd1455d6322e2012579a0661`

Closed at 2026-09-12T19:44:15.724360+00:00.
