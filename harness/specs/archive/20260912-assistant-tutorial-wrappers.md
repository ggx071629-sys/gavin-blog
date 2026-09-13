---
id: archive-20260912-assistant-tutorial-wrappers
level: L2
summary: 校验真实教程回答中的重复主题引介和英文完整通知关系
load_when:
  - task:20260912-assistant-tutorial-wrappers
author: Codex
task_id: 20260912-assistant-tutorial-wrappers
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明重复主题引介仅在与后句一致时归一化，保留有限英文关系范围。
evidence_sha256: f833145c3b9a2e975474449b0425a1239f8dab62ac4270e3af9edab31fbfb761
state_history:
---

# 20260912-assistant-tutorial-wrappers

Deterministic compressed record. The original active spec remains in Git history.

## Goal

允许同一主题重复引介及完整邮件通知关系的已确认英文表达；完整事实内容、标题、原因和限定保持核对。

## Acceptance criteria

- AC-1: 两个真实输出的合法重复引介/英文完整关系通过；错误主题、协议、否定、限定和新增事实仍拒绝。
- AC-2: 数值、事实语境、讨论以及运行器授权边界回归通过，文档明确有限范围，不以离线关闭替代G07实际模型验收。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-tutorial-wrappers.json](../../verification/evidence/20260912-assistant-tutorial-wrappers.json)

SHA-256: `f833145c3b9a2e975474449b0425a1239f8dab62ac4270e3af9edab31fbfb761`

Closed at 2026-09-12T12:08:11.589349+00:00.
