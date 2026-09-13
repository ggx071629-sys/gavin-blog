---
id: archive-20260910-studio-trial
level: L2
summary: 对齐试问布局并保留真实会话和引用状态
load_when:
  - task:20260910-studio-trial
task_id: 20260910-studio-trial
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录试问布局、实际会话及计费呈现边界。
evidence_sha256: 14a5e784d9821a291c764d766638e51db50dcabe760e86303eed58c3241d5eba
state_history:
---

# 20260910-studio-trial

Deterministic compressed record. The original active spec remains in Git history.

## Goal

桌面采用说明/对话两列，手机单列；空态、问题、回答依据和输入操作采用选定稿层级。保留真实状态及会话操作。

## Acceptance criteria

- AC-1: 试问桌面分区、手机堆叠，双主题 320/390/1440px 无溢出且 axe 通过；空态、真实回答、折叠依据、输入与发送可读可操作。
- AC-2: 隔离真实会话完成提问、结算、恢复及清空；引用仍只指向安全公开来源；未满足试问条件时按钮与快捷键均不能提交。

## Result

Verified and closed by the harness close command.

## Evidence

[20260910-studio-trial.json](../../verification/evidence/20260910-studio-trial.json)

SHA-256: `14a5e784d9821a291c764d766638e51db50dcabe760e86303eed58c3241d5eba`

Closed at 2026-09-10T07:34:45.111067+00:00.
