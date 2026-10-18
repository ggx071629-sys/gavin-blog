---
id: archive-20260911-index-vector-reuse
level: L2
summary: 相同正文新版本复用向量并停止不可重试错误的退避循环
load_when:
  - task:20260911-index-vector-reuse
task_id: 20260911-index-vector-reuse
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录向量复用条件与需要介入错误的终止规则。
evidence_sha256: e4b81e37b87a848980c86793cc916bcb742b28fcf447cf0c46bb1f80d590ad27
state_history:
---

# 20260911-index-vector-reuse

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在同一模型与pipeline身份下，按完全一致的切片正文复用同来源已存向量，并更新新版本元数据与FTS；需要介入的错误立即失败且保留准确状态。

## Acceptance criteria

- AC-1: 相同正文重新发布后更新索引版本且不再次调用嵌入；正文、身份、向量维度或绑定不匹配不得复用。
- AC-2: 结果未知或成功记录缺失可复用向量时立即终止，区分原因并保持禁止隐式重发；普通临时错误仍保留重试。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-index-vector-reuse.json](../../verification/evidence/20260911-index-vector-reuse.json)

SHA-256: `e4b81e37b87a848980c86793cc916bcb742b28fcf447cf0c46bb1f80d590ad27`

Closed at 2026-09-11T08:17:10.329149+00:00.
