---
id: archive-20260911-assistant-about-sync
level: L2
summary: Q2-02 关于页发布回滚原子触发索引并撤销旧版本资格
load_when:
  - task:20260911-assistant-about-sync
task_id: 20260911-assistant-about-sync
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - packages/contracts/README.md
documentation_reason: 说明关于页事务同步、旧版失效和管理来源枚举。
evidence_sha256: f744f26c3501248357c836665c049567868a1f2168434aff9c1a33788b189dab
state_history:
---

# 20260911-assistant-about-sync

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在发布和回滚事务内登记 about 最新版本任务，并通过既有来源 fence 排除旧证据和迟到任务；新来源可通过管理合同读取。

## Acceptance criteria

- AC-1: 发布/回滚入队与修订原子一致，草稿无任务，失败无泄漏，重复发布合并到最新目标；旧来源版本立即被 fence 拒绝，管理 schema 与共享类型接受 about。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-assistant-about-sync.json](../../verification/evidence/20260911-assistant-about-sync.json)

SHA-256: `f744f26c3501248357c836665c049567868a1f2168434aff9c1a33788b189dab`

Closed at 2026-09-10T17:11:17.368721+00:00.
