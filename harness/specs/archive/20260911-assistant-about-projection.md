---
id: archive-20260911-assistant-about-projection
level: L2
summary: Q2-01 为关于页增加显式问答资格和发布正文投影
load_when:
  - task:20260911-assistant-about-projection
task_id: 20260911-assistant-about-projection
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明 about 来源投影、显式资格和草稿隔离。
evidence_sha256: 4146811a4fc95049010503929ec4653699e49464f237717ff75e4039249cbba5
state_history:
---

# 20260911-assistant-about-projection

Deterministic compressed record. The original active spec remains in Git history.

## Goal

提供 about 来源类型、发布正文投影及资格迁移，保留既有四类来源和数据。

## Acceptance criteria

- AC-1: 仅当前主动发布/回滚修订可投影，正文覆盖适用结构字段；草稿与 seed 排除，旧库升级保留数据并允许 about 索引类型，非法来源仍拒绝。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-assistant-about-projection.json](../../verification/evidence/20260911-assistant-about-projection.json)

SHA-256: `4146811a4fc95049010503929ec4653699e49464f237717ff75e4039249cbba5`

Closed at 2026-09-10T17:04:57.843781+00:00.
