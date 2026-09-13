---
id: archive-20260911-assistant-live-activation
level: L2
summary: 实际内容库接入并补齐本机快捷启动器的既有worker生命周期
load_when:
  - task:20260911-assistant-live-activation
task_id: 20260911-assistant-live-activation
status: compressed
documentation_impact: required
documentation_targets:
  - harness/docs/operations/local-real-qa.md
documentation_reason: 明确真实内容库、后台worker启停以及实际简历接入结果。
evidence_sha256: f17fb433ad30a667a757e716c47bf11e3378ec2aaf16a1e02668e3ab3ee1b6bb
state_history:
---

# 20260911-assistant-live-activation

Deterministic compressed record. The original active spec remains in Git history.

## Goal

快捷启动器统一管理既有索引worker，使用.env.e5真实库和模型配置，使实际导入及后续手动刷新生效。

## Acceptance criteria

- AC-1: worker由同一个快捷启动管理进程创建并纳入现有退出清理和失败检测；在E5/Qdrant就绪后启动，使用.env.e5，默认库和Chat秘密不被误用。
- AC-2: 快捷入口现有端口检查、受控进程身份与配置错误脱敏合同保持；实际库导入和版本引用可验，结果与隔离测试区分。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-assistant-live-activation.json](../../verification/evidence/20260911-assistant-live-activation.json)

SHA-256: `f17fb433ad30a667a757e716c47bf11e3378ec2aaf16a1e02668e3ab3ee1b6bb`

Closed at 2026-09-11T01:54:16.754830+00:00.
