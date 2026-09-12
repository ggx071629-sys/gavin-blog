---
id: archive-20260913-assistant-sync-attention
level: L2
summary: 依据当前公开内容收录事实排除已覆盖的历史同步失败提醒
load_when:
  - task:20260913-assistant-sync-attention
task_id: 20260913-assistant-sync-attention
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明同步待处理数量与保留历史任务的区别及只读判定边界。
evidence_sha256: 9092688f72d91f1b7e9cf25bc073ed6c5e4faf23c269e5c15b7edbea90b21c53
state_history:
---

# 20260913-assistant-sync-attention

Deterministic compressed record. The original active spec remains in Git history.

## Goal

仅对当前未解决的同步失败提醒；历史列表标注已收录并禁止无意义重试，保留原状态及费用记录。

## Acceptance criteria

- AC-1: 当前 active 索引的公开版本、完整切片与全文检索投影一致并有成功构建或同步事实时，历史 upsert 失败不计入 queue.failed；缺版本、缺切片、缺全文记录、无运行配置或无成功事实仍保留提醒，删除清理失败保守保留。
- AC-2: 历史任务继续以原失败状态可查，返回明确的覆盖标记；前端显示历史失败已收录并隐藏重试和故障诊断动作，普通未解决失败保持原操作；读取不调用模型或向量服务。

## Result

Verified and closed by the harness close command.

## Evidence

[20260913-assistant-sync-attention.json](../../verification/evidence/20260913-assistant-sync-attention.json)

SHA-256: `9092688f72d91f1b7e9cf25bc073ed6c5e4faf23c269e5c15b7edbea90b21c53`

Closed at 2026-09-12T20:05:12.552943+00:00.
