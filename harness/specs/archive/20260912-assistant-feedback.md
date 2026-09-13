---
id: archive-20260912-assistant-feedback
level: L2
summary: Q3-05 提供短会话内无正文赞踩和被动后台观测
load_when:
  - task:20260912-assistant-feedback
task_id: 20260912-assistant-feedback
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
  - packages/contracts/README.md
documentation_reason: 反馈接口、告知、短留存和删除语义跨端生效。
evidence_sha256: 8d7511f1cc0a4444a6d5cbab8dc41d8256dce175d97acbc0cc0d97be252825ba
state_history:
---

# 20260912-assistant-feedback

Deterministic compressed record. The original active spec remains in Git history.

## Goal

为当前短会话的有效回答保存一个可修改/撤销的赞踩选择；后台展示有界、无正文反馈与异常统计。

## Acceptance criteria

- AC-1: 反馈受原 Origin、Cookie、CSRF、会话和速率保护，只能评价自己的有效回答；同 turn 幂等覆盖或撤销，不携带正文、不调用模型。
- AC-2: 反馈不延长原回答TTL，正文到期/清除时删除；无正文诊断保留7天并由既有清理器删除，清理失败不宣称成功。
- AC-3: 公开回答可赞踩并撤销，提交/失败状态准确，恢复严格解析选择；界面告知用途和删除语义，过期/清除不接纳迟到结果。
- AC-4: 管理端只读展示当前有效赞踩及阶段统计/已有错误异常提示；契约生成同步，用户反馈不冒充正确率，未选正文采样与外部告警有明确范围说明。

## Result

Verified and closed by the harness close command.

## Evidence

[20260912-assistant-feedback.json](../../verification/evidence/20260912-assistant-feedback.json)

SHA-256: `8d7511f1cc0a4444a6d5cbab8dc41d8256dce175d97acbc0cc0d97be252825ba`

Closed at 2026-09-12T14:15:59.417564+00:00.
