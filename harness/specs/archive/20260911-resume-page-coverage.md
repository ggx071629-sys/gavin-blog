---
id: archive-20260911-resume-page-coverage
level: L2
summary: 避免简历预算选取遗漏后页项目并将片段误作完整清单
load_when:
  - task:20260911-resume-page-coverage
task_id: 20260911-resume-page-coverage
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 说明简历页覆盖与局部证据的枚举边界。
evidence_sha256: 1c02cfed3fef7a320a986ebef0133767ba1a7e15940071369622322915d1037b
state_history:
---

# 20260911-resume-page-coverage

Deterministic compressed record. The original active spec remains in Git history.

## Goal

预算压力下让同一简历不同页获得首条候选机会，保留完整切片与引用；要求回答枚举已支持条目，不把片段当成全文。

## Acceptance criteria

- AC-1: 超限时简历按来源/版本/页轮转，第二页首项先于第一页追加项；其他来源行为及引用完整性保持。
- AC-2: 枚举提示要求列出所有有证据的不同条目，说明局部片段不能证明全文总数；当前真实项目提问与追问选中两个项目。

## Result

Verified and closed by the harness close command.

## Evidence

[20260911-resume-page-coverage.json](../../verification/evidence/20260911-resume-page-coverage.json)

SHA-256: `1c02cfed3fef7a320a986ebef0133767ba1a7e15940071369622322915d1037b`

Closed at 2026-09-11T04:02:19.800963+00:00.
