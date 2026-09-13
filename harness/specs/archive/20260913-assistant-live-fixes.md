---
id: archive-20260913-assistant-live-fixes
level: L2
summary: 修复隔离现场验证发现的助手控制、清除与测试入口问题
load_when:
  - task:20260913-assistant-live-fixes
author: Gavin
task_id: 20260913-assistant-live-fixes
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
documentation_reason: 明确内容备份围栏与运行控制边界、清除失败及测试模式说明。
evidence_sha256: 017b3e79c50e3cb97537647dbfc022f2800c4558d84db68b2445c6e14f0706a9
state_history:
---

# 20260913-assistant-live-fixes

Deterministic compressed record. The original active spec remains in Git history.

## Goal

修复已确认的问题，增加精确回归，按合同核定待验证现象并保留原失败记录。

## Acceptance criteria

- AC-1: 内容围栏持有期间仅运行库会话创建、删除与紧急停止可执行，认证及内容写入保护保持；在途执行失去资格后不得发布回答。
- AC-2: 清除失败保留可见记录并明确未确认服务端清除；成功及202撤销态继续阻止迟到响应恢复正文。
- AC-3: E2E干净构建可启动，持续Worker使用同一测试索引，离线测试说明匹配配置。
- AC-4: 管理开放状态核验当前readiness绑定，费用身份维度与剩余七行缺口按现行合同完成核定。

## Result

Verified and closed by the harness close command.

## Evidence

[20260913-assistant-live-fixes.json](../../verification/evidence/20260913-assistant-live-fixes.json)

SHA-256: `017b3e79c50e3cb97537647dbfc022f2800c4558d84db68b2445c6e14f0706a9`

Closed at 2026-09-13T09:01:06.521429+00:00.
