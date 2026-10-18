---
id: archive-20260906-public-assistant-ui
level: L2
summary: 完成视觉提案第六阶段的公开问答面板与状态交互
load_when:
  - task:20260906-public-assistant-ui
author: Gavin
task_id: 20260906-public-assistant-ui
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/README.md
  - ui-fix/PHASE-6.md
documentation_reason: 记录访客问答面板、状态恢复、引用焦点、设备验证和生产资格边界。
evidence_sha256: cdc4e10ece5e0f80e5a6cdc49d67b563dd296db8d02e77ac1305a1ff6195f001
state_history:
---

# 20260906-public-assistant-ui

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在真实公开页面迁入阅读批注式问答面板，补齐完整会话状态和交互，使用真实隔离问答及受控故障响应验证。

## Acceptance criteria

- AC-1: 480px 桌面浮窗、平板抽屉、手机全屏符合现有双主题；全部八个设计宽度、短视口和长内容无横滚，输入与清除可达，可视视口缩小时保持操作可用。
- AC-2: 等待保留问题，欢迎和真实数据说明适时折叠，引用定位与返回对应本轮及本次触发点，未读定位最新回答且上翻不被抢滚动；输入支持 IME、桌面回车与手机换行。
- AC-3: 恢复、拒答、限流、断线、失效、结果检查及清除准确区分，检查不重新提问；迟到响应不恢复旧正文，恢复和清除期间禁止重复提交。
- AC-4: 真实隔离提问和来源导航通过，默认关闭零请求、引用校验、进行中刷新、多轮上下文、清除代际与菜单焦点互斥保持。
- AC-5: 文档、设计差异、验证结果和回退方式可复查；未执行真机或生产资格检查不得写为通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260906-public-assistant-ui.json](../../verification/evidence/20260906-public-assistant-ui.json)

SHA-256: `cdc4e10ece5e0f80e5a6cdc49d67b563dd296db8d02e77ac1305a1ff6195f001`

Closed at 2026-09-05T21:19:24.694582+00:00.
