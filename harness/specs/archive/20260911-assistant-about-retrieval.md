---
id: archive-20260911-assistant-about-retrieval
level: L2
summary: Q2-03 将关于页加入初次重建与有界混合检索
load_when:
  - task:20260911-assistant-about-retrieval
task_id: 20260911-assistant-about-retrieval
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录关于页初次重建和预算内检索行为。
evidence_sha256: 386fc0b64cf07ae1bdb7c8f912a1bc38db6ee76ff0798f76405d417317fc9149
state_history:
---

# 20260911-assistant-about-retrieval

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让合格关于页通过现有 worker 初次构建和关键词/向量混合检索，复用证据预算与版本复检。

## Acceptance criteria

- AC-1: 自动 seed 不加入重建，主动修订生成可检索切片；FTS/向量可召回且证据满足预算；更新等待时旧 evidence 被拒绝，其他有效来源仍可用。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-assistant-about-retrieval.json](../../verification/evidence/20260911-assistant-about-retrieval.json)

SHA-256: `386fc0b64cf07ae1bdb7c8f912a1bc38db6ee76ff0798f76405d417317fc9149`

Closed at 2026-09-10T17:15:10.821579+00:00.
