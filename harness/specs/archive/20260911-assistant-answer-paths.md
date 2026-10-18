---
id: archive-20260911-assistant-answer-paths
level: L2
summary: 问答正文使用来源标题并阻止来源路径回显
load_when:
  - task:20260911-assistant-answer-paths
author: Codex
task_id: 20260911-assistant-answer-paths
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 明确正文来源地址替换与导航元数据保留的边界。
evidence_sha256: 090c6eb622f7353d5767c0e3ce0a9ac11ef5b6b623e2031f112c3ce3efc7bd22
state_history:
---

# 20260911-assistant-answer-paths

Deterministic compressed record. The original active spec remains in Git history.

## Goal

本站来源的地址在新回答正文中改用可信来源标题，引用跳转保持可用。

## Acceptance criteria

- AC-1: 回答中与当前证据绑定的来源裸路径、完整 HTTP(S) URL 及其查询/片段形式使用来源标题；路径边界不误匹配其他文件或更长路径；引用元数据保留原跳转路径，非法引用及原有危险格式仍被拒绝。
- AC-2: 提示明确历史中的来源路径不得复述，事实仍以本轮证据为准；有效教程路径不受全局斜杠过滤影响。
- AC-3: 实际问答链路的 SSE、会话恢复和新存储历史使用同一处理后的回答，来源导航路径保持不变。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-assistant-answer-paths.json](../../verification/evidence/20260911-assistant-answer-paths.json)

SHA-256: `090c6eb622f7353d5767c0e3ce0a9ac11ef5b6b623e2031f112c3ce3efc7bd22`

Closed at 2026-09-11T13:23:55.059636+00:00.
